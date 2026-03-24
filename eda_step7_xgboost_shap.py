"""
eda_step7_xgboost_shap.py
=========================
Bifurcated XGBoost + SHAP pipeline — four separate predictive models split
by media format (Image vs Video) and financial target (CTR vs CPM).

Why bifurcation?
  Image rows have zero-padded pca_var_* columns by construction.  Feeding
  those zeros into a unified model creates spurious feature importance for
  the variance block.  Separate models guarantee clean SHAP inferences per
  format.

Pipeline:
  0. PCA prep   — silently regenerate pca_mean_1/2, pca_var_1/2, is_video
  1. Bifurcation — df_img (is_video=0) / df_vid (is_video=1)
  2. OHE         — dominant_funnel_stage → funnel_Awareness / _Consideration /
                   _Conversion  (Unknown rows excluded)
  3. Training    — 5-Fold CV (R² + MAE) then full-data fit for SHAP
  4. SHAP        — TreeExplainer → summary plots × 4
  5. Console     — CV table + Top 3 SHAP features per model

Outputs:
  · shap_img_ctr.png  shap_img_cpm.png
  · shap_vid_ctr.png  shap_vid_cpm.png
"""

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")                       # non-interactive backend for saving

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from pathlib import Path
from sklearn.decomposition import PCA
from sklearn.model_selection import cross_validate, KFold
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
DATA = BASE / "Havas.2" / "df_master.csv"

# ── Cognitive column groups (for PCA prep) ─────────────────────────────────────
COG_MEAN = [f"cognitive_mean_{i}" for i in range(10)]
COG_VAR  = [f"cognitive_var_{i}"  for i in range(10)]

# ── Model config ───────────────────────────────────────────────────────────────
XGB_PARAMS = dict(
    n_estimators    = 300,
    max_depth       = 4,
    learning_rate   = 0.08,
    subsample       = 0.8,
    colsample_bytree= 0.8,
    min_child_weight= 5,
    random_state    = 42,
    verbosity       = 0,
    tree_method     = "hist",
)

CV_FOLDS    = 5
RANDOM_SEED = 42


