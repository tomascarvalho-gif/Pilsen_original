"""
eda_step5_cognitive_audit.py
============================
Feature Audit (EDA) for the 20-dimensional EEGFuseNet cognitive vector
in df_master.csv, prior to feeding them into a predictive model.

Columns audited:
  cognitive_mean_0 … cognitive_mean_9  — Static cognitive state (blue)
  cognitive_var_0  … cognitive_var_9   — Temporal volatility (red; zero-padded for images)

Outputs:
  · eda_cognitive_distributions.png   — 4×5 histogram/KDE grid
  · eda_cognitive_collinearity.png    — 20×20 Spearman heatmap (lower triangle)
  · Console                           — Transposed describe() + collinearity WARNING alerts
"""

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# ── Paths & constants ──────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
DATA   = BASE / "Havas.2" / "df_master.csv"
FIG1   = BASE / "eda_cognitive_distributions.png"
FIG2   = BASE / "eda_cognitive_collinearity.png"

N_DIMS           = 10
BLUE             = "#4C9BE8"
RED              = "#E8604C"
BINS             = 60
COLLINEARITY_THR = 0.85          # |ρ| threshold for WARNING alert


# ── Load data ──────────────────────────────────────────────────────────────────
def load_cognitive(path: Path) -> tuple[pd.DataFrame, list[str], list[str]]:
    df        = pd.read_csv(path)
    mean_cols = sorted(c for c in df.columns if c.startswith("cognitive_mean_"))
    var_cols  = sorted(c for c in df.columns if c.startswith("cognitive_var_"))

    if len(mean_cols) != N_DIMS or len(var_cols) != N_DIMS:
        raise ValueError(
            f"Expected {N_DIMS} mean and {N_DIMS} var columns. "
            f"Found {len(mean_cols)} mean, {len(var_cols)} var. "
            "Run fix_master_pipeline.py to reconstruct df_master.csv."
        )

    print("═" * 72)
    print("  EDA Step 5 — Cognitive Feature Audit")
    print("═" * 72)
    print(f"\n  Dataset : {path.name}  ({df.shape[0]:,} rows × {df.shape[1]} cols)")
    print(f"  Mean cols ({len(mean_cols)}): {mean_cols}")
    print(f"  Var  cols ({len(var_cols)}): {var_cols}")
    zero_pct = (df[var_cols] == 0).all(axis=1).mean() * 100
    print(f"  Zero-inflation in var cols : {zero_pct:.1f}% rows "
          f"(image creatives, by design)\n")

    return df, mean_cols, var_cols


