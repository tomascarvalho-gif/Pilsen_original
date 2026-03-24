"""
EDA Step 2 — Stratified CPM Distribution by Funnel Stage
=========================================================
Performs three operations in sequence:

  1. ARGMAX   — derives dominant funnel stage from video percentage columns
  2. COALESCE — builds 'dominant_funnel_stage' (image label > video argmax > Unknown)
  3. PROOF    — re-plots CPM distribution from EDA Step 1, now stratified by
                funnel stage using hue, to visually prove that the distribution
                of CPM differs across Awareness / Consideration / Conversion.

Usage (notebook):
    from eda_step2_stratified_cpm import run_eda_step2
    run_eda_step2(df_master)

Usage (standalone):
    python eda_step2_stratified_cpm.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import seaborn as sns
from scipy import stats
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────

VIDEO_COLS   = ["Awareness_Percentage", "Consideration_Percentage", "Conversion_Percentage"]
IMG_COL      = "taxonomy_category"
TARGET_COL   = "dominant_funnel_stage"
PLOT_METRIC  = "CPM"
RANDOM_SEED  = 42

STAGE_ORDER  = ["Awareness", "Consideration", "Conversion"]
PALETTE      = {
    "Awareness"    : "#4C72B0",   # blue
    "Consideration": "#55A868",   # green
    "Conversion"   : "#C44E52",   # red
}

BACKGROUND   = "#F8F9FA"
TITLE_FS     = 13
LABEL_FS     = 10

# ── Step 1 & 2 — Build dominant_funnel_stage ───────────────────────────────────

def build_funnel_stage(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds (or refreshes) the dominant_funnel_stage column.

    Priority:
      1. taxonomy_category  (images — direct label)
      2. idxmax of video %  (videos — highest probability stage)
      3. 'Unknown'          (neither)
    """
    df = df.copy()

    # ── Argmax across video % columns ─────────────────────────────────────────
    has_video = df[VIDEO_COLS].notna().any(axis=1)
    video_argmax = (
        df.loc[has_video, VIDEO_COLS]
        .idxmax(axis=1)
        .str.replace("_Percentage", "", regex=False)   # 'Conversion_Percentage' → 'Conversion'
    )

    # ── Coalesce ───────────────────────────────────────────────────────────────
    df[TARGET_COL] = (
        df[IMG_COL]                              # priority 1: image label
        .where(df[IMG_COL].notna(),
               other=video_argmax.reindex(df.index))  # priority 2: video argmax
        .fillna("Unknown")                       # priority 3: fallback
    )

    # ── Console summary ────────────────────────────────────────────────────────
    counts = df[TARGET_COL].value_counts(dropna=False)
    total  = len(df)
    print("\n" + "═" * 52)
    print("  DOMINANT FUNNEL STAGE — Distribution")
    print("═" * 52)
    for stage, n in counts.items():
        bar = "█" * int(n / total * 30)
        print(f"  {str(stage):<16} {n:>5}  ({n/total*100:5.1f}%)  {bar}")
    print("═" * 52 + "\n")

    return df


# ── Step 3 — Stratified CPM Plot ───────────────────────────────────────────────

