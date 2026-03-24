"""
eda_step8_classification_clustering.py
======================================
Classification pivot + K-Means archetype clustering.

Part A — XGBClassifier (Top-Performer Detection)
  · Binary target: is_top_performer = 1 if CTR ≥ 75th percentile
    within its (is_video × dominant_funnel_stage) group.
  · Two separate classifiers: Image model (8 features) / Video model (10 features).
  · 5-Fold Stratified CV → ROC-AUC + SHAP summary plots.

Part B — K-Means Archetype Clustering (Video only)
  · 3 clusters on scaled neural features.
  · Cross-tabulation: Cluster × Funnel Stage → median CTR, median CPM.
  · Cluster centroid profiles for archetype naming.

Outputs:
  · shap_class_img_ctr.png   shap_class_vid_ctr.png
  · Console: ROC-AUC table + cluster cross-tabulation
"""

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
DATA = BASE / "Havas.2" / "df_master.csv"

# ── Column groups ──────────────────────────────────────────────────────────────
COG_MEAN  = [f"cognitive_mean_{i}" for i in range(10)]
COG_VAR   = [f"cognitive_var_{i}"  for i in range(10)]
NEURO     = ["engajamentoneural", "cognitivedemand", "focus"]

# ── XGB Classifier config ─────────────────────────────────────────────────────
XGB_PARAMS = dict(
    n_estimators     = 300,
    max_depth        = 4,
    learning_rate    = 0.08,
    subsample        = 0.8,
    colsample_bytree = 0.8,
    min_child_weight = 5,
    random_state     = 42,
    verbosity        = 0,
    tree_method      = "hist",
    eval_metric      = "logloss",
)

CV_FOLDS    = 5
RANDOM_SEED = 42


# ══════════════════════════════════════════════════════════════════════════════
# Step 0 — Data prep (PCA + is_video + OHE + grouped threshold)
# ══════════════════════════════════════════════════════════════════════════════
def prepare_data(path: Path) -> pd.DataFrame:
    print("─" * 68)
    print("[Step 0] Data preparation — PCA + grouped threshold + OHE...")
    print("─" * 68)

    df = pd.read_csv(path)
    df = df[df["dominant_funnel_stage"] != "Unknown"].copy()

    # is_video flag
    video_mask     = (df[COG_VAR] > 0).any(axis=1)
    df["is_video"] = video_mask.astype(int)

    # ── PCA Mean block (all rows) ─────────────────────────────────────────────
    X_m_sc = StandardScaler().fit_transform(df[COG_MEAN])
    pca_m  = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_m    = pca_m.fit_transform(X_m_sc)
    for i in range(X_m.shape[1]):
        df[f"pca_mean_{i+1}"] = X_m[:, i]

    # ── PCA Var block (video rows only) ───────────────────────────────────────
    X_v_sc = StandardScaler().fit_transform(df.loc[video_mask, COG_VAR])
    pca_v  = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_v    = pca_v.fit_transform(X_v_sc)
    for i in range(X_v.shape[1]):
        df[f"pca_var_{i+1}"] = 0.0
        df.loc[video_mask, f"pca_var_{i+1}"] = X_v[:, i]

    n_mean = X_m.shape[1]
    n_var  = X_v.shape[1]
    print(f"  PCA: {n_mean} mean components + {n_var} var components")

    # ── Grouped top-performer threshold ───────────────────────────────────────
    df["p75_threshold"] = (
        df.groupby(["is_video", "dominant_funnel_stage"])["CTR"]
        .transform(lambda g: g.quantile(0.75))
    )
    df["is_top_performer"] = (df["CTR"] >= df["p75_threshold"]).astype(int)

    # Print the threshold table
    thr = (df.groupby(["is_video", "dominant_funnel_stage"])
             .agg(n=("CTR", "size"),
                  p75_CTR=("p75_threshold", "first"),
                  top_pct=("is_top_performer", "mean"))
             .reset_index())
    thr["media"] = thr["is_video"].map({0: "Image", 1: "Video"})
    thr["top_pct"] = (thr["top_pct"] * 100).round(1)

    print(f"\n  Grouped P75 Thresholds:")
    print(f"  {'Media':<8} {'Funnel':<16} {'N':>6}  {'P75 CTR':>10}  {'Top %':>6}")
    print(f"  " + "─" * 52)
    for _, row in thr.iterrows():
        print(f"  {row['media']:<8} {row['dominant_funnel_stage']:<16} "
              f"{row['n']:>6}  {row['p75_CTR']:>10.5f}  {row['top_pct']:>5.1f}%")

    top_rate = df["is_top_performer"].mean() * 100
    print(f"\n  Overall top-performer rate: {top_rate:.1f}%  "
          f"(n={df['is_top_performer'].sum():,} of {len(df):,})")

    # ── OHE funnel stage ──────────────────────────────────────────────────────
    ohe = pd.get_dummies(
        df["dominant_funnel_stage"], prefix="funnel", drop_first=False, dtype=float
    )
    df = pd.concat([df, ohe], axis=1)

    return df, n_mean, n_var, sorted(ohe.columns.tolist())


