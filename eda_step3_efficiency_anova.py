"""
EDA Step 3 — Efficiency Analysis & ANOVA Proof
================================================
Tests the dissertation hypothesis:
  H₀: All funnel stages cost the same (μ_Awareness = μ_Consideration = μ_Conversion)
  H₁: At least one funnel stage has a significantly different CPM

STEP A — Efficiency Analysis
  1. Mean & Median table for CPM and CTR by dominant_funnel_stage
  2. Scatter plot: CPM vs CTR, hue = funnel stage, OLS trend line per group

STEP B — Statistical Significance
  1. Normality check per group (Shapiro-Wilk) → log-transform if needed
  2. One-Way ANOVA on (log-)CPM across the three stages
  3. Tukey HSD post-hoc test to identify which pairs differ

Usage (notebook):
    from eda_step3_efficiency_anova import run_eda_step3
    run_eda_step3(df_master)

Usage (standalone):
    python eda_step3_efficiency_anova.py
"""

import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import f_oneway, shapiro
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Configuration ──────────────────────────────────────────────────────────────

STAGE_COL   = "dominant_funnel_stage"
STAGE_ORDER = ["Awareness", "Consideration", "Conversion"]
PALETTE     = {"Awareness": "#4C72B0", "Consideration": "#55A868", "Conversion": "#C44E52"}

BACKGROUND  = "#F8F9FA"
SHAPIRO_N   = 5000
RANDOM_SEED = 42
ALPHA       = 0.05


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def clean_col(series: pd.Series) -> np.ndarray:
    arr = pd.to_numeric(series, errors="coerce").values
    return arr[np.isfinite(arr) & (arr > 0)]


def shapiro_safe(arr: np.ndarray, seed: int = RANDOM_SEED):
    """Shapiro-Wilk with sampling for large arrays."""
    if len(arr) > SHAPIRO_N:
        rng = np.random.default_rng(seed)
        arr = rng.choice(arr, size=SHAPIRO_N, replace=False)
    return shapiro(arr)


def fmt_p(p: float) -> str:
    if p < 0.001:
        return f"{p:.2e}"
    return f"{p:.4f}"


def stars(p: float) -> str:
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    return "ns"


# ══════════════════════════════════════════════════════════════════════════════
# STEP A — EFFICIENCY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def step_a_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate mean/median CPM and CTR per funnel stage."""
    known = df[df[STAGE_COL].isin(STAGE_ORDER)].copy()
    known["CPM"] = pd.to_numeric(known["CPM"], errors="coerce")
    known["CTR"] = pd.to_numeric(known["CTR"], errors="coerce")

    rows = []
    for stage in STAGE_ORDER:
        sub = known[known[STAGE_COL] == stage]
        cpm = sub["CPM"].dropna()
        ctr = sub["CTR"].dropna()
        rows.append({
            "Stage"      : stage,
            "N"          : len(sub),
            "CPM_mean"   : cpm.mean(),
            "CPM_median" : cpm.median(),
            "CTR_mean"   : ctr.mean(),
            "CTR_median" : ctr.median(),
            "CPM/CTR_ratio": cpm.mean() / ctr.mean() if ctr.mean() > 0 else np.nan,
        })

    summary = pd.DataFrame(rows).set_index("Stage")

    # ── Console table ──────────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("  STEP A — EFFICIENCY SUMMARY TABLE")
    print("═" * 72)
    header = f"  {'Stage':<16} {'N':>6}  {'CPM Mean':>10}  {'CPM Median':>11}  {'CTR Mean':>10}  {'CTR Median':>11}  {'CPM/CTR':>9}"
    print(header)
    print("  " + "─" * 68)
    for stage, row in summary.iterrows():
        print(
            f"  {stage:<16} {int(row['N']):>6}  "
            f"{row['CPM_mean']:>10.2f}  {row['CPM_median']:>11.2f}  "
            f"{row['CTR_mean']:>10.5f}  {row['CTR_median']:>11.5f}  "
            f"{row['CPM/CTR_ratio']:>9.1f}"
        )
    print("═" * 72)

    # ── Interpretation ─────────────────────────────────────────────────────────
    conv_cpm = summary.loc["Conversion", "CPM_mean"]
    awar_cpm = summary.loc["Awareness",  "CPM_mean"]
    conv_ctr = summary.loc["Conversion", "CTR_mean"]
    awar_ctr = summary.loc["Awareness",  "CTR_mean"]
    cpm_uplift = (conv_cpm - awar_cpm) / awar_cpm * 100
    ctr_uplift = (conv_ctr - awar_ctr) / awar_ctr * 100

    print(f"\n  ► Conversion costs {cpm_uplift:+.1f}% more CPM than Awareness")
    print(f"  ► Conversion has   {ctr_uplift:+.1f}% higher CTR than Awareness")
    if abs(cpm_uplift) > abs(ctr_uplift):
        print("  ► FINDING: CPM premium EXCEEDS CTR gain → cost not fully justified by clicks.")
    else:
        print("  ► FINDING: CTR gain EXCEEDS CPM premium → cost is justified by click performance.")

    return summary