def plot_stratified_cpm(df: pd.DataFrame) -> None:
    """
    Re-draws the CPM KDE from EDA Step 1, stratified by dominant_funnel_stage.
    'Unknown' rows are excluded. Log scale applied if all CPM values > 0.
    """

    # Filter: known stages only, valid CPM values
    df_known = df[df[TARGET_COL].isin(STAGE_ORDER)].copy()
    df_known[PLOT_METRIC] = pd.to_numeric(df_known[PLOT_METRIC], errors="coerce")
    df_known = df_known[np.isfinite(df_known[PLOT_METRIC])]

    if df_known.empty:
        print("[WARN] No valid rows to plot after filtering.")
        return

    use_log   = bool((df_known[PLOT_METRIC] > 0).all())
    n_total   = len(df_known)
    n_stages  = df_known[TARGET_COL].value_counts()

    # ── Canvas ─────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 6), facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    # ── Main plot ──────────────────────────────────────────────────────────────
    sns.histplot(
        data      = df_known,
        x         = PLOT_METRIC,
        hue       = TARGET_COL,
        hue_order = STAGE_ORDER,
        palette   = PALETTE,
        kde       = True,
        log_scale = use_log,
        alpha     = 0.40,
        linewidth = 0.3,
        edgecolor = "white",
        line_kws  = {"linewidth": 2.5},
        ax        = ax,
    )

    # ── Median lines per stage ─────────────────────────────────────────────────
    for stage in STAGE_ORDER:
        sub    = df_known.loc[df_known[TARGET_COL] == stage, PLOT_METRIC]
        median = sub.median()
        ax.axvline(
            median,
            color     = PALETTE[stage],
            linewidth = 1.6,
            linestyle = "--",
            alpha     = 0.85,
            label     = f"_median_{stage}"   # suppress from legend
        )
        # Median label on the axis
        ax.text(
            median, ax.get_ylim()[1] * 0.92,
            f" {stage[:3]}\nMd={median:.1f}",
            color     = PALETTE[stage],
            fontsize  = 7.5,
            fontweight= "bold",
            va        = "top",
            ha        = "left",
        )

    # ── Title & labels ─────────────────────────────────────────────────────────
    scale_note = "log₁₀ scale" if use_log else "trimmed p1–p95"
    ax.set_title(
        f"CPM Distribution — Stratified by Funnel Stage\n"
        f"Filtered to classified rows only  (n = {n_total:,})  ·  {scale_note}",
        fontsize  = TITLE_FS,
        fontweight= "bold",
        color     = "#1A1A2E",
        pad       = 12,
    )
    ax.set_xlabel(
        f"CPM  ({'log₁₀ scale' if use_log else '1st–95th percentile'})",
        fontsize=LABEL_FS, color="#444"
    )
    ax.set_ylabel("Count", fontsize=LABEL_FS, color="#444")
    ax.tick_params(labelsize=9)

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    # ── Stage count annotation box ─────────────────────────────────────────────
    count_lines = "\n".join(
        [f"{s}: n={n_stages.get(s, 0):,}" for s in STAGE_ORDER]
    )
    ax.annotate(
        count_lines,
        xy        = (0.98, 0.97),
        xycoords  = "axes fraction",
        ha        = "right",
        va        = "top",
        fontsize  = 8,
        family    = "monospace",
        color     = "#333",
        bbox      = dict(boxstyle="round,pad=0.4", facecolor="white",
                         edgecolor="#ccc", alpha=0.9)
    )

    plt.tight_layout()
    plt.savefig("eda_step2_stratified_cpm.png", dpi=180, bbox_inches="tight")
    plt.show()
    print("[INFO] Figure saved → eda_step2_stratified_cpm.png")


# ── Entry Point ────────────────────────────────────────────────────────────────

def run_eda_step2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point. Pass df_master.
    Returns the DataFrame with dominant_funnel_stage added.
    """
    required = [IMG_COL] + VIDEO_COLS + [PLOT_METRIC]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in DataFrame: {missing}")

    df = build_funnel_stage(df)
    plot_stratified_cpm(df)
    return df


# ── Standalone ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATA_PATH = Path(__file__).parent / "Havas.2" / "df_master.csv"

    print(f"[INFO] Loading → {DATA_PATH.name}")
    df_master = pd.read_csv(DATA_PATH)
    print(f"       Shape   : {df_master.shape}")

    df_master = run_eda_step2(df_master)

    # Persist dominant_funnel_stage back to df_master.csv
    df_master.to_csv(DATA_PATH, index=False)
    print(f"[INFO] df_master saved with '{TARGET_COL}' column.")