# ══════════════════════════════════════════════════════════════════════════════
# Step 0 — Silent PCA prep (regenerates pca_mean_*, pca_var_*, is_video)
# ══════════════════════════════════════════════════════════════════════════════
def build_pca_features(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    df = df.copy()
    video_mask   = (df[COG_VAR] > 0).any(axis=1)
    df["is_video"] = video_mask.astype(int)

    # ── Mean block  (all rows) ─────────────────────────────────────────────────
    X_m_sc  = StandardScaler().fit_transform(df[COG_MEAN])
    pca_m   = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_m     = pca_m.fit_transform(X_m_sc)
    n_mean  = X_m.shape[1]
    for i in range(n_mean):
        df[f"pca_mean_{i+1}"] = X_m[:, i]

    # ── Var block  (video rows only, images stay 0.0) ──────────────────────────
    X_v_sc = StandardScaler().fit_transform(df.loc[video_mask, COG_VAR])
    pca_v  = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_v    = pca_v.fit_transform(X_v_sc)
    n_var  = X_v.shape[1]
    for i in range(n_var):
        df[f"pca_var_{i+1}"] = 0.0
        df.loc[video_mask, f"pca_var_{i+1}"] = X_v[:, i]

    return df, n_mean, n_var


# ══════════════════════════════════════════════════════════════════════════════
# Step 1-2 — Bifurcation & OHE
# ══════════════════════════════════════════════════════════════════════════════
def build_datasets(df: pd.DataFrame,
                   n_mean: int,
                   n_var:  int) -> dict:
    """
    Returns a dict with keys img_ctr, img_cpm, vid_ctr, vid_cpm.
    Each value is a (X, y) tuple ready for modelling.
    """
    pca_mean_cols = [f"pca_mean_{i+1}" for i in range(n_mean)]
    pca_var_cols  = [f"pca_var_{i+1}"  for i in range(n_var)]
    neuro_cols    = ["engajamentoneural", "cognitivedemand", "focus"]

    # Exclude Unknown funnel rows (only 5 rows — clean split)
    df = df[df["dominant_funnel_stage"] != "Unknown"].copy()

    # One-hot encode funnel stage
    ohe = pd.get_dummies(
        df["dominant_funnel_stage"],
        prefix="funnel",
        drop_first=False,
        dtype=float,
    )
    df = pd.concat([df, ohe], axis=1)
    funnel_cols = sorted(ohe.columns.tolist())   # funnel_Awareness, _Consideration, _Conversion

    # Bifurcate
    df_img = df[df["is_video"] == 0].copy()
    df_vid = df[df["is_video"] == 1].copy()

    def make_xy(subset, feature_cols, target):
        keep = feature_cols + [target]
        sub  = subset[keep].dropna()
        X    = sub[feature_cols]
        y    = sub[target]
        return X, y

    img_features = pca_mean_cols + neuro_cols + funnel_cols
    vid_features = pca_mean_cols + pca_var_cols + neuro_cols + funnel_cols

    datasets = {
        "img_ctr": make_xy(df_img, img_features, "CTR"),
        "img_cpm": make_xy(df_img, img_features, "CPM"),
        "vid_ctr": make_xy(df_vid, vid_features, "CTR"),
        "vid_cpm": make_xy(df_vid, vid_features, "CPM"),
    }

    return datasets


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Cross-Validation + full fit
# ══════════════════════════════════════════════════════════════════════════════
def train_models(datasets: dict) -> tuple[dict, dict]:
    """Returns (cv_results, fitted_models)."""
    kf = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    cv_results    = {}
    fitted_models = {}

    LABELS = {
        "img_ctr": "Image  │  CTR",
        "img_cpm": "Image  │  CPM",
        "vid_ctr": "Video  │  CTR",
        "vid_cpm": "Video  │  CPM",
    }

    print("\n" + "─" * 62)
    print("[Step 3] Cross-Validation & model fitting...")
    print("─" * 62)

    for key, (X, y) in datasets.items():
        model = XGBRegressor(**XGB_PARAMS)

        cv = cross_validate(
            model, X, y,
            cv       = kf,
            scoring  = {"r2": "r2", "mae": "neg_mean_absolute_error"},
            n_jobs   = -1,
        )

        cv_results[key] = {
            "label" : LABELS[key],
            "n"     : len(y),
            "r2_mean": cv["test_r2"].mean(),
            "r2_std" : cv["test_r2"].std(),
            "mae_mean": -cv["test_mae"].mean(),   # neg_MAE → positive MAE
            "mae_std" :  cv["test_mae"].std(),    # std is always positive
        }

        # Full-data fit for SHAP
        model.fit(X, y)
        fitted_models[key] = (model, X)

        print(f"  ✓ {LABELS[key]:<14}  (n={len(y):,})")

    return cv_results, fitted_models


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — SHAP extraction + summary plots
# ══════════════════════════════════════════════════════════════════════════════
def run_shap(fitted_models: dict) -> dict:
    """Returns shap importances dict: key → pd.Series(mean_abs_shap, index=features)."""

    FILENAMES = {
        "img_ctr": BASE / "shap_img_ctr.png",
        "img_cpm": BASE / "shap_img_cpm.png",
        "vid_ctr": BASE / "shap_vid_ctr.png",
        "vid_cpm": BASE / "shap_vid_cpm.png",
    }

    PLOT_TITLES = {
        "img_ctr": "SHAP — Image Model  |  Target: CTR",
        "img_cpm": "SHAP — Image Model  |  Target: CPM",
        "vid_ctr": "SHAP — Video Model  |  Target: CTR",
        "vid_cpm": "SHAP — Video Model  |  Target: CPM",
    }

    print("\n" + "─" * 62)
    print("[Step 4] SHAP extraction & summary plots...")
    print("─" * 62)

    importances = {}

    # Columns to hide from the SHAP plot (model still trains with them)
    FUNNEL_HIDE = {"funnel_Awareness", "funnel_Consideration", "funnel_Conversion"}

    for key, (model, X) in fitted_models.items():
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)          # numpy array (n_samples × n_feats)

        # ── Importance series (full, including funnel) ────────────────────────
        mean_abs = np.abs(shap_values).mean(axis=0)
        importances[key] = pd.Series(
            mean_abs, index=X.columns
        ).sort_values(ascending=False)

        # ── Visual filter: remove funnel dummies from plot only ──────────────
        keep_mask    = ~X.columns.isin(FUNNEL_HIDE)
        X_plot       = X.loc[:, keep_mask]
        shap_plot    = shap_values[:, keep_mask]         # slice columns in sync

        # ── Summary plot ───────────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(9, max(4, len(X_plot.columns) * 0.42 + 1)))
        shap.summary_plot(
            shap_plot, X_plot,
            plot_type = "dot",
            show      = False,
            max_display = len(X_plot.columns),
        )
        plt.title(PLOT_TITLES[key], fontsize=12, fontweight="bold", pad=10)
        plt.tight_layout()
        plt.savefig(FILENAMES[key], dpi=150, bbox_inches="tight")
        plt.close("all")

        print(f"  ✓ {PLOT_TITLES[key]}  →  {FILENAMES[key].name}")

    return importances


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Terminal executive summary
# ══════════════════════════════════════════════════════════════════════════════
def print_cv_table(cv_results: dict) -> None:
    W = 72
    print("\n" + "═" * W)
    print("  CROSS-VALIDATION RESULTS  (5-Fold, XGBoost)")
    print("═" * W)
    print(f"  {'Model':<18} {'N':>6}  {'R²  (mean ± std)':>22}  {'MAE  (mean ± std)':>22}")
    print("  " + "─" * (W - 2))

    for key, r in cv_results.items():
        r2_str  = f"{r['r2_mean']:>+.4f} ± {r['r2_std']:.4f}"
        mae_str = f"{r['mae_mean']:>8.4f} ± {r['mae_std']:.4f}"
        print(f"  {r['label']:<18} {r['n']:>6,}  {r2_str:>22}  {mae_str:>22}")

    print("═" * W + "\n")


