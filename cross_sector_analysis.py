"""
Cross-Sector Correlation Shifts (COVID-19) — Exploratory Question 3

This module identifies which sector-to-sector relationships experienced a
statistically significant structural break during the COVID-19 pandemic by
testing all unique pairwise correlations across the 11 GICS sectors.

Methodology:
  1. Reuse the GARCH(1,1) standardized residuals from Phase 1 (Question A),
     which remove the Forbes-Rigobon (2002) volatility-induced correlation bias.
  2. Compute the full 11×11 Pearson correlation matrix for two regimes:
         Pre-COVID  (2018-01-01 to 2019-12-31)
         COVID Shock (2020-01-01 to 2021-12-31)
  3. Compute the Delta Matrix: Δρ = ρ_covid − ρ_pre.
  4. Apply the Fisher z-transformation hypothesis test (H0: ρ_pre = ρ_covid)
     to every unique sector pair (55 tests for 11 sectors).
  5. Visualise only statistically significant shifts (α = 0.05).

Output (in cross_sector_output/):
  - fig1_delta_significance_heatmap.png
  - significant_shifts.csv

Usage:
    python3 cross_sector_analysis.py [--output-dir DIR] [--no-download]

Dependencies: pandas, numpy, yfinance, arch, scipy, matplotlib, seaborn
"""

import os
import warnings
import argparse
import logging
from typing import Dict, Optional, Tuple
from itertools import combinations

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from scipy import stats as sp_stats