def step_a_scatter(df: pd.DataFrame) -> None:
    """Scatter plot CPM vs CTR with per-stage OLS trend lines."""
    known = df[df[STAGE_COL].isin(STAGE_ORDER)].copy()
    known["CPM"] = pd.to_numeric(known["CPM"], errors="coerce")
    known["CTR"] = pd.to_numeric(known["CTR"], errors="coerce")
    known = known.dropna(subset=["CPM", "CTR"])
    known = known[(known["CPM"] > 0) & (known["CTR"] > 0)]

    # Clip to 1st–99th percentile for readability
    cpm_lo, cpm_hi = known["CPM"].quantile([0.01, 0.99])
    ctr_lo, ctr_hi = known["CTR"].quantile([0.01, 0.99])
    plot_df = known[(known["CPM"].between(cpm_lo, cpm_hi)) &
                    (known["CTR"].between(ctr_lo, ctr_hi))]

    fig, ax = plt.subplots(figsize=(13, 7), facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    for stage in STAGE_ORDER:
        sub = plot_df[plot_df[STAGE_COL] == stage]
        color = PALETTE[stage]

        # Scatter (transparent points)
        ax.scatter(sub["CPM"], sub["CTR"],
                   c=color, alpha=0.25, s=18, linewidths=0, label=f"_{stage}")

        # OLS trend line (fit in log space, draw in linear space)
        if len(sub) >= 10:
            log_cpm = np.log10(sub["CPM"])
            slope, intercept, r, p_val, _ = stats.linregress(log_cpm, sub["CTR"])
            x_range = np.linspace(sub["CPM"].min(), sub["CPM"].max(), 300)
            y_fit   = slope * np.log10(x_range) + intercept
            ax.plot(x_range, y_fit, color=color, linewidth=2.5,
                    label=f"{stage}  (r={r:.2f}, p={fmt_p(p_val)})")

    ax.set_xscale("log")
    ax.set_xlabel("CPM  (log scale)", fontsize=11, color="#444")
    ax.set_ylabel("CTR", fontsize=11, color="#444")
    ax.set_title(
        "Efficiency Analysis — CPM vs CTR by Funnel Stage\n"
        "Trend lines fitted via OLS on log₁₀(CPM). Shaded points = individual creatives.",
        fontsize=13, fontweight="bold", color="#1A1A2E", pad=10
    )
    ax.legend(fontsize=9, framealpha=0.9, loc="upper right")
    ax.tick_params(labelsize=9)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig("eda_step3a_scatter.png", dpi=180, bbox_inches="tight")
    plt.show()
    print("[INFO] Figure saved → eda_step3a_scatter.png")


# ══════════════════════════════════════════════════════════════════════════════
# STEP B — ANOVA & TUKEY HSD
# ══════════════════════════════════════════════════════════════════════════════

def step_b_normality(groups: dict) -> bool:
    """Shapiro-Wilk per group; returns True if log-transform is recommended."""
    print("\n" + "═" * 58)
    print("  STEP B-1 — NORMALITY CHECK (Shapiro-Wilk per group)")
    print("═" * 58)
    print(f"  {'Stage':<16} {'W':>8}  {'p-value':>12}  {'Normal?':>10}")
    print("  " + "─" * 52)

    any_non_normal = False
    for stage, arr in groups.items():
        w, p = shapiro_safe(arr)
        normal = p >= ALPHA
        if not normal:
            any_non_normal = True
        flag = "✓ Yes" if normal else "✗ No"
        print(f"  {stage:<16} {w:>8.4f}  {fmt_p(p):>12}  {flag:>10}")

    print("═" * 58)

    if any_non_normal:
        print("  → Non-normality detected. Applying log₁₀(CPM) transformation for ANOVA.")
        print("    (log-transform stabilises variance and satisfies ANOVA assumptions)\n")
    else:
        print("  → All groups approximately normal. Raw CPM used for ANOVA.\n")

    return any_non_normal


def step_b_anova(groups_raw: dict, groups_log: dict, use_log: bool) -> tuple:
    """One-Way ANOVA + interpretation."""
    groups = groups_log if use_log else groups_raw
    label  = "log₁₀(CPM)" if use_log else "CPM"

    f_stat, p_val = f_oneway(*groups.values())

    print("═" * 58)
    print(f"  STEP B-2 — ONE-WAY ANOVA  ({label})")
    print("═" * 58)
    print(f"  F-statistic : {f_stat:.4f}")
    print(f"  p-value     : {fmt_p(p_val)}")
    print(f"  Significance: {stars(p_val)}")
    print("─" * 58)

    if p_val < ALPHA:
        print(f"  ✓ REJECT H₀ (p = {fmt_p(p_val)} < α = {ALPHA})")
        print(f"  The mean {label} differs significantly across funnel stages.")
        print(f"  → Proceed to Tukey HSD to identify which pairs differ.")
    else:
        print(f"  ✗ FAIL TO REJECT H₀ (p = {fmt_p(p_val)} ≥ α = {ALPHA})")
        print(f"  No significant difference in {label} across funnel stages.")

    print("═" * 58)
    return f_stat, p_val, groups, label


def step_b_tukey(groups: dict, label: str) -> pd.DataFrame:
    """Tukey HSD post-hoc test using scipy."""
    from scipy.stats import tukey_hsd

    arrays = [groups[s] for s in STAGE_ORDER]
    result = tukey_hsd(*arrays)

    rows = []
    stage_pairs = [(STAGE_ORDER[i], STAGE_ORDER[j])
                   for i in range(len(STAGE_ORDER))
                   for j in range(i + 1, len(STAGE_ORDER))]

    print("\n" + "═" * 68)
    print(f"  STEP B-3 — TUKEY HSD POST-HOC  ({label})")
    print("═" * 68)
    print(f"  {'Pair':<32} {'Statistic':>10}  {'p-value':>12}  {'Sig':>5}")
    print("  " + "─" * 62)

    for i, (s1, s2) in enumerate(stage_pairs):
        idx1 = STAGE_ORDER.index(s1)
        idx2 = STAGE_ORDER.index(s2)
        p    = result.pvalue[idx1][idx2]
        stat = result.statistic[idx1][idx2]
        sig  = stars(p)
        pair_label = f"{s1} vs {s2}"
        print(f"  {pair_label:<32} {stat:>10.4f}  {fmt_p(p):>12}  {sig:>5}")
        rows.append({"Pair": pair_label, "Statistic": stat, "p-value": p, "Significance": sig})

    print("═" * 68)

    tukey_df = pd.DataFrame(rows)

    # ── Interpretation ─────────────────────────────────────────────────────────
    print("\n  INTERPRETATION:")
    for _, row in tukey_df.iterrows():
        if row["p-value"] < ALPHA:
            print(f"  ✓ {row['Pair']}: SIGNIFICANT (p={fmt_p(row['p-value'])}) {row['Significance']}")
            print(f"    → These two stages have statistically different {label} costs.")
        else:
            print(f"  ✗ {row['Pair']}: NOT significant (p={fmt_p(row['p-value'])})")
            print(f"    → No proven cost difference between these stages.")

    return tukey_df


def step_b_plot(groups_raw: dict, tukey_df: pd.DataFrame, use_log: bool) -> None:
    """Box plot of CPM by stage + Tukey significance brackets."""
    label = "log₁₀(CPM)" if use_log else "CPM"

    fig, ax = plt.subplots(figsize=(8, 6), facecolor=BACKGROUND)
    ax.set_facecolor(BACKGROUND)

    plot_data = []
    for stage in STAGE_ORDER:
        arr = np.log10(groups_raw[stage]) if use_log else groups_raw[stage]
        for v in arr:
            plot_data.append({"Stage": stage, label: v})
    plot_df = pd.DataFrame(plot_data)

    sns.boxplot(data=plot_df, x="Stage", y=label,
                order=STAGE_ORDER, palette=PALETTE,
                width=0.5, linewidth=1.5, fliersize=2,
                flierprops={"alpha": 0.3}, ax=ax)
    sns.stripplot(data=plot_df, x="Stage", y=label,
                  order=STAGE_ORDER, palette=PALETTE,
                  alpha=0.08, size=3, jitter=True, ax=ax)

    # Significance brackets
    y_max  = plot_df[label].quantile(0.98)
    y_step = (plot_df[label].max() - y_max) * 0.12 + (y_max * 0.04)
    x_pos  = {s: i for i, s in enumerate(STAGE_ORDER)}
    sig_pairs = tukey_df[tukey_df["p-value"] < ALPHA]

    for offset, (_, row) in enumerate(sig_pairs.iterrows()):
        s1, s2 = row["Pair"].split(" vs ")
        x1, x2 = x_pos[s1], x_pos[s2]
        y = y_max + y_step * (offset + 1)
        ax.plot([x1, x1, x2, x2], [y - y_step*0.3, y, y, y - y_step*0.3],
                lw=1.5, color="#333")
        ax.text((x1 + x2) / 2, y + y_step * 0.05,
                row["Significance"], ha="center", va="bottom",
                fontsize=12, fontweight="bold", color="#333")

    ax.set_title(f"CPM Distribution by Funnel Stage\n(transformed: {label})",
                 fontsize=12, fontweight="bold", color="#1A1A2E")
    ax.set_xlabel("Funnel Stage", fontsize=10, color="#444")
    ax.set_ylabel(label, fontsize=10, color="#444")
    ax.tick_params(labelsize=9)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)

    plt.tight_layout()
    plt.savefig("eda_step3b_anova.png", dpi=180, bbox_inches="tight")
    plt.show()
    print("[INFO] Figure saved → eda_step3b_anova.png")