def print_shap_summary(importances: dict, cv_results: dict) -> None:
    MODEL_LABELS = {
        "img_ctr": "Image — CTR",
        "img_cpm": "Image — CPM",
        "vid_ctr": "Video — CTR",
        "vid_cpm": "Video — CPM",
    }
    W = 62
    print("═" * W)
    print("  TOP 3 SHAP FEATURES BY MODEL  (mean |SHAP value|)")
    print("═" * W)

    for key, imp in importances.items():
        top3 = imp.head(3)
        print(f"\n  ▶  {MODEL_LABELS[key]}")
        print("  " + "─" * (W - 2))
        for rank, (feat, val) in enumerate(top3.items(), start=1):
            bar = "█" * int(val / imp.iloc[0] * 18)
            print(f"  {rank}.  {feat:<24}  {val:.5f}  {bar}")

    print("\n" + "═" * W + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def run_eda_step7(df: pd.DataFrame | None = None) -> None:
    print("═" * 62)
    print("  EDA Step 7 — Bifurcated XGBoost + SHAP Pipeline")
    print("═" * 62)

    if df is None:
        df = pd.read_csv(DATA)
    print(f"\n  Dataset : {df.shape[0]:,} rows × {df.shape[1]} cols")

    # ── 0. Build PCA features ──────────────────────────────────────────────────
    print("\n" + "─" * 62)
    print("[Step 0] Regenerating PCA features from cognitive columns...")
    df, n_mean, n_var = build_pca_features(df)
    print(f"         pca_mean components : {n_mean}  "
          f"({[f'pca_mean_{i+1}' for i in range(n_mean)]})")
    print(f"         pca_var  components : {n_var}  "
          f"({[f'pca_var_{i+1}' for i in range(n_var)]})")

    # ── 1-2. Bifurcate + OHE ──────────────────────────────────────────────────
    print("\n" + "─" * 62)
    print("[Step 1-2] Bifurcation & one-hot encoding funnel stage...")
    datasets = build_datasets(df, n_mean, n_var)
    for key, (X, y) in datasets.items():
        print(f"  {key:<10}  X={X.shape}  features: {list(X.columns)}")

    # ── 3. CV + fit ───────────────────────────────────────────────────────────
    cv_results, fitted_models = train_models(datasets)

    # ── 4. SHAP ───────────────────────────────────────────────────────────────
    importances = run_shap(fitted_models)

    # ── 5. Summary ────────────────────────────────────────────────────────────
    print_cv_table(cv_results)
    print_shap_summary(importances, cv_results)


if __name__ == "__main__":
    run_eda_step7()