# ══════════════════════════════════════════════════════════════════════════════
# Part A — XGBClassifier + Stratified CV + SHAP
# ══════════════════════════════════════════════════════════════════════════════
def run_classification(df: pd.DataFrame,
                       n_mean: int,
                       n_var:  int,
                       funnel_cols: list[str]) -> None:

    pca_mean_cols = [f"pca_mean_{i+1}" for i in range(n_mean)]
    pca_var_cols  = [f"pca_var_{i+1}"  for i in range(n_var)]

    img_features = pca_mean_cols + NEURO + funnel_cols
    vid_features = pca_mean_cols + pca_var_cols + NEURO + funnel_cols

    df_img = df[df["is_video"] == 0].copy()
    df_vid = df[df["is_video"] == 1].copy()

    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_SEED)

    results = {}

    for label, subset, features, filename in [
        ("Image", df_img, img_features, BASE / "shap_class_img_ctr.png"),
        ("Video", df_vid, vid_features, BASE / "shap_class_vid_ctr.png"),
    ]:
        X = subset[features].dropna()
        y = subset.loc[X.index, "is_top_performer"]

        # ── 5-Fold Stratified CV → ROC-AUC ────────────────────────────────────
        model = XGBClassifier(**XGB_PARAMS)
        auc_scores = cross_val_score(
            model, X, y, cv=skf, scoring="roc_auc", n_jobs=-1
        )
        results[label] = {
            "n":        len(y),
            "pos_rate": y.mean() * 100,
            "auc_mean": auc_scores.mean(),
            "auc_std":  auc_scores.std(),
        }

        # ── Full fit for SHAP ──────────────────────────────────────────────────
        model.fit(X, y)
        explainer   = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # ── Visual filter: remove funnel dummies from plot only ──────────────
        FUNNEL_HIDE = {"funnel_Awareness", "funnel_Consideration", "funnel_Conversion"}
        keep_mask   = ~X.columns.isin(FUNNEL_HIDE)
        X_plot      = X.loc[:, keep_mask]
        shap_plot   = shap_values[:, keep_mask]

        # ── SHAP summary plot ──────────────────────────────────────────────────
        fig, ax = plt.subplots(figsize=(9, max(4, len(X_plot.columns) * 0.42 + 1)))
        shap.summary_plot(
            shap_plot, X_plot,
            plot_type   = "dot",
            show        = False,
            max_display = len(X_plot.columns),
        )
        plt.title(
            f"SHAP — {label} Classifier  |  Target: is_top_performer (CTR ≥ P75 by group)",
            fontsize=11, fontweight="bold", pad=10
        )
        plt.tight_layout()
        plt.savefig(filename, dpi=150, bbox_inches="tight")
        plt.close("all")

        print(f"  ✓ {label} classifier  |  SHAP → {filename.name}")

    # ── Print ROC-AUC table ───────────────────────────────────────────────────
    W = 68
    print("\n" + "═" * W)
    print("  CLASSIFICATION RESULTS — Top-Performer Detection (CTR ≥ P75)")
    print("  Target: is_top_performer (grouped by is_video × funnel_stage)")
    print("═" * W)
    print(f"  {'Model':<10} {'N':>6}  {'Pos %':>7}  {'ROC-AUC  (mean ± std)':>26}")
    print("  " + "─" * (W - 2))

    for label, r in results.items():
        auc_str = f"{r['auc_mean']:.4f} ± {r['auc_std']:.4f}"
        print(f"  {label:<10} {r['n']:>6,}  {r['pos_rate']:>6.1f}%  {auc_str:>26}")

    print("═" * W)


