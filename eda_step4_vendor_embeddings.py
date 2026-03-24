"""
EDA Step 4 — Vendor Embedding Feature Stability Audit
======================================================
Performs pre-modelling EDA on the 20 EEGFuseNet latent columns in df_master.csv:

  · cognitive_mean_0 … cognitive_mean_9  — Mean of each latent dimension
                                           (temporal mean for videos; static value for images)
  · cognitive_var_0  … cognitive_var_9   — Variance of each latent dimension
                                           (temporal var for videos; zero-padded for images)

Reconstruction source: fix_master_pipeline.py
  Images (4,167 rows) → mean = static embedding values | var = 0.0
  Videos (2,077 rows) → mean = arr.mean(axis=0)        | var = arr.var(axis=0, ddof=0)

Outputs:
  · eda_vendor_embeddings_histograms.png   — 4×5 histogram/KDE grid
  · Console statistical summary            — normalization bounds & outlier audit
  · Console interpretation guide           — pre-modelling scaling decision guide
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / "Havas.2" / "df_master.csv"
OUTFIG = BASE / "eda_vendor_embeddings_histograms.png"

# ── Constants ──────────────────────────────────────────────────────────────────
BLUE = "#4C9BE8"
RED  = "#E8604C"
BINS = 50


# ── 1. Load & dynamically isolate embedding columns ───────────────────────────
def load_embeddings(path: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    df = pd.read_csv(path)

    mean_cols = sorted([c for c in df.columns if c.startswith("cognitive_mean_")])
    var_cols  = sorted([c for c in df.columns if c.startswith("cognitive_var_")])

    print(f"[INFO] Dataset loaded        : {df.shape[0]:,} rows × {df.shape[1]} columns")
    print(f"[INFO] Mean cols found  (×{len(mean_cols)}) : {mean_cols}")
    print(f"[INFO] Var  cols found  (×{len(var_cols)}) : {var_cols}")
    print(f"[INFO] Zero-inflation in var cols: "
          f"{(df[var_cols] == 0).all(axis=1).mean() * 100:.1f}% of rows "
          f"(image-only creatives)\n")

    return df, mean_cols, var_cols


# ── 2. Visualisation — 4×5 histogram/KDE grid ─────────────────────────────────
def plot_histograms(df: pd.DataFrame,
                   mean_cols: list[str],
                   var_cols:  list[str]) -> None:

    fig, axes = plt.subplots(4, 5, figsize=(22, 16))
    fig.suptitle(
        "EEGFuseNet Latent Embedding Distributions — Pre-Modelling Stability Audit\n"
        "Blue: cognitive_mean (State)   |   Red: cognitive_var (Volatility, zero-padded for images)",
        fontsize=13, fontweight="bold", y=1.004
    )

    flat_axes   = axes.flatten()
    all_cols    = mean_cols + var_cols
    colours     = [BLUE] * len(mean_cols) + [RED] * len(var_cols)
    type_labels = ["Feature Mean (State)"] * len(mean_cols) + \
                  ["Feature Variance (Volatility)"] * len(var_cols)

    for idx, (col, colour, label) in enumerate(zip(all_cols, colours, type_labels)):
        ax     = flat_axes[idx]
        series = df[col].dropna()

        # For variance columns: exclude zeros to show the true video distribution
        # alongside zero spike — plot both transparently
        if col.startswith("cognitive_var_") and (series == 0).mean() > 0.3:
            # Full distribution (includes zeros → shows zero spike)
            sns.histplot(
                series,
                bins=BINS,
                color=colour,
                alpha=0.35,
                kde=False,
                ax=ax,
                label="all rows",
            )
            # Video-only overlay (non-zero rows) for the true temporal variance shape
            nonzero = series[series > 0]
            if len(nonzero) > 10:
                sns.histplot(
                    nonzero,
                    bins=BINS,
                    color=colour,
                    alpha=0.65,
                    kde=True,
                    line_kws={"linewidth": 1.8, "color": colour},
                    ax=ax,
                    label="video rows only",
                )
        else:
            sns.histplot(
                series,
                bins=BINS,
                color=colour,
                alpha=0.55,
                kde=True,
                line_kws={"linewidth": 1.8, "color": colour},
                ax=ax,
            )

        # ── Stat badges ────────────────────────────────────────────────────────
        mu       = series.mean()
        sigma    = series.std()
        pct_zero = (series == 0).mean() * 100

        stats_text = f"μ={mu:.4f}\nσ={sigma:.4f}"
        if pct_zero > 1:
            stats_text += f"\nzero={pct_zero:.1f}%"

        ax.text(
            0.97, 0.95, stats_text,
            transform=ax.transAxes,
            fontsize=7, ha="right", va="top",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.80, ec=colour),
        )

        # ── Median line (non-zero only for var cols) ───────────────────────────
        median_series = series[series > 0] if col.startswith("cognitive_var_") else series
        if len(median_series) > 0:
            ax.axvline(median_series.median(), color=colour, linewidth=1.2,
                       linestyle="--", alpha=0.8)

        # ── Labels ─────────────────────────────────────────────────────────────
        dim_num = idx % 10
        ax.set_title(f"{label} — Dim {dim_num}", fontsize=9, fontweight="bold")
        ax.set_xlabel(col, fontsize=7.5)
        ax.set_ylabel("Count", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))

    for unused in flat_axes[len(all_cols):]:
        unused.set_visible(False)

    plt.tight_layout()
    fig.savefig(OUTFIG, dpi=150, bbox_inches="tight")
    print(f"[INFO] Figure saved → {OUTFIG.name}\n")
    plt.close(fig)


# ── 3. Statistical summary ─────────────────────────────────────────────────────
def print_stats(df: pd.DataFrame, mean_cols: list[str], var_cols: list[str]) -> None:
    all_cols = mean_cols + var_cols
    stats    = df[all_cols].describe().loc[["mean", "std", "min", "50%", "max"]].T
    stats["zero_%"]      = (df[all_cols] == 0).mean().mul(100).round(2)
    stats["nonzero_std"] = pd.Series({
        col: df.loc[df[col] != 0, col].std() if col in var_cols else df[col].std()
        for col in all_cols
    })

    divider = "═" * 100
    print(divider)
    print("  COGNITIVE EMBEDDING STATISTICS — Normalization Bounds & Outlier Audit")
    print("  Source: fix_master_pipeline.py  |  Images: var=0.0 padded  |  Videos: temporal var")
    print(divider)
    print(f"\n  {'Column':<24} {'mean':>9} {'std':>9} {'min':>9} {'50%':>9} {'max':>9}"
          f" {'zero_%':>8} {'nonzero_σ':>10}")
    print("  " + "─" * 90)

    for col, row in stats.iterrows():
        flag = "  ← ⚠ zero-padded (images)" if row["zero_%"] > 50 else ""
        nz_std = f"{row['nonzero_std']:.4f}" if not np.isnan(row['nonzero_std']) else "   N/A"
        print(
            f"  {col:<24}"
            f"{row['mean']:>9.4f}"
            f"{row['std']:>9.4f}"
            f"{row['min']:>9.4f}"
            f"{row['50%']:>9.4f}"
            f"{row['max']:>9.4f}"
            f"{row['zero_%']:>7.1f}%"
            f"{nz_std:>11}"
            f"{flag}"
        )

    print("\n" + divider + "\n")


# ── 4. Interpretation guide ────────────────────────────────────────────────────
def print_interpretation() -> None:
    guide = """