# ══════════════════════════════════════════════════════════════════════════════
# FINAL VERDICT
# ══════════════════════════════════════════════════════════════════════════════

def print_verdict(f_stat: float, p_val: float, tukey_df: pd.DataFrame,
                  summary: pd.DataFrame, use_log: bool) -> None:
    label = "log₁₀(CPM)" if use_log else "CPM"
    sig_pairs = tukey_df[tukey_df["p-value"] < ALPHA]["Pair"].tolist()

    print("\n" + "╔" + "═" * 64 + "╗")
    print("║  DISSERTATION VERDICT                                          ║")
    print("╠" + "═" * 64 + "╣")

    if p_val < ALPHA:
        print(f"║  H₀ REJECTED  (F={f_stat:.2f}, p={fmt_p(p_val)})                     ")
        print(f"║                                                                ")
        print(f"║  The null hypothesis — that all funnel stages cost the same —  ")
        print(f"║  is OFFICIALLY REJECTED at α={ALPHA}.                            ")
        print(f"║                                                                ")
        print(f"║  Statistically significant CPM differences confirmed between:  ")
        for pair in sig_pairs:
            print(f"║    • {pair:<56}  ")
        print(f"║                                                                ")
        print(f"║  This supports the use of funnel stage as a cost predictor     ")
        print(f"║  and justifies stratified modelling in your dissertation.       ")
    else:
        print(f"║  H₀ NOT REJECTED  (F={f_stat:.2f}, p={fmt_p(p_val)})")
        print(f"║  No statistically significant CPM difference detected.")

    print("╚" + "═" * 64 + "╝\n")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def run_eda_step3(df: pd.DataFrame) -> None:
    """Main entry point. Pass df_master (must have dominant_funnel_stage, CPM, CTR)."""
    required = [STAGE_COL, "CPM", "CTR"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Filter to known stages + valid numeric CPM/CTR
    known = df[df[STAGE_COL].isin(STAGE_ORDER)].copy()
    known["CPM"] = pd.to_numeric(known["CPM"], errors="coerce")
    known["CTR"] = pd.to_numeric(known["CTR"], errors="coerce")

    # Build raw groups (positive CPM only for log-transform)
    groups_raw = {s: clean_col(known.loc[known[STAGE_COL] == s, "CPM"])
                  for s in STAGE_ORDER}
    groups_log = {s: np.log10(arr) for s, arr in groups_raw.items()}

    # ── Step A ─────────────────────────────────────────────────────────────────
    summary = step_a_summary(df)
    step_a_scatter(df)

    # ── Step B ─────────────────────────────────────────────────────────────────
    use_log          = step_b_normality(groups_raw)
    f_stat, p_val, groups_used, label = step_b_anova(groups_raw, groups_log, use_log)

    if p_val < ALPHA:
        tukey_df = step_b_tukey(groups_used, label)
    else:
        tukey_df = pd.DataFrame(columns=["Pair", "Statistic", "p-value", "Significance"])
        print("  Tukey HSD skipped — ANOVA not significant.")

    step_b_plot(groups_raw, tukey_df, use_log)
    print_verdict(f_stat, p_val, tukey_df, summary, use_log)


# ── Standalone ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    DATA_PATH = Path(__file__).parent / "Havas.2" / "df_master.csv"
    print(f"[INFO] Loading → {DATA_PATH.name}")
    df_master = pd.read_csv(DATA_PATH)
    print(f"       Shape   : {df_master.shape}")
    run_eda_step3(df_master)