# Reuse Phase 1 infrastructure for GARCH residuals
from covid_impact_analysis import (
    SectorReturnBuilder,
    GARCHVolatilityAnalyzer,
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Suppress noisy warnings from yfinance and arch
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*arch.*")

# Analysis window (must cover both regimes + allow GARCH burn-in)
START_DATE = "2018-01-01"
END_DATE = "2021-12-31"

# Regime definitions
REGIMES: Dict[str, Tuple[str, str]] = {
    "Pre-COVID":   ("2018-01-01", "2019-12-31"),
    "COVID Shock": ("2020-01-01", "2021-12-31"),
}

# Significance level
ALPHA = 0.05

# Matplotlib style
sns.set_theme(style="whitegrid", font_scale=1.1)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CROSS-SECTOR CORRELATION ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class CrossSectorCorrelationAnalyzer:
    """
    Computes the full 11×11 sector-to-sector Pearson correlation matrices
    on GARCH-standardized residuals for two regimes, then derives the
    delta matrix Δρ = ρ_covid − ρ_pre.
    """

    def __init__(
        self,
        std_residuals: pd.DataFrame,
        regimes: Dict[str, Tuple[str, str]] = REGIMES,
    ):
        self.residuals = std_residuals
        self.regimes = regimes
        self.sectors = sorted(std_residuals.columns.tolist())
        self.corr_matrices: Dict[str, pd.DataFrame] = {}
        self.n_obs: Dict[str, int] = {}
        self.delta_matrix: Optional[pd.DataFrame] = None

    def compute_regime_correlations(self) -> Dict[str, pd.DataFrame]:
        """
        Compute the full Pearson correlation matrix for each regime.

        Returns
        -------
        Dict mapping regime name → 11×11 correlation DataFrame.
        """
        logger.info("Computing cross-sector correlation matrices …")

        for regime_name, (start, end) in self.regimes.items():
            mask = (self.residuals.index >= start) & (self.residuals.index <= end)
            regime_data = self.residuals.loc[mask, self.sectors].dropna()

            n = len(regime_data)
            self.n_obs[regime_name] = n
            logger.info(f"  {regime_name}: {n} trading days, {len(self.sectors)} sectors")

            if n < 30:
                logger.warning(f"  {regime_name}: only {n} observations — correlation unreliable")

            self.corr_matrices[regime_name] = regime_data.corr(method="pearson")

        return self.corr_matrices

    def compute_delta_matrix(self) -> pd.DataFrame:
        """
        Δρ = ρ_covid − ρ_pre

        Positive Δρ → sectors became *more* correlated during COVID (coupling).
        Negative Δρ → sectors became *less* correlated (decoupling).
        """
        regime_names = list(self.regimes.keys())
        if len(regime_names) < 2:
            raise RuntimeError("Need at least 2 regimes to compute delta")

        pre_name = regime_names[0]
        covid_name = regime_names[1]

        self.delta_matrix = self.corr_matrices[covid_name] - self.corr_matrices[pre_name]
        logger.info(
            f"Delta matrix computed: Δρ = ρ_{covid_name} − ρ_{pre_name}  "
            f"(range: [{self.delta_matrix.min().min():.3f}, {self.delta_matrix.max().max():.3f}])"
        )
        return self.delta_matrix


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MATRIX-WIDE FISHER Z-TEST
# ═══════════════════════════════════════════════════════════════════════════════

class PairwiseFisherZTester:
    """
    Applies the Fisher z-transformation hypothesis test to every unique
    sector pair (C(11,2) = 55 tests).

    H0: ρ_pre(A,B) = ρ_covid(A,B)
    """

    def __init__(
        self,
        corr_matrices: Dict[str, pd.DataFrame],
        n_obs: Dict[str, int],
        sectors: list,
        alpha: float = ALPHA,
    ):
        self.corr_matrices = corr_matrices
        self.n_obs = n_obs
        self.sectors = sectors
        self.alpha = alpha
        self.pvalue_matrix: Optional[pd.DataFrame] = None
        self.zstat_matrix: Optional[pd.DataFrame] = None
        self.results_df: Optional[pd.DataFrame] = None

    @staticmethod
    def fisher_z_test(
        r1: float, n1: int, r2: float, n2: int
    ) -> Tuple[float, float]:
        """
        Test H0: ρ1 = ρ2 using the Fisher z-transformation.

        z_i = arctanh(r_i)
        Z = (z1 − z2) / √(1/(n1−3) + 1/(n2−3))
        Two-sided p-value from N(0,1).
        """
        r1 = np.clip(r1, -0.9999, 0.9999)
        r2 = np.clip(r2, -0.9999, 0.9999)

        z1 = np.arctanh(r1)
        z2 = np.arctanh(r2)

        se = np.sqrt(1.0 / (n1 - 3) + 1.0 / (n2 - 3))
        z_stat = (z1 - z2) / se
        p_value = 2.0 * sp_stats.norm.sf(abs(z_stat))
        return z_stat, p_value

    def run_all_tests(self) -> pd.DataFrame:
        """
        Apply Fisher z-test to every unique (sector_A, sector_B) pair.

        Populates:
            self.pvalue_matrix  — 11×11 symmetric p-value matrix
            self.zstat_matrix   — 11×11 symmetric Z-statistic matrix
            self.results_df     — Long-form table of all pair results

        Returns
        -------
        results_df with columns:
            Sector_A, Sector_B, rho_pre, rho_covid, delta_rho,
            z_stat, p_value, significant
        """
        regime_names = list(self.corr_matrices.keys())
        pre_name = regime_names[0]
        covid_name = regime_names[1]
        n_pre = self.n_obs[pre_name]
        n_covid = self.n_obs[covid_name]

        corr_pre = self.corr_matrices[pre_name]
        corr_covid = self.corr_matrices[covid_name]

        n_sectors = len(self.sectors)
        pval_mat = pd.DataFrame(
            np.ones((n_sectors, n_sectors)),
            index=self.sectors, columns=self.sectors,
        )
        zstat_mat = pd.DataFrame(
            np.zeros((n_sectors, n_sectors)),
            index=self.sectors, columns=self.sectors,
        )

        records = []

        for s_a, s_b in combinations(self.sectors, 2):
            r_pre = corr_pre.loc[s_a, s_b]
            r_covid = corr_covid.loc[s_a, s_b]

            if np.isnan(r_pre) or np.isnan(r_covid):
                continue

            z_stat, p_val = self.fisher_z_test(r_pre, n_pre, r_covid, n_covid)

            pval_mat.loc[s_a, s_b] = p_val
            pval_mat.loc[s_b, s_a] = p_val
            zstat_mat.loc[s_a, s_b] = z_stat
            zstat_mat.loc[s_b, s_a] = -z_stat  # antisymmetric for z-stat sign

            records.append({
                "Sector_A": s_a,
                "Sector_B": s_b,
                "rho_pre": round(r_pre, 4),
                "rho_covid": round(r_covid, 4),
                "delta_rho": round(r_covid - r_pre, 4),
                "z_stat": round(z_stat, 4),
                "p_value": round(p_val, 6),
                "significant": p_val < self.alpha,
            })

        # Diagonal: self-correlation, set p-value to NaN (not testable)
        for s in self.sectors:
            pval_mat.loc[s, s] = np.nan
            zstat_mat.loc[s, s] = np.nan

        self.pvalue_matrix = pval_mat
        self.zstat_matrix = zstat_mat
        self.results_df = pd.DataFrame(records)

        n_sig = self.results_df["significant"].sum()
        n_total = len(self.results_df)
        logger.info(
            f"Fisher z-tests complete: {n_sig}/{n_total} pairs significant at α={self.alpha}"
        )
        return self.results_df


# ═══════════════════════════════════════════════════════════════════════════════
# 3. VISUALISATION & REPORT
# ═══════════════════════════════════════════════════════════════════════════════

class CrossSectorReport:
    """
    Orchestrates the full pipeline and generates outputs.
    """

    def __init__(self, output_dir: str = "cross_sector_output", skip_download: bool = False):
        self.output_dir = output_dir
        self.skip_download = skip_download
        os.makedirs(output_dir, exist_ok=True)

    # ── Heatmap ───────────────────────────────────────────────────────────

    def _plot_delta_significance_heatmap(
        self,
        delta_matrix: pd.DataFrame,
        pvalue_matrix: pd.DataFrame,
        n_pre: int,
        n_covid: int,
    ) -> None:
        """
        Plot the Δρ matrix as a diverging heatmap.

        Non-significant pairs (p ≥ 0.05) are masked and shown in gray.
        The diagonal is also masked (self-correlation is always 1).
        """
        # Shorten long sector names for readability
        short_names = {
            "Communication Services": "Comm Svc",
            "Consumer Discretionary": "Cons Disc",
            "Consumer Staples": "Cons Stap",
            "Health Care": "Health",
            "Information Technology": "Info Tech",
            "Real Estate": "Real Est",
            "Financials": "Financials",
            "Industrials": "Industrials",
            "Materials": "Materials",
            "Energy": "Energy",
            "Utilities": "Utilities",
        }

        sectors = delta_matrix.columns.tolist()
        labels = [short_names.get(s, s) for s in sectors]

        # Build significance mask: True where p >= alpha OR diagonal
        sig_mask = pvalue_matrix.values >= ALPHA
        np.fill_diagonal(sig_mask, True)

        # Data for the heatmap — mask non-significant cells
        data = delta_matrix.values.copy()
        data_masked = np.where(sig_mask, np.nan, data)

        # Determine symmetric colour limits
        vmax = np.nanmax(np.abs(data_masked)) if not np.all(np.isnan(data_masked)) else 0.3
        vmax = max(vmax, 0.05)  # minimum range

        fig, ax = plt.subplots(figsize=(13, 10.5))

        # First layer: gray background for non-significant cells
        gray_data = np.where(sig_mask & ~np.eye(len(sectors), dtype=bool), 0, np.nan)
        sns.heatmap(
            gray_data,
            ax=ax,
            cmap=["#e0e0e0"],
            cbar=False,
            xticklabels=labels,
            yticklabels=labels,
            linewidths=0.5,
            linecolor="white",
            square=True,
        )

        # Second layer: significant cells with diverging colourmap
        sns.heatmap(
            data_masked,
            ax=ax,
            cmap="RdBu_r",      # Red = negative (decoupling), Blue = positive (coupling)
            center=0,
            vmin=-vmax,
            vmax=vmax,
            annot=True,
            fmt=".2f",
            annot_kws={"size": 8, "fontweight": "bold"},
            xticklabels=labels,
            yticklabels=labels,
            linewidths=0.5,
            linecolor="white",
            square=True,
            cbar_kws={
                "label": "Δρ  (ρ_COVID − ρ_Pre-COVID)",
                "shrink": 0.75,
            },
            mask=np.isnan(data_masked),
        )

        # Diagonal: mark with a distinct pattern
        for i in range(len(sectors)):
            ax.add_patch(plt.Rectangle((i, i), 1, 1, fill=True,
                                       facecolor="#404040",
                                       linewidth=0.5, edgecolor="white"))

        # Cross-hatch pattern on non-significant off-diagonal cells
        for i in range(len(sectors)):
            for j in range(len(sectors)):
                if i != j and sig_mask[i, j]:
                    ax.add_patch(plt.Rectangle(
                        (j, i), 1, 1, fill=False,
                        hatch="//", edgecolor="#999999", linewidth=0,
                    ))

        ax.set_title(
            "Cross-Sector Correlation Shift: Δρ = ρ$_{COVID}$ − ρ$_{Pre-COVID}$\n"
            f"(GARCH-adjusted  |  Pre: n={n_pre}  |  COVID: n={n_covid}  |  "
            f"Gray / hatched = not significant at α={ALPHA})",
            fontsize=13,
            pad=15,
        )

        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
        ax.set_yticklabels(labels, rotation=0, fontsize=9)

        # Legend patches
        legend_handles = [
            mpatches.Patch(facecolor="#d73027", label="Coupling (Δρ > 0)"),
            mpatches.Patch(facecolor="#4575b4", label="Decoupling (Δρ < 0)"),
            mpatches.Patch(facecolor="#e0e0e0", hatch="//", edgecolor="#999",
                           label=f"Not significant (p ≥ {ALPHA})"),
            mpatches.Patch(facecolor="#404040", label="Diagonal (self)"),
        ]
        ax.legend(
            handles=legend_handles,
            loc="lower left",
            fontsize=8.5,
            framealpha=0.9,
        )

        fig.tight_layout()
        outpath = os.path.join(self.output_dir, "fig1_delta_significance_heatmap.png")
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved: {outpath}")

    # ── CSV export ────────────────────────────────────────────────────────

    def _export_significant_shifts(self, results_df: pd.DataFrame) -> None:
        """Export only significant pairs, sorted by |Z-statistic|."""
        sig = results_df[results_df["significant"]].copy()
        sig["abs_z"] = sig["z_stat"].abs()
        sig.sort_values("abs_z", ascending=False, inplace=True)
        sig.drop(columns=["abs_z", "significant"], inplace=True)

        outpath = os.path.join(self.output_dir, "significant_shifts.csv")
        sig.to_csv(outpath, index=False)
        logger.info(f"Saved: {outpath}  ({len(sig)} significant pairs)")
        if not sig.empty:
            logger.info(f"\n{sig.to_string(index=False)}")

    # ── Main pipeline ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full cross-sector analysis pipeline."""
        logger.info("=" * 72)
        logger.info("CROSS-SECTOR CORRELATION SHIFTS — EXPLORATORY QUESTION 3")
        logger.info("=" * 72)

        # ── Step 1: Build sector returns (reuse Phase 1 infrastructure) ──
        builder = SectorReturnBuilder(start=START_DATE, end=END_DATE)
        builder.load_sp500_sectors()

        if not self.skip_download:
            builder.download_daily_prices()
            builder.download_market_caps()
        else:
            raise NotImplementedError("--no-download requires cached data (not implemented)")

        builder.compute_sector_returns()
        index_returns = builder.get_sp500_index_returns()

        # ── Step 2: GARCH(1,1) standardized residuals ──
        garch = GARCHVolatilityAnalyzer(
            sector_returns=builder.sector_returns,
            index_returns=index_returns,
        )
        garch.fit_all()
        sector_resid, _ = garch.get_standardized_residuals()

        logger.info(f"GARCH residual sectors: {sorted(sector_resid.columns.tolist())}")

        # ── Step 3: Cross-sector correlation matrices ──
        analyzer = CrossSectorCorrelationAnalyzer(
            std_residuals=sector_resid,
            regimes=REGIMES,
        )
        analyzer.compute_regime_correlations()
        analyzer.compute_delta_matrix()

        # ── Step 4: Pairwise Fisher z-tests ──
        tester = PairwiseFisherZTester(
            corr_matrices=analyzer.corr_matrices,
            n_obs=analyzer.n_obs,
            sectors=analyzer.sectors,
        )
        results = tester.run_all_tests()

        # ── Step 5: Outputs ──
        regime_names = list(REGIMES.keys())
        self._plot_delta_significance_heatmap(
            delta_matrix=analyzer.delta_matrix,
            pvalue_matrix=tester.pvalue_matrix,
            n_pre=analyzer.n_obs[regime_names[0]],
            n_covid=analyzer.n_obs[regime_names[1]],
        )
        self._export_significant_shifts(results)

        logger.info("\n" + "=" * 72)
        logger.info("CROSS-SECTOR ANALYSIS COMPLETE")
        logger.info("=" * 72)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Cross-Sector Correlation Shifts (COVID-19) — Q3",
    )
    parser.add_argument(
        "--output-dir",
        default="cross_sector_output",
        help="Directory for output figures and tables (default: cross_sector_output/)",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip Yahoo Finance downloads (use cached data).",
    )
    args = parser.parse_args()

    report = CrossSectorReport(
        output_dir=args.output_dir,
        skip_download=args.no_download,
    )
    report.run()


if __name__ == "__main__":
    main()