╔══════════════════════════════════════════════════════════════════════════════╗
║  INTERPRETATION GUIDE — Pre-Modelling Scaling Decision                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  VARIANCE FEATURES (cognitive_var_0…9) — Red histograms                     ║
║  ──────────────────────────────────────────────────────                     ║
║  · Expect ≈66.7% zero-inflation (4,167 image rows zero-padded by design).   ║
║    Red plots show TWO layers: full distribution (zero spike) +               ║
║    video-only KDE overlay (true temporal variance shape).                    ║
║  · Check nonzero_σ column: if σ of video-only values is very small (<0.001) ║
║    the temporal dynamics are flat → low predictive signal for that dim.      ║
║  · For modelling: use a two-branch strategy OR add a binary indicator        ║
║    feature is_video=1/0 alongside the 10 var columns.                        ║
║  · Scaling: apply RobustScaler to video rows only (IQR-based, outlier-safe). ║
║    Do NOT scale the zero rows — zero-padding must remain at exactly 0.       ║
║                                                                              ║
║  MEAN FEATURES (cognitive_mean_0…9) — Blue histograms                       ║
║  ─────────────────────────────────────────────────────                      ║
║  · Values are in range [−0.22, +0.22] with σ ≈ 0.001–0.010.                ║
║    The embedding space is compact and already well-bounded.                  ║
║  · StandardScaler is safe and sufficient — no log transform needed.          ║
║  · Bimodal blue distributions indicate two distinct creative clusters        ║
║    (image vs. video modality); this is informative, not a flaw.             ║
║                                                                              ║
║  OUTLIER / SCALING DECISION RULE                                             ║
║  ────────────────────────────────                                           ║
║  · cognitive_mean_* : StandardScaler (μ≈0, σ small, no extreme outliers)    ║
║  · cognitive_var_*  : RobustScaler on video rows only; keep image zeros as-is║
║  · If max/nonzero_σ > 10 for any var dim → flag dimension for removal       ║
║    (near-constant temporal dynamics → uninformative feature).                ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(guide)


# ── Entry point ────────────────────────────────────────────────────────────────
def run_eda_step4(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df, mean_cols, var_cols = load_embeddings(DATA)
    else:
        mean_cols = sorted([c for c in df.columns if c.startswith("cognitive_mean_")])
        var_cols  = sorted([c for c in df.columns if c.startswith("cognitive_var_")])
        print(f"[INFO] Dataset received      : {df.shape[0]:,} rows × {df.shape[1]} columns")
        print(f"[INFO] Mean cols  (×{len(mean_cols)}): {mean_cols}")
        print(f"[INFO] Var  cols  (×{len(var_cols)}): {var_cols}\n")

    if not mean_cols or not var_cols:
        raise ValueError(
            "No cognitive_mean_* or cognitive_var_* columns found. "
            "Run fix_master_pipeline.py first to reconstruct df_master.csv."
        )

    plot_histograms(df, mean_cols, var_cols)
    print_stats(df, mean_cols, var_cols)
    print_interpretation()


if __name__ == "__main__":
    run_eda_step4()
