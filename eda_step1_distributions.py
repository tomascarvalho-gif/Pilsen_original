"""
EDA Step 1 — Distribution Analysis & Normality Testing
=======================================================
Proves financial asymmetry and non-normality of dependent variables (Y)
to justify the use of non-parametric statistical methods.

Target Variables: CTR, CPM, cost, impressions, clicks
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy import stats

# ── Configuration ─────────────────────────────────────────────────────────────

TARGET_COLS    = ["CTR", "CPM", "cost", "impressions", "clicks"]
SHAPIRO_LIMIT  = 5000      # max rows for Shapiro-Wilk (scipy limitation)
RANDOM_SEED    = 42
GRID_ROWS      = 2
GRID_COLS      = 3

# Visual style
PALETTE        = "#4C72B0"
BACKGROUND     = "#F8F9FA"
TITLE_FONTSIZE = 11
LABEL_FONTSIZE = 9
FIG_TITLE      = "Distribution Analysis of Advertising Performance Metrics"

# ── Core Functions ─────────────────────────────────────────────────────────────

def clean_series(series: pd.Series) -> np.ndarray:
    """Drop NaN and infinite values, return as numpy array."""
    arr = pd.to_numeric(series, errors="coerce").values
    mask = np.isfinite(arr)
    return arr[mask]


def compute_stats(arr: np.ndarray) -> dict:
    """
    Calculate skewness (γ1) and Shapiro-Wilk p-value.
    Samples up to SHAPIRO_LIMIT rows for Shapiro-Wilk if needed.
    """
    skewness = stats.skew(arr)

    if len(arr) > SHAPIRO_LIMIT:
        rng     = np.random.default_rng(RANDOM_SEED)
        sample  = rng.choice(arr, size=SHAPIRO_LIMIT, replace=False)
    else:
        sample  = arr

    _, shapiro_p = stats.shapiro(sample)

    return {
        "n"        : len(arr),
        "skewness" : skewness,
        "shapiro_p": shapiro_p,
    }


def format_p(p: float) -> str:
    """Return a readable p-value string."""
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_distributions(df: pd.DataFrame) -> None:
    """
    Build a GRID_ROWS × GRID_COLS subplot grid.
    Each occupied cell shows a histogram + KDE with annotated statistics.
    The last cell (if unused) is hidden.
    """
    fig = plt.figure(figsize=(18, 10), facecolor=BACKGROUND)
    fig.suptitle(
        FIG_TITLE,
        fontsize=15, fontweight="bold", y=0.98,
        color="#1A1A2E"
    )

    gs = gridspec.GridSpec(
        GRID_ROWS, GRID_COLS,
        figure=fig,
        hspace=0.55, wspace=0.35,
        left=0.06, right=0.97, top=0.91, bottom=0.08
    )

    results = []   # collect for console output

    for idx, col in enumerate(TARGET_COLS):
        row, col_pos = divmod(idx, GRID_COLS)
        ax = fig.add_subplot(gs[row, col_pos])
        ax.set_facecolor(BACKGROUND)

        # ── Data ──────────────────────────────────────────────────────────────
        arr = clean_series(df[col])
        if len(arr) == 0:
            ax.text(0.5, 0.5, "No valid data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=LABEL_FONTSIZE)
            ax.set_title(col, fontsize=TITLE_FONTSIZE, fontweight="bold")
            continue

        s = compute_stats(arr)
        results.append({"Variable": col, **s})

        # ── Axis scale strategy ───────────────────────────────────────────────
        # Prefer log scale; fall back to percentile trimming if zeros/negatives
        # are present (log(0) is undefined and would break the axis).
        use_log = bool(np.all(arr > 0))

        if use_log:
            sns.histplot(
                arr, kde=True, ax=ax,
                color=PALETTE, alpha=0.65,
                log_scale=True,
                line_kws={"linewidth": 2, "color": "#E63946"},
                edgecolor="white", linewidth=0.4
            )
            x_label    = f"{col}  (log scale)"
            scale_tag  = "log₁₀ scale"
            tag_color  = "#2A6496"
            tag_bg     = "#D6EAF8"
        else:
            p1  = np.percentile(arr, 1)
            p95 = np.percentile(arr, 95)
            sns.histplot(
                arr, kde=True, ax=ax,
                color=PALETTE, alpha=0.65,
                line_kws={"linewidth": 2, "color": "#E63946"},
                edgecolor="white", linewidth=0.4
            )
            ax.set_xlim(p1, p95)
            x_label    = f"{col}  (trimmed: p1–p95)"
            scale_tag  = "trimmed p1–p95"
            tag_color  = "#7D6608"
            tag_bg     = "#FEF9E7"

        # ── Title with stats ──────────────────────────────────────────────────
        skew_sign = "+" if s["skewness"] >= 0 else ""
        title = (
            f"{col}\n"
            f"γ₁ (Skewness) = {skew_sign}{s['skewness']:.3f}   "
            f"│   Shapiro-Wilk p = {format_p(s['shapiro_p'])}"
        )
        ax.set_title(title, fontsize=TITLE_FONTSIZE, fontweight="bold",
                     color="#1A1A2E", pad=8)

        # ── Normality badge (top-right) ───────────────────────────────────────
        normality = "Non-Normal ✗" if s["shapiro_p"] < 0.05 else "Normal ✓"
        box_color = "#FFDDD2" if s["shapiro_p"] < 0.05 else "#D4EDDA"
        ax.annotate(
            normality,
            xy=(0.97, 0.93), xycoords="axes fraction",
            ha="right", va="top", fontsize=8, fontweight="bold",
            color="#E63946" if s["shapiro_p"] < 0.05 else "#2D6A4F",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=box_color,
                      edgecolor="none", alpha=0.9)
        )

        # ── Scale badge (bottom-left) ─────────────────────────────────────────
        ax.annotate(
            scale_tag,
            xy=(0.03, 0.07), xycoords="axes fraction",
            ha="left", va="bottom", fontsize=7, fontstyle="italic",
            color=tag_color,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=tag_bg,
                      edgecolor="none", alpha=0.85)
        )

        # ── Axis labels ───────────────────────────────────────────────────────
        ax.set_xlabel(x_label, fontsize=LABEL_FONTSIZE, color="#444")
        ax.set_ylabel("Count", fontsize=LABEL_FONTSIZE, color="#444")
        ax.tick_params(labelsize=8)
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)

    # ── Hide unused subplots ──────────────────────────────────────────────────
    for idx in range(len(TARGET_COLS), GRID_ROWS * GRID_COLS):
        row, col_pos = divmod(idx, GRID_COLS)
        fig.add_subplot(gs[row, col_pos]).set_visible(False)

    plt.savefig("eda_step1_distributions.png", dpi=180, bbox_inches="tight")
    plt.show()
    print("\n[INFO] Figure saved → eda_step1_distributions.png")

    return results


# ── Console Summary ────────────────────────────────────────────────────────────

def print_summary(results: list) -> None:
    """Print a formatted summary table to the console."""
    col_w = [14, 10, 12, 18, 12]
    header = (
        f"{'Variable':<{col_w[0]}}"
        f"{'N (valid)':>{col_w[1]}}"
        f"{'Skewness':>{col_w[2]}}"
        f"{'Shapiro-Wilk p':>{col_w[3]}}"
        f"{'Normality':>{col_w[4]}}"
    )
    sep = "─" * sum(col_w)

    print("\n" + "═" * sum(col_w))
    print("  EDA STEP 1 — Normality Test Summary")
    print("═" * sum(col_w))
    print(header)
    print(sep)

    for r in results:
        normality = "REJECTED" if r["shapiro_p"] < 0.05 else "NOT rejected"
        skew_str  = f"{r['skewness']:+.4f}"
        p_str     = format_p(r["shapiro_p"])
        print(
            f"{r['Variable']:<{col_w[0]}}"
            f"{r['n']:>{col_w[1]}}"
            f"{skew_str:>{col_w[2]}}"
            f"{p_str:>{col_w[3]}}"
            f"{normality:>{col_w[4]}}"
        )

    print(sep)
    print(
        "  H₀: data follows a normal distribution. "
        "Rejection at α = 0.05 justifies non-parametric methods."
    )
    print("═" * sum(col_w) + "\n")


# ── Entry Point ────────────────────────────────────────────────────────────────

def run_eda_step1(df: pd.DataFrame) -> None:
    """Main entry point. Pass your df_master DataFrame."""
    missing = [c for c in TARGET_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    results = plot_distributions(df)
    print_summary(results)


# ── Usage ──────────────────────────────────────────────────────────────────────
# In your notebook or script, call:
#
#   from eda_step1_distributions import run_eda_step1
#   run_eda_step1(df_master)
#
# Or run directly (replace the sample below with your actual df_master load):

if __name__ == "__main__":
    from pathlib import Path

    DATA_PATH = Path(__file__).parent / "Havas.2" / "df_master.csv"

    print(f"[INFO] Loading data from: {DATA_PATH}")
    df_master = pd.read_csv(DATA_PATH)
    print(f"[INFO] DataFrame shape: {df_master.shape}")

    run_eda_step1(df_master)
