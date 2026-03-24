# Correlation Methodology Audit Report
**Project:** Synapsee / Havas Q1 2026 Dissertation
**Date:** 2026-03-06
**Status:** CRITICAL — Pearson correlation used throughout non-normal data

---

## 1. AUDIT FINDINGS — Infected Files

### Category A: Pearson (Explicit — `method='pearson'` or `pearsonr()`)
These files explicitly named Pearson, leaving no ambiguity:

| File | Line(s) | Code |
|------|---------|------|
| `analyze_correlations.py` | 48, 58 | `.corr(method='pearson')` |
| `fluency_from_excel.py` | 56 | `pearsonr(df_clean[neural], df_clean[perf_metric])` |
| `fluency_eval.py` | 87, 162 | `pearsonr(df_final[m], df_final['CTR'])` |
| `GAIA/analyze_advanced.py` | 112, 130 | `.corr(method='pearson')` |
| `Havas.2/phase2_analysis.py` | 49 | `pearsonr(clean_df[var], clean_df[target])` |
| `Havas.2/havas_analysis.py` | 102, 126 | `.corr(method='pearson')` + heatmap |
| `Havas.2/verify_5sec_hypothesis.py` | 46 | `pearsonr(df[f], df[target])` |
| `Tunad/tunad_timeline_analysis.py` | 17 | `pearsonr(clean_df[f], clean_df[target])` |
| `Havas/havas_analisar.ipynb` | cells 8, 16 | `pearsonr(...)` × 4 calls |
| `Tunad/tunad_analisar.ipynb` | cells 6–12, 40 | `pearsonr(...)` × 10+ calls |

### Category B: Pearson (Silent Default — `.corr()` with no method argument)
`pandas.DataFrame.corr()` defaults to `method='pearson'` when no argument is given.
These files never declared Pearson but are running it silently:

| File | Line(s) | Code |
|------|---------|------|
| `GAIA/analyze_excel.py` | 23 | `df[numeric_cols].corr()` |
| `GAIA/processar.ipynb` | cell 12 | `df_valid[cols].corr().iloc[0, 1]` |
| `analise_excel_itau.ipynb` | cells 10, 14 | `df_final[cols].corr()` |
| `analise_excel_natura.ipynb` | cells 8, 11 | `df_final[cols].corr()` |
| `estudo_base.ipynb` | cells 4–11 | `.corr(numeric_only=True)` × 6 calls |
| `Tunad/processar_e_analisar.ipynb` | cells 8–12 | `x.corr(y)` (Series default) |

### Category C: Correct Usage (Spearman already present)
| File | Notes |
|------|-------|
| `GAIA/analyze_correlations.py` | Runs both — but **returns Pearson matrix** (line 101) |
| `Tunad/tunad_analisar.ipynb` | Compares both in plot titles — valid for diagnostic use |

---

## 2. THE CRITICAL FIX — One-Line Change

For every `.corr()` call in the project:

```python
# ❌ WRONG — Pearson is the silent default
df[cols].corr()
df[cols].corr(method='pearson')

# ✅ CORRECT — Spearman for non-normal, skewed data
df[cols].corr(method='spearman')
```

For every `pearsonr()` call:

```python
# ❌ WRONG
from scipy.stats import pearsonr
r, p = pearsonr(x, y)

# ✅ CORRECT
from scipy.stats import spearmanr
r, p = spearmanr(x, y)
```

---

## 3. DISSERTATION TEXT — Academic Explanation

### The Flaw: Why Pearson Correlation Is Mathematically Invalid for This Dataset

The application of Pearson's product-moment correlation coefficient (r) to the present
dataset constitutes a fundamental methodological error that systematically invalidates
any linear association findings derived from it. Pearson's r is predicated on four
classical assumptions: (1) a linear relationship between the variables, (2) bivariate
normality, (3) homoscedasticity, and (4) the absence of influential outliers. The
Exploratory Data Analysis conducted in Step 1 of this study — through Shapiro-Wilk
tests (all p-values < 0.001) and skewness coefficients routinely exceeding γ₁ > 5.0
for variables including CTR, CPM, cost, impressions, and clicks — categorically
demonstrates that none of these assumptions are met. The distributions are
characterised by extreme positive (right) skew consistent with a power-law or
log-normal generative process, a structural property of advertising performance
data where a small number of creatives capture a disproportionate share of
impressions and clicks. Under these conditions, the Pearson coefficient is
algebraically dominated by the squared deviations of outlier observations. A single
high-spend, high-impression creative can artificially inflate or deflate r by several
tenths of a point, producing "phantom correlations" — statistically significant
associations that reflect the leverage of extreme values rather than any true
monotonic relationship present in the bulk of the distribution. This renders every
Pearson-derived r value in the preceding analyses both numerically unstable and
substantively uninterpretable.

### The Solution: Why Spearman's Rank-Order Correlation Is Required

The methodologically appropriate alternative for this dataset is Spearman's
rank-order correlation coefficient (ρ), which must replace all Pearson computations
throughout this study. Spearman's ρ operates by first transforming raw metric values
into their ordinal ranks, then computing Pearson's r on those ranks. This rank
transformation produces two critical properties that directly address the pathologies
identified above. First, it is entirely insensitive to the magnitude of extreme values:
whether a creative receives 100,000 impressions or 100,000,000, it is assigned a
rank, and that rank's influence on ρ is bounded. Second, Spearman's ρ tests for
monotonic association — the broader, more appropriate question of whether higher
values of one variable tend to correspond to higher values of another — rather than
requiring the narrow and violated assumption of linearity. For advertising performance
data, which is structurally non-normal and governed by multiplicative rather than
additive processes, monotonicity is both the theoretically justified and empirically
testable relationship. The transition to Spearman's ρ therefore does not represent
a statistical concession; it represents the adoption of a more rigorous and
assumption-consistent methodology. All correlation coefficients reported in the
subsequent modelling chapters of this dissertation are computed exclusively using
Spearman's rank-order method (scipy.stats.spearmanr; pandas .corr(method='spearman')),
and prior Pearson-based findings from the exploratory phase are explicitly
superseded by these corrected values.

---

## 4. SUMMARY TABLE FOR DISSERTATION APPENDIX

| Script / Notebook | Method Used | Status | Action Required |
|---|---|---|---|
| `analyze_correlations.py` | Pearson (explicit) | ❌ Invalid | Replace with `method='spearman'` |
| `fluency_from_excel.py` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `fluency_eval.py` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `GAIA/analyze_excel.py` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
| `GAIA/analyze_advanced.py` | Pearson (explicit) | ❌ Invalid | Replace with `method='spearman'` |
| `GAIA/analyze_correlations.py` | Both (returns Pearson) | ⚠️ Partial | Return Spearman matrix |
| `Havas.2/phase2_analysis.py` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `Havas.2/havas_analysis.py` | Pearson (explicit) + heatmap | ❌ Invalid | Replace method + regenerate heatmap |
| `Havas.2/verify_5sec_hypothesis.py` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `Tunad/tunad_timeline_analysis.py` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `GAIA/processar.ipynb` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
| `analise_excel_itau.ipynb` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
| `analise_excel_natura.ipynb` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
| `estudo_base.ipynb` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
| `Havas/havas_analisar.ipynb` | Pearson (explicit) | ❌ Invalid | Replace `pearsonr` → `spearmanr` |
| `Tunad/tunad_analisar.ipynb` | Both (diagnostic) | ⚠️ Partial | Retain Spearman, remove Pearson from final results |
| `Tunad/processar_e_analisar.ipynb` | Pearson (default) | ❌ Invalid | Add `method='spearman'` |