# ══════════════════════════════════════════════════════════════════════════════
# Part B — K-Means Archetype Clustering (Video only)
# ══════════════════════════════════════════════════════════════════════════════
def run_clustering(df: pd.DataFrame, n_mean: int, n_var: int) -> None:

    pca_mean_cols = [f"pca_mean_{i+1}" for i in range(n_mean)]
    pca_var_cols  = [f"pca_var_{i+1}"  for i in range(n_var)]
    cluster_feats = pca_mean_cols + pca_var_cols + NEURO

    df_vid = df[df["is_video"] == 1].copy()
    X      = df_vid[cluster_feats].dropna()
    idx    = X.index

    # ── Scale + K-Means (K=3) ──────────────────────────────────────────────────
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=3, random_state=RANDOM_SEED, n_init=20)
    labels = kmeans.fit_predict(X_scaled)

    df_vid.loc[idx, "cluster"] = labels
    df_vid["cluster"] = df_vid["cluster"].astype(int)

    W = 80

    # ── 1. Cross-tabulation: Cluster × Funnel → median CTR + CPM ──────────────
    print("\n" + "═" * W)
    print("  K-MEANS ARCHETYPE CLUSTERING — Video Creatives (K=3)")
    print("═" * W)

    xtab = (df_vid.loc[idx]
            .groupby(["cluster", "dominant_funnel_stage"])
            .agg(
                n       = ("CTR", "size"),
                med_CTR = ("CTR", "median"),
                med_CPM = ("CPM", "median"),
            )
            .reset_index())

    # Global cluster totals for reference
    global_tab = (df_vid.loc[idx]
                  .groupby("cluster")
                  .agg(
                      total_n = ("CTR", "size"),
                      med_CTR = ("CTR", "median"),
                      med_CPM = ("CPM", "median"),
                  )
                  .reset_index())

    print(f"\n  ┌─ Cross-Tabulation: Cluster × Funnel Stage")
    print(f"  │")
    print(f"  │  {'Cluster':>8}  {'Funnel':<16} {'N':>5}  {'Median CTR':>11}  {'Median CPM':>11}")
    print(f"  │  " + "─" * 58)

    for cluster_id in sorted(xtab["cluster"].unique()):
        rows = xtab[xtab["cluster"] == cluster_id]
        gbl  = global_tab[global_tab["cluster"] == cluster_id].iloc[0]
        for _, row in rows.iterrows():
            print(f"  │  {row['cluster']:>8}  {row['dominant_funnel_stage']:<16} "
                  f"{row['n']:>5}  {row['med_CTR']:>11.5f}  {row['med_CPM']:>11.2f}")
        print(f"  │  {'':>8}  {'── TOTAL':<16} "
              f"{gbl['total_n']:>5}  {gbl['med_CTR']:>11.5f}  {gbl['med_CPM']:>11.2f}")
        if cluster_id < xtab["cluster"].max():
            print(f"  │")

    print(f"  └{'─' * (W - 2)}")

    # ── 2. Cluster centroid profiles ───────────────────────────────────────────
    print(f"\n  ┌─ Cluster Centroid Profiles (average original-scale features)")
    print(f"  │")

    centroids = (df_vid.loc[idx]
                 .groupby("cluster")[cluster_feats]
                 .mean())

    print(f"  │  {'Feature':<24}", end="")
    for c in sorted(centroids.index):
        print(f"  {'Cluster ' + str(c):>12}", end="")
    print()
    print(f"  │  " + "─" * (24 + 14 * len(centroids)))

    for feat in cluster_feats:
        print(f"  │  {feat:<24}", end="")
        vals  = centroids[feat].values
        best  = np.argmax(np.abs(vals))
        for i, v in enumerate(vals):
            marker = " ◄" if i == best else "  "
            print(f"  {v:>+10.5f}{marker}", end="")
        print()

    print(f"  └{'─' * (W - 2)}")

    # ── 3. Archetype naming hints ──────────────────────────────────────────────
    print(f"\n  ┌─ Archetype Naming Hints")
    print(f"  │")

    for c in sorted(centroids.index):
        row  = centroids.loc[c]
        top  = row.abs().nlargest(3).index.tolist()
        tags = []
        for feat in top:
            direction = "high" if row[feat] > 0 else "low"
            tags.append(f"{feat}={direction}")

        gbl = global_tab[global_tab["cluster"] == c].iloc[0]
        perf = "TOP" if gbl["med_CTR"] == global_tab["med_CTR"].max() else \
               "LOW" if gbl["med_CTR"] == global_tab["med_CTR"].min() else "MID"

        print(f"  │  Cluster {c} ({perf} CTR) : {', '.join(tags)}")

    print(f"  └{'─' * (W - 2)}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def run_eda_step8(df: pd.DataFrame | None = None) -> None:
    print("═" * 68)
    print("  EDA Step 8 — Classification Pivot + K-Means Clustering")
    print("═" * 68)

    if df is not None:
        # Caller passed a df — write to temp and use file-based prep
        # (simpler than duplicating all prep logic for in-memory df)
        import tempfile, os
        tmp = Path(tempfile.mktemp(suffix=".csv"))
        df.to_csv(tmp, index=False)
        full_df, n_mean, n_var, funnel_cols = prepare_data(tmp)
        os.unlink(tmp)
    else:
        full_df, n_mean, n_var, funnel_cols = prepare_data(DATA)

    print(f"\n  Total rows after prep: {len(full_df):,}")
    print(f"  Images: {(full_df['is_video']==0).sum():,}  |  "
          f"Videos: {(full_df['is_video']==1).sum():,}")

    # ── Part A: Classification ─────────────────────────────────────────────────
    print("\n" + "─" * 68)
    print("[Part A] XGBClassifier — Top-Performer Detection (CTR ≥ P75)")
    print("─" * 68)
    run_classification(full_df, n_mean, n_var, funnel_cols)

    # ── Part B: Clustering ─────────────────────────────────────────────────────
    print("\n" + "─" * 68)
    print("[Part B] K-Means Archetype Clustering — Video Creatives")
    print("─" * 68)
    run_clustering(full_df, n_mean, n_var)


if __name__ == "__main__":
    run_eda_step8()