# ══════════════════════════════════════════════════════════════════════════════
# Graph 1 — Distribution Matrix (4×5)
# ══════════════════════════════════════════════════════════════════════════════
def plot_distributions(df: pd.DataFrame,
                       mean_cols: list[str],
                       var_cols:  list[str]) -> None:

    all_cols    = mean_cols + var_cols
    colours     = [BLUE] * N_DIMS + [RED] * N_DIMS
    is_var      = [False] * N_DIMS + [True] * N_DIMS

    fig, axes = plt.subplots(4, 5, figsize=(24, 16))
    fig.patch.set_facecolor("#F8F9FB")
    fig.suptitle(
        "Cognitive Embedding Distributions — Pre-Modelling Feature Audit\n"
        r"$\bf{Blue}$: cognitive_mean (static state) "
        r"  |  "
        r"$\bf{Red}$: cognitive_var (temporal volatility, zero-padded for images)",
        fontsize=13, y=1.005
    )

    for idx, (col, colour, var_flag) in enumerate(zip(all_cols, colours, is_var)):
        ax     = axes.flatten()[idx]
        series = df[col].dropna()
        dim    = idx % N_DIMS

        ax.set_facecolor("#FAFAFA")

        if var_flag:
            # ── Variance column: two-layer plot ───────────────────────────────
            # Layer 1: full distribution (shows zero spike in light colour)
            sns.histplot(series, bins=BINS, color=colour, alpha=0.20,
                         kde=False, ax=ax)

            # Layer 2: video-only rows (non-zero), with KDE
            nonzero = series[series > 0]
            if len(nonzero) >= 10:
                sns.histplot(nonzero, bins=BINS, color=colour, alpha=0.65,
                             kde=True,
                             line_kws={"linewidth": 2.0, "color": colour},
                             ax=ax)

            # Scientific notation on x-axis for tiny var values
            ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.1e"))
            ax.tick_params(axis="x", labelsize=6.5, rotation=20)

            # Stats badge (non-zero rows for meaningful stats)
            mu_nz  = nonzero.mean() if len(nonzero) > 0 else 0.0
            sd_nz  = nonzero.std()  if len(nonzero) > 0 else 0.0
            zero_p = (series == 0).mean() * 100
            badge  = f"μ={mu_nz:.2e}\nσ={sd_nz:.2e}\nzero={zero_p:.0f}%"

            # Median line (video rows only)
            if len(nonzero) > 0:
                ax.axvline(nonzero.median(), color=colour,
                           linewidth=1.3, linestyle="--", alpha=0.9)
        else:
            # ── Mean column: standard histogram + KDE ─────────────────────────
            sns.histplot(series, bins=BINS, color=colour, alpha=0.55,
                         kde=True,
                         line_kws={"linewidth": 2.0, "color": colour},
                         ax=ax)

            ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
            ax.tick_params(axis="x", labelsize=7.5)
            ax.axvline(series.median(), color=colour,
                       linewidth=1.3, linestyle="--", alpha=0.9)

            mu_nz = series.mean()
            sd_nz = series.std()
            badge = f"μ={mu_nz:.4f}\nσ={sd_nz:.4f}"

        # ── Stat badge ────────────────────────────────────────────────────────
        ax.text(0.97, 0.97, badge,
                transform=ax.transAxes, fontsize=7,
                ha="right", va="top",
                bbox=dict(boxstyle="round,pad=0.3",
                          fc="white", alpha=0.85, ec=colour))

        # ── Title & labels ────────────────────────────────────────────────────
        kind  = "Mean" if not var_flag else "Var"
        ax.set_title(f"cognitive_{kind.lower()}_{dim}", fontsize=9,
                     fontweight="bold",
                     color="#1A237E" if not var_flag else "#B71C1C")
        ax.set_xlabel("")
        ax.set_ylabel("Count", fontsize=7.5)
        ax.tick_params(axis="y", labelsize=7)
        for spine in ax.spines.values():
            spine.set_edgecolor("#CCCCCC")

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(FIG1, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"[Graph 1] Saved → {FIG1.name}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Graph 2 — Spearman Collinearity Heatmap (20×20, lower triangle)
# ══════════════════════════════════════════════════════════════════════════════
def plot_collinearity(df: pd.DataFrame,
                      mean_cols: list[str],
                      var_cols:  list[str]) -> pd.DataFrame:

    all_cols = mean_cols + var_cols

    # Compute Spearman correlation matrix
    rho = df[all_cols].corr(method="spearman")

    # Lower-triangle mask (hide upper + diagonal)
    mask = np.triu(np.ones_like(rho, dtype=bool), k=0)

    # Tick label colours: blue for mean dims, red for var dims
    tick_colours = ["#1A237E"] * N_DIMS + ["#B71C1C"] * N_DIMS

    fig, ax = plt.subplots(figsize=(16, 13))
    fig.patch.set_facecolor("#F8F9FB")
    ax.set_facecolor("#F8F9FB")

    sns.heatmap(
        rho,
        mask=mask,
        annot=True,
        fmt=".2f",
        annot_kws={"size": 6.5},
        cmap="RdBu_r",
        vmin=-1, vmax=1,
        center=0,
        linewidths=0.4,
        linecolor="#E0E0E0",
        square=True,
        cbar_kws={"shrink": 0.7, "label": "Spearman ρ"},
        ax=ax,
    )

    # Colour tick labels by block
    for tick, colour in zip(ax.get_xticklabels(), tick_colours):
        tick.set_color(colour)
        tick.set_fontsize(7.5)
        tick.set_rotation(45)
        tick.set_ha("right")

    for tick, colour in zip(ax.get_yticklabels(), tick_colours):
        tick.set_color(colour)
        tick.set_fontsize(7.5)
        tick.set_rotation(0)

    # Block separator lines (mean block | var block)
    ax.axhline(N_DIMS, color="#333333", linewidth=2.0, linestyle="--", alpha=0.6)
    ax.axvline(N_DIMS, color="#333333", linewidth=2.0, linestyle="--", alpha=0.6)

    # Block annotations
    ax.text(N_DIMS / 2, -0.8, "cognitive_mean block",
            ha="center", va="bottom", fontsize=9,
            color="#1A237E", fontweight="bold",
            transform=ax.get_xaxis_transform())
    ax.text(N_DIMS + N_DIMS / 2, -0.8, "cognitive_var block",
            ha="center", va="bottom", fontsize=9,
            color="#B71C1C", fontweight="bold",
            transform=ax.get_xaxis_transform())

    ax.set_title(
        "Spearman Collinearity Heatmap — 20 Cognitive Features\n"
        "Blue labels: cognitive_mean_*   |   Red labels: cognitive_var_*   |"
        "   Dashed line: block boundary",
        fontsize=12, pad=14
    )

    plt.tight_layout()
    fig.savefig(FIG2, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"[Graph 2] Saved → {FIG2.name}")
    plt.close(fig)

    return rho


# ══════════════════════════════════════════════════════════════════════════════
# Terminal Output — Describe table + Collinearity alerts
# ══════════════════════════════════════════════════════════════════════════════
def print_describe(df: pd.DataFrame, mean_cols: list[str], var_cols: list[str]) -> None:
    all_cols = mean_cols + var_cols
    desc     = df[all_cols].describe().loc[["mean", "std", "min", "25%", "50%", "75%", "max"]].T

    divider = "═" * 90
    print("\n" + divider)
    print("  DESCRIBE TABLE — Cognitive Feature Scales (transposed)")
    print(divider)
    print(f"\n  {'Column':<24} {'mean':>11} {'std':>11} {'min':>11} "
          f"{'25%':>11} {'50%':>11} {'75%':>11} {'max':>11}")
    print("  " + "─" * 84)

    for i, (col, row) in enumerate(desc.iterrows()):
        # Block separator between mean and var sections
        if i == N_DIMS:
            print("  " + "┄" * 84)

        # Scientific notation for variance columns (values ≈ 1e-5 to 1e-4)
        if col.startswith("cognitive_var_"):
            fmt = lambda v: f"{v:.3e}"
        else:
            fmt = lambda v: f"{v:.6f}"

        print(
            f"  {col:<24} "
            f"{fmt(row['mean']):>11} "
            f"{fmt(row['std']):>11} "
            f"{fmt(row['min']):>11} "
            f"{fmt(row['25%']):>11} "
            f"{fmt(row['50%']):>11} "
            f"{fmt(row['75%']):>11} "
            f"{fmt(row['max']):>11}"
        )

    print("\n" + divider + "\n")


def print_collinearity_alerts(rho: pd.DataFrame,
                               mean_cols: list[str],
                               var_cols:  list[str]) -> None:
    all_cols = mean_cols + var_cols
    divider  = "═" * 72

    print(divider)
    print("  COLLINEARITY AUDIT — Spearman |ρ| > {:.2f} Pairs".format(COLLINEARITY_THR))
    print(divider)

    high_pairs: list[tuple[str, str, float, str]] = []

    for i in range(len(all_cols)):
        for j in range(i + 1, len(all_cols)):
            col_a = all_cols[i]
            col_b = all_cols[j]
            rho_val = rho.loc[col_a, col_b]
            if abs(rho_val) > COLLINEARITY_THR:
                # Classify the pair type
                both_mean = col_a.startswith("cognitive_mean_") and \
                            col_b.startswith("cognitive_mean_")
                both_var  = col_a.startswith("cognitive_var_") and \
                            col_b.startswith("cognitive_var_")
                pair_type = ("mean–mean" if both_mean
                             else "var–var" if both_var
                             else "mean–var (cross-block)")
                high_pairs.append((col_a, col_b, rho_val, pair_type))

    if not high_pairs:
        print(f"\n  ✅  No collinear pairs found above |ρ| = {COLLINEARITY_THR}.")
        print("      All 20 cognitive dimensions are sufficiently independent.\n")
    else:
        # Sort by |ρ| descending
        high_pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        print(f"\n  ⚠️  WARNING — {len(high_pairs)} collinear pair(s) detected!\n")
        print(f"  {'Pair':<44} {'ρ':>7}  {'Block type'}")
        print("  " + "─" * 68)

        for col_a, col_b, rho_val, ptype in high_pairs:
            arrow = "↑" if rho_val > 0 else "↓"
            print(f"  {col_a:<22} ↔  {col_b:<22} {rho_val:>+.4f} {arrow}  [{ptype}]")

        print()
        # ── Structured recommendation block ───────────────────────────────────
        mean_mean_pairs = [p for p in high_pairs if p[3] == "mean–mean"]
        var_var_pairs   = [p for p in high_pairs if p[3] == "var–var"]
        cross_pairs     = [p for p in high_pairs if "cross" in p[3]]

        print("  RECOMMENDATION:")
        if mean_mean_pairs:
            dims = sorted(set(
                int(c.split("_")[-1])
                for p in mean_mean_pairs for c in [p[0], p[1]]
            ))
            print(f"  · cognitive_mean dims {dims} are redundant.")
            print(f"    → Apply PCA or drop lowest-variance dimension(s) before modelling.")
        if var_var_pairs:
            dims = sorted(set(
                int(c.split("_")[-1])
                for p in var_var_pairs for c in [p[0], p[1]]
            ))
            print(f"  · cognitive_var dims {dims} share high temporal co-movement.")
            print(f"    → Consider reducing via PCA on video rows only (exclude zero-padded).")
        if cross_pairs:
            print(f"  · Cross-block collinearity detected (mean–var pairs).")
            print(f"    → Investigate whether mean and var are encoding the same latent signal.")
        print()

    print(divider + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════
def run_eda_step5(df: pd.DataFrame | None = None) -> None:
    if df is None:
        df, mean_cols, var_cols = load_cognitive(DATA)
    else:
        mean_cols = sorted(c for c in df.columns if c.startswith("cognitive_mean_"))
        var_cols  = sorted(c for c in df.columns if c.startswith("cognitive_var_"))
        print("═" * 72)
        print("  EDA Step 5 — Cognitive Feature Audit")
        print("═" * 72)
        print(f"\n  Dataset received: {df.shape[0]:,} rows × {df.shape[1]} cols")
        zero_pct = (df[var_cols] == 0).all(axis=1).mean() * 100
        print(f"  Zero-inflation in var cols: {zero_pct:.1f}% (image creatives)\n")

    # ── Run all three components ───────────────────────────────────────────────
    plot_distributions(df, mean_cols, var_cols)
    rho = plot_collinearity(df, mean_cols, var_cols)
    print_describe(df, mean_cols, var_cols)
    print_collinearity_alerts(rho, mean_cols, var_cols)


if __name__ == "__main__":
    run_eda_step5()
