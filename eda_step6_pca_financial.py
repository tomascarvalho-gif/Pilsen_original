"""
eda_step6_pca_financial.py
==========================
PCA dimensionality reduction on the two cognitive blocks, followed by
Spearman correlation between the orthogonal components and financial targets.

Pipeline:
  1. Mean block (all 6,244 rows)
       cognitive_mean_0…9  →  StandardScaler  →  PCA(90%)  →  pca_mean_1, pca_mean_2, …

  2. Var block (video rows only, 2,077 rows)
       cognitive_var_0…9   →  StandardScaler  →  PCA(90%)  →  pca_var_1, pca_var_2, …
       Image rows get 0.0 fill (zero-padding logic preserved)

  3. Spearman correlation heatmap
       Features : all pca_mean_*, all pca_var_*, is_video
       Targets  : CTR, CPM

Output:
  · eda_financial_pca_correlation.png
  · Console: components retained, top CTR & CPM correlates
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / "Havas.2" / "df_master.csv"
OUTFIG = BASE / "eda_financial_pca_correlation.png"

# ── Column groups ──────────────────────────────────────────────────────────────
MEAN_COLS = [f"cognitive_mean_{i}" for i in range(10)]
VAR_COLS  = [f"cognitive_var_{i}"  for i in range(10)]
FINANCIAL = ["CTR", "CPM"]


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Mean block PCA  (all rows)
# ══════════════════════════════════════════════════════════════════════════════
def pca_mean_block(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    print("─" * 62)
    print("[Step 1] Mean block PCA — all rows")

    X      = df[MEAN_COLS].values
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    pca     = PCA(n_components=0.90, random_state=42)
    X_pca   = pca.fit_transform(X_sc)
    n_comp  = pca.n_components_

    ev_ratio = pca.explained_variance_ratio_
    ev_cum   = np.cumsum(ev_ratio)

    print(f"         Components retained : {n_comp}  "
          f"(explains {ev_cum[-1]*100:.2f}% of variance)")
    print(f"         Per-component EVR   :", end="")
    for i, r in enumerate(ev_ratio):
        print(f"  PC{i+1}={r*100:.1f}%", end="")
    print()

    col_names = [f"pca_mean_{i+1}" for i in range(n_comp)]
    pca_df    = pd.DataFrame(X_pca, columns=col_names, index=df.index)
    df        = pd.concat([df, pca_df], axis=1)

    return df, n_comp


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Var block PCA  (video rows only, zeros preserved for images)
# ══════════════════════════════════════════════════════════════════════════════
def pca_var_block(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    print("\n" + "─" * 62)
    print("[Step 2] Var block PCA — video rows only")

    # Identify video rows (any var column > 0)
    video_mask = (df[VAR_COLS] > 0).any(axis=1)
    n_video    = video_mask.sum()
    n_image    = (~video_mask).sum()
    print(f"         Video rows : {n_video:,}  |  Image rows (zero-filled) : {n_image:,}")

    X_vid  = df.loc[video_mask, VAR_COLS].values
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X_vid)

    pca    = PCA(n_components=0.90, random_state=42)
    X_pca  = pca.fit_transform(X_sc)
    n_comp = pca.n_components_

    ev_ratio = pca.explained_variance_ratio_
    ev_cum   = np.cumsum(ev_ratio)

    print(f"         Components retained : {n_comp}  "
          f"(explains {ev_cum[-1]*100:.2f}% of variance)")
    print(f"         Per-component EVR   :", end="")
    for i, r in enumerate(ev_ratio):
        print(f"  PC{i+1}={r*100:.1f}%", end="")
    print()

    col_names = [f"pca_var_{i+1}" for i in range(n_comp)]

    # Initialise all rows with 0.0 (preserves zero-padding for image rows)
    for col in col_names:
        df[col] = 0.0

    # Assign PCA scores to video rows only
    df.loc[video_mask, col_names] = X_pca

    return df, n_comp


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Financial Spearman correlation heatmap
# ══════════════════════════════════════════════════════════════════════════════
def compute_spearman(df: pd.DataFrame,
                     pca_mean_n: int,
                     pca_var_n:  int) -> pd.DataFrame:
    """
    Returns a DataFrame (features × targets) of Spearman rho values.
    NaNs in financial columns are dropped per-column.
    """
    feat_cols = (
        [f"pca_mean_{i+1}" for i in range(pca_mean_n)] +
        [f"pca_var_{i+1}"  for i in range(pca_var_n)]  +
        ["is_video"]
    )

    rho_dict: dict[str, dict[str, float]] = {f: {} for f in feat_cols}

    for target in FINANCIAL:
        valid = df[target].notna()
        for feat in feat_cols:
            x = df.loc[valid, feat].values
            y = df.loc[valid, target].values
            rho, _ = stats.spearmanr(x, y)
            rho_dict[feat][target] = round(rho, 4)

    return pd.DataFrame(rho_dict).T   # shape: (features × targets)


def plot_heatmap(rho_df: pd.DataFrame, pca_mean_n: int, pca_var_n: int) -> None:
    feat_cols   = list(rho_df.index)
    n_mean_feat = pca_mean_n
    n_var_feat  = pca_var_n

    # Colour the y-tick labels by block
    tick_colours = (
        ["#1A237E"] * n_mean_feat +
        ["#B71C1C"] * n_var_feat  +
        ["#1B5E20"]                  # is_video → green
    )

    fig_h = max(6, len(feat_cols) * 0.55 + 2)
    fig, ax = plt.subplots(figsize=(5, fig_h))
    fig.patch.set_facecolor("#F8F9FB")
    ax.set_facecolor("#F8F9FB")

    sns.heatmap(
        rho_df,
        annot=True,
        fmt=".3f",
        annot_kws={"size": 10, "weight": "bold"},
        cmap="coolwarm",
        vmin=-1, vmax=1,
        center=0,
        linewidths=0.8,
        linecolor="#E0E0E0",
        square=False,
        cbar_kws={"shrink": 0.6, "label": "Spearman ρ"},
        ax=ax,
    )

    # Colour y-tick labels by block
    for tick, colour in zip(ax.get_yticklabels(), tick_colours):
        tick.set_color(colour)
        tick.set_fontsize(10)
        tick.set_fontweight("bold")

    for tick in ax.get_xticklabels():
        tick.set_fontsize(11)
        tick.set_fontweight("bold")
        tick.set_rotation(0)

    # Separator lines between blocks
    ax.axhline(n_mean_feat,              color="#333", linewidth=1.8,
               linestyle="--", alpha=0.7)
    ax.axhline(n_mean_feat + n_var_feat, color="#333", linewidth=1.8,
               linestyle="--", alpha=0.7)

    # Block labels on the right margin
    def mid(start, n): return start + n / 2

    for y_mid, label, colour in [
        (mid(0,            n_mean_feat), "pca_mean\nblock", "#1A237E"),
        (mid(n_mean_feat,  n_var_feat),  "pca_var\nblock",  "#B71C1C"),
        (mid(n_mean_feat + n_var_feat, 1), "is_video",      "#1B5E20"),
    ]:
        ax.text(
            2.08, y_mid, label,
            transform=ax.get_yaxis_transform(),
            fontsize=8, color=colour, fontweight="bold",
            ha="left", va="center",
        )

    ax.set_title(
        "Spearman Correlation — PCA Components vs Financial Targets\n"
        "Blue: pca_mean_*   |   Red: pca_var_*   |   Green: is_video",
        fontsize=11, pad=12
    )
    ax.set_ylabel("")
    ax.set_xlabel("")

    plt.tight_layout()
    fig.savefig(OUTFIG, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"\n[Graph] Saved → {OUTFIG.name}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Terminal summary
# ══════════════════════════════════════════════════════════════════════════════
def print_summary(rho_df: pd.DataFrame, pca_mean_n: int, pca_var_n: int) -> None:
    divider = "═" * 62

    print("\n" + divider)
    print("  PCA SUMMARY")
    print(divider)
    print(f"  Mean block : {pca_mean_n} component(s) retained  "
          f"(pca_mean_1 … pca_mean_{pca_mean_n})")
    print(f"  Var  block : {pca_var_n} component(s) retained  "
          f"(pca_var_1  … pca_var_{pca_var_n})")
    print(f"  is_video   : binary flag (1 = video creative)")
    print(divider)

    print("\n" + divider)
    print("  FINANCIAL CORRELATION RANKINGS")
    print(divider)

    for target, direction, label in [
        ("CTR", "positive", "↑ strongest POSITIVE correlation with CTR "
                            "(features that increase click rate)"),
        ("CPM", "negative", "↓ strongest NEGATIVE correlation with CPM "
                            "(features that make ads cheaper)"),
    ]:
        col = rho_df[target].sort_values(
            ascending=(direction == "negative")
        )
        top2 = col.head(2)

        print(f"\n  {label}")
        print("  " + "─" * 58)
        for feat, rho in top2.items():
            bar_len = int(abs(rho) * 20)
            bar     = ("█" * bar_len).ljust(20)
            sign    = "+" if rho > 0 else ""
            print(f"    {feat:<18}  ρ = {sign}{rho:.4f}  {bar}")

    print("\n" + divider + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def run_eda_step6(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df = pd.read_csv(DATA)
        print("═" * 62)
        print("  EDA Step 6 — PCA + Financial Correlation")
        print("═" * 62)
        print(f"\n  Dataset : df_master.csv  ({df.shape[0]:,} × {df.shape[1]})\n")

    # Add binary is_video flag before PCA
    video_mask    = (df[VAR_COLS] > 0).any(axis=1)
    df["is_video"] = video_mask.astype(int)

    # Run PCA blocks
    df, pca_mean_n = pca_mean_block(df)
    df, pca_var_n  = pca_var_block(df)

    # Compute Spearman rho matrix
    print("\n" + "─" * 62)
    print("[Step 3] Computing Spearman correlations with CTR and CPM...")
    rho_df = compute_spearman(df, pca_mean_n, pca_var_n)

    # Plot heatmap
    plot_heatmap(rho_df, pca_mean_n, pca_var_n)

    # Print summary
    print_summary(rho_df, pca_mean_n, pca_var_n)

    return df   # return enriched df for downstream use


if __name__ == "__main__":
    run_eda_step6()
