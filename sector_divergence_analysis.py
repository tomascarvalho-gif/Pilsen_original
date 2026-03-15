"""
Sector Divergence Analysis — Technology vs. Energy Inverse Correlation

Research Question B of the dissertation: mathematically prove the inverse
correlation and fundamental divergence between the Information Technology
and Energy sectors across distinct macroeconomic regimes.

Pipeline:
  1. GARCH(1,1)-adjusted rolling correlation between Tech and Energy sector
     returns (using SPDR Select Sector ETFs: XLK and XLE as market-cap-
     weighted proxies — standard academic practice).
  2. Market-cap-weighted P/E and ROE spread time series
     (Tech premium = Tech indicator − Energy indicator).
  3. Regime-based Welch's t-tests on the fundamental spreads.

Regimes:
  - Regime 1  "Oil Glut"           2014-06-01 to 2016-02-28
  - Regime 2  "Pandemic Shock"     2020-01-01 to 2021-12-31
  - Regime 3  "Rate Hikes"         2022-01-01 to 2023-12-31

Usage:
    python3 sector_divergence_analysis.py [--output-dir DIR]

Dependencies: pandas, numpy, yfinance, arch, scipy, matplotlib, seaborn
"""

import os
import warnings
import argparse
import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats as sp_stats
from arch import arch_model

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*arch.*")

# Full analysis window (must cover all three regimes)
START_DATE = "2013-06-01"   # 1 year before Regime 1 for GARCH burn-in
END_DATE = "2024-06-30"     # buffer after Regime 3

# Fundamental indicator lookback — must start well before Regime 1 so that
# the 4-quarter rolling window in compute_confidence_intervals() is fully
# populated by the time Regime 1 begins (2014-06-01).
# 2012-01-01 provides ~10 quarters of burn-in runway.  This also accounts
# for sparse early-XBRL filings where not every S&P 500 company had adopted
# the XBRL reporting standard yet.
INDICATOR_LOOKBACK_START = "2012-01-01"

# Sector ETF tickers (SPDR Select Sector — market-cap-weighted by design)
TECH_ETF = "XLK"
ENERGY_ETF = "XLE"
INDEX_ETF = "^GSPC"

# Sector names in the indicator CSV
TECH_SECTOR = "Information Technology"
ENERGY_SECTOR = "Energy"

# Rolling correlation window (63 trading days ≈ 1 calendar quarter)
ROLLING_WINDOW = 63

# Regime definitions
REGIMES: Dict[str, Tuple[str, str]] = {
    "Oil Glut\n(2014–2016)":        ("2014-06-01", "2016-02-28"),
    "Pandemic Shock\n(2020–2021)":  ("2020-01-01", "2021-12-31"),
    "Rate Hikes\n(2022–2023)":      ("2022-01-01", "2023-12-31"),
}

# Regime display colours (for consistent shading across all figures)
REGIME_COLORS = {
    "Oil Glut\n(2014–2016)":        "#2ecc71",   # green
    "Pandemic Shock\n(2020–2021)":  "#e74c3c",   # red
    "Rate Hikes\n(2022–2023)":      "#3498db",   # blue
}

ALPHA = 0.05

# Matplotlib publication style
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "figure.figsize": (14, 7),
})


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SECTOR PAIR RETURN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class SectorPairReturnBuilder:
    """
    Downloads daily adjusted close prices for the Technology (XLK) and
    Energy (XLE) SPDR Select Sector ETFs and the S&P 500 index (^GSPC),
    and computes daily log-return series.

    Why ETFs instead of constituent-level reconstruction?
      - SPDR Select Sector ETFs are already market-cap-weighted by design,
        matching the S&P 500 GICS sector methodology.
      - They have full price history back to 1998, covering all three regimes.
      - Constituent-level reconstruction would require survivorship-bias
        adjustment and is unnecessary for sector-level correlation analysis.
      - This is standard practice in empirical finance (e.g., Fama-French
        industry portfolio research uses similar aggregate proxies).
    """

    def __init__(self, start: str = START_DATE, end: str = END_DATE):
        self.start = start
        self.end = end
        self.prices: Optional[pd.DataFrame] = None
        self.log_returns: Optional[pd.DataFrame] = None

    def download(self) -> pd.DataFrame:
        """Download daily adjusted close prices for XLK, XLE, ^GSPC."""
        logger.info(f"Downloading daily prices for {TECH_ETF}, {ENERGY_ETF}, {INDEX_ETF}...")
        tickers = [TECH_ETF, ENERGY_ETF, INDEX_ETF]
        data = yf.download(
            tickers, start=self.start, end=self.end,
            auto_adjust=True, progress=False, threads=True,
        )

        if isinstance(data.columns, pd.MultiIndex):
            self.prices = data["Close"][tickers].copy()
        else:
            self.prices = data[["Close"]].copy()
            self.prices.columns = tickers[:1]

        self.prices = self.prices.ffill().dropna()
        logger.info(f"Price matrix: {self.prices.shape[0]} trading days")
        return self.prices

    def compute_log_returns(self) -> pd.DataFrame:
        """
        Compute daily log returns: r_t = ln(P_t / P_{t-1}).
        Log returns are time-additive and approximately normally distributed.
        """
        if self.prices is None:
            raise RuntimeError("Call download() first")
        self.log_returns = np.log(self.prices / self.prices.shift(1)).dropna()
        logger.info(f"Log-return series: {self.log_returns.shape[0]} observations")
        return self.log_returns


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SECTOR PAIR GARCH ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class SectorPairGARCH:
    """
    Fits GARCH(1,1) to the Tech and Energy daily log-return series and
    extracts standardized residuals for volatility-adjusted correlation.

    The Forbes-Rigobon (2002) critique applies to sector-pair analysis
    just as it does to sector-index: raw Pearson ρ is inflated during
    crises because both variance and covariance spike together. GARCH
    standardisation removes this confound.
    """

    SCALE = 100  # numerical stability for arch library

    def __init__(self, log_returns: pd.DataFrame):
        self.log_returns = log_returns
        self.results: Dict[str, object] = {}
        self.std_resid: Optional[pd.DataFrame] = None

    def _fit_one(self, series: pd.Series, name: str) -> Optional[object]:
        """Fit GARCH(1,1) to a single series."""
        scaled = series.dropna() * self.SCALE
        if len(scaled) < 252:  # need at least ~1 year
            logger.warning(f"GARCH: insufficient data for '{name}' ({len(scaled)} obs)")
            return None
        try:
            model = arch_model(
                scaled, mean="Constant", vol="GARCH",
                p=1, q=1, dist="Normal", rescale=False,
            )
            res = model.fit(disp="off", show_warning=False)
            logger.info(
                f"GARCH({name}): omega={res.params['omega']:.4f}, "
                f"alpha={res.params['alpha[1]']:.4f}, "
                f"beta={res.params['beta[1]']:.4f}"
            )
            return res
        except Exception as e:
            logger.warning(f"GARCH fit failed for '{name}': {e}")
            return None

    def fit(self):
        """Fit GARCH(1,1) to both Tech (XLK) and Energy (XLE) series."""
        logger.info("Fitting GARCH(1,1) to Tech and Energy return series...")
        for ticker in [TECH_ETF, ENERGY_ETF]:
            if ticker in self.log_returns.columns:
                res = self._fit_one(self.log_returns[ticker], ticker)
                if res is not None:
                    self.results[ticker] = res
        if len(self.results) < 2:
            raise RuntimeError("GARCH fitting failed for one or both sectors")

    def get_standardized_residuals(self) -> pd.DataFrame:
        """
        Extract standardized residuals ε_t = (r_t − μ) / σ_t.
        Returns a DataFrame with columns [XLK, XLE], aligned on dates.
        """
        resid_dict = {}
        for ticker in [TECH_ETF, ENERGY_ETF]:
            resid_dict[ticker] = self.results[ticker].std_resid

        self.std_resid = pd.DataFrame(resid_dict).dropna()
        logger.info(f"Standardized residuals: {self.std_resid.shape[0]} aligned observations")
        return self.std_resid

    def compute_rolling_correlation(self, window: int = ROLLING_WINDOW) -> pd.Series:
        """
        Compute rolling Pearson correlation between Tech and Energy
        GARCH-standardized residuals.

        Returns a pd.Series indexed by date.
        """
        if self.std_resid is None:
            self.get_standardized_residuals()
        rolling = (
            self.std_resid[TECH_ETF]
            .rolling(window)
            .corr(self.std_resid[ENERGY_ETF])
        )
        rolling.name = "rho_tech_energy"
        logger.info(f"Rolling correlation ({window}-day): {rolling.notna().sum()} valid values")
        return rolling


# ═══════════════════════════════════════════════════════════════════════════════
# 3. FUNDAMENTAL SPREAD ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class FundamentalSpreadAnalyzer:
    """
    Reads the sanitized, market-cap-weighted indicator data and computes
    the Tech–Energy "premium spread" for P/E and ROE.

    Data source priority:
      1. covid_analysis_output/sector_indicators.csv (Phase 1 output)
      2. If the CSV lacks coverage for earlier regimes (e.g., Oil Glut
         2014–2016), extends the data by re-running the existing
         IndicatorDivergenceAnalyzer pipeline with a wider date window.
         This reuses the Phase 1 infrastructure (including the Winsorization
         filters) — no new JSON parsing logic is written.
    """

    def __init__(
        self,
        csv_path: str = "covid_analysis_output/sector_indicators.csv",
        json_dir: str = "xbrl_data_json",
    ):
        self.csv_path = csv_path
        self.json_dir = json_dir
        self.indicators: Optional[pd.DataFrame] = None
        self.spreads: Optional[pd.DataFrame] = None

    def _load_csv(self) -> pd.DataFrame:
        """Load the Phase 1 indicator CSV."""
        df = pd.read_csv(self.csv_path, parse_dates=["date"])
        logger.info(
            f"Loaded {len(df)} rows from {self.csv_path} "
            f"(date range: {df['date'].min().date()} to {df['date'].max().date()})"
        )
        return df

    def _extend_coverage(self, earliest_needed: str) -> pd.DataFrame:
        """
        Regenerate the indicator CSV with an extended date window using the
        existing IndicatorDivergenceAnalyzer from covid_impact_analysis.py.

        This reuses the Phase 1 Winsorization pipeline — no new raw-JSON
        parsing code is introduced.
        """
        logger.info(
            f"CSV lacks data before {earliest_needed}. "
            "Extending coverage via IndicatorDivergenceAnalyzer..."
        )
        # Import here to avoid circular dependency at module level
        import covid_impact_analysis as cia
        from info_picker_2 import download_SP500_data

        # Get sector mapping
        raw_sectors = download_SP500_data()
        ticker_to_sector = {
            t: info["sector"]
            for t, info in raw_sectors.items()
            if isinstance(info, dict) and "sector" in info
        }

        # Temporarily override the module-level date boundaries
        original_start = cia.START_DATE
        original_end = cia.END_DATE
        cia.START_DATE = earliest_needed
        cia.END_DATE = END_DATE

        analyzer = cia.IndicatorDivergenceAnalyzer(
            json_dir=self.json_dir,
            sp500_sectors=ticker_to_sector,
        )
        analyzer.load_quarterly_indicators()
        analyzer.aggregate_by_sector_mcap()
        analyzer.compute_confidence_intervals()

        # Restore original boundaries
        cia.START_DATE = original_start
        cia.END_DATE = original_end

        extended = analyzer.sector_agg.copy()
        if "quarter" in extended.columns:
            extended["quarter"] = extended["quarter"].astype(str)

        # Persist the extended CSV for reproducibility
        extended.to_csv(self.csv_path, index=False, float_format="%.4f")
        logger.info(
            f"Extended CSV saved ({len(extended)} rows, "
            f"{extended['date'].min()} to {extended['date'].max()})"
        )
        return extended

    def load_indicators(self) -> pd.DataFrame:
        """
        Load indicator data, extending the date range if necessary to
        cover all three regimes.

        The IndicatorDivergenceAnalyzer's 4-quarter rolling CI window
        requires substantial burn-in *before* the first regime begins.
        Regime 1 (Oil Glut) starts 2014-06-01, so the data must begin
        no later than 2012-01-01 to guarantee that:
          - The quarterly sector aggregates are populated from 2012Q1,
          - The 4-quarter rolling window is fully primed by 2013Q1,
          - Regime 1 (2014Q3–2016Q1, ~7 quarters) has full spread data.
        """
        earliest_needed = INDICATOR_LOOKBACK_START

        if os.path.exists(self.csv_path):
            df = self._load_csv()
            csv_min = df["date"].min()
            if csv_min <= pd.Timestamp(earliest_needed):
                self.indicators = df
                return df
            logger.info(
                f"CSV starts at {csv_min.date()}, need {earliest_needed}. Extending..."
            )

        # Extend (or generate from scratch if CSV missing)
        df = self._extend_coverage(earliest_needed)
        df["date"] = pd.to_datetime(df["date"])
        self.indicators = df
        return df

    def compute_spreads(self) -> pd.DataFrame:
        """
        Compute the Tech Premium Spread:
            Spread_{P/E,t} = P/E_{Tech,t} − P/E_{Energy,t}
            Spread_{ROE,t} = ROE_{Tech,t} − ROE_{Energy,t}

        Returns a DataFrame indexed by date with spread columns.
        """
        if self.indicators is None:
            raise RuntimeError("Call load_indicators() first")

        tech = (
            self.indicators[self.indicators["sector"] == TECH_SECTOR]
            .set_index("date")[["weighted_P/E", "weighted_ROE"]]
            .rename(columns={"weighted_P/E": "PE_tech", "weighted_ROE": "ROE_tech"})
        )
        energy = (
            self.indicators[self.indicators["sector"] == ENERGY_SECTOR]
            .set_index("date")[["weighted_P/E", "weighted_ROE"]]
            .rename(columns={"weighted_P/E": "PE_energy", "weighted_ROE": "ROE_energy"})
        )

        merged = tech.join(energy, how="inner").sort_index()
        merged["Spread_PE"] = merged["PE_tech"] - merged["PE_energy"]
        merged["Spread_ROE"] = merged["ROE_tech"] - merged["ROE_energy"]

        self.spreads = merged
        logger.info(
            f"Spread series: {len(self.spreads)} quarters "
            f"({self.spreads.index.min().date()} to {self.spreads.index.max().date()})"
        )
        return self.spreads


# ═══════════════════════════════════════════════════════════════════════════════
# 4. REGIME ANALYZER — Welch's t-tests
# ═══════════════════════════════════════════════════════════════════════════════

class RegimeAnalyzer:
    """
    Assigns quarterly spread observations to macroeconomic regimes and
    performs Welch's t-tests (unequal variance) to compare the Tech
    Premium Spread across regime pairs.

    Welch's t-test is preferred over Student's t-test because:
      - Regime durations differ (unequal sample sizes).
      - Variance of spreads almost certainly differs across regimes
        (heteroskedasticity is expected given the distinct macro environments).
      - Welch's test does not assume equal variance and uses the
        Welch-Satterthwaite degrees-of-freedom approximation.
    """

    def __init__(self, spreads: pd.DataFrame, regimes: Dict[str, Tuple[str, str]] = REGIMES):
        self.spreads = spreads
        self.regimes = regimes
        self.regime_data: Dict[str, pd.DataFrame] = {}
        self.test_results: Optional[pd.DataFrame] = None

    def assign_regimes(self) -> Dict[str, pd.DataFrame]:
        """
        Slice the spread data into regime-specific subsets.

        Rows are kept if EITHER Spread_PE or Spread_ROE is non-NaN
        (how='all').  This is critical for the Oil Glut regime where
        Energy P/E is systematically NaN (negative earnings → Winsorized
        out) but ROE is valid.  The Welch t-tests in run_welch_tests()
        handle per-indicator NaN independently via column-level dropna.
        """
        for regime_name, (start, end) in self.regimes.items():
            mask = (self.spreads.index >= start) & (self.spreads.index <= end)
            subset = self.spreads.loc[mask].dropna(
                subset=["Spread_PE", "Spread_ROE"], how="all",
            )
            self.regime_data[regime_name] = subset
            n_pe = subset["Spread_PE"].notna().sum()
            n_roe = subset["Spread_ROE"].notna().sum()
            logger.info(
                f"Regime '{regime_name}': {len(subset)} quarters "
                f"(P/E valid: {n_pe}, ROE valid: {n_roe})"
            )
        return self.regime_data

    def run_welch_tests(self) -> pd.DataFrame:
        """
        Perform Welch's t-tests comparing adjacent regimes:
          - Regime 1 (Oil Glut)      vs. Regime 2 (Pandemic)
          - Regime 2 (Pandemic)      vs. Regime 3 (Rate Hikes)

        For both Spread_{P/E} and Spread_{ROE}.

        Returns a DataFrame with columns:
            comparison, indicator, mean_1, mean_2, t_stat, p_value,
            df (Welch-Satterthwaite), significant
        """
        if not self.regime_data:
            self.assign_regimes()

        regime_names = list(self.regimes.keys())
        pairs = [
            (regime_names[0], regime_names[1]),
            (regime_names[1], regime_names[2]),
        ]

        records = []
        for r1_name, r2_name in pairs:
            r1 = self.regime_data[r1_name]
            r2 = self.regime_data[r2_name]

            for spread_col, label in [("Spread_PE", "P/E Spread"), ("Spread_ROE", "ROE Spread")]:
                s1 = r1[spread_col].dropna()
                s2 = r2[spread_col].dropna()

                if len(s1) < 2 or len(s2) < 2:
                    logger.warning(
                        f"Insufficient data for Welch's t-test: "
                        f"{r1_name} vs {r2_name} ({label}): n1={len(s1)}, n2={len(s2)}"
                    )
                    records.append({
                        "Comparison": f"{r1_name}  vs.  {r2_name}",
                        "Indicator": label,
                        "Mean_1": s1.mean() if len(s1) else np.nan,
                        "Mean_2": s2.mean() if len(s2) else np.nan,
                        "n_1": len(s1),
                        "n_2": len(s2),
                        "t_stat": np.nan,
                        "p_value": np.nan,
                        "df_welch": np.nan,
                        "Significant": False,
                    })
                    continue

                # Welch's t-test (unequal variance)
                t_stat, p_value = sp_stats.ttest_ind(s1, s2, equal_var=False)

                # Welch-Satterthwaite degrees of freedom (for reporting)
                v1, v2 = s1.var(ddof=1), s2.var(ddof=1)
                n1, n2 = len(s1), len(s2)
                if v1 == 0 and v2 == 0:
                    df_ws = n1 + n2 - 2
                else:
                    num = (v1 / n1 + v2 / n2) ** 2
                    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
                    df_ws = num / den if den > 0 else n1 + n2 - 2

                records.append({
                    "Comparison": f"{r1_name}  vs.  {r2_name}",
                    "Indicator": label,
                    "Mean_1": s1.mean(),
                    "Mean_2": s2.mean(),
                    "n_1": n1,
                    "n_2": n2,
                    "t_stat": t_stat,
                    "p_value": p_value,
                    "df_welch": df_ws,
                    "Significant": p_value < ALPHA,
                })

                sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "n.s."
                logger.info(
                    f"Welch t-test  {label:12s}  {r1_name} vs {r2_name}: "
                    f"t={t_stat:+.3f}, p={p_value:.4f} {sig}"
                )

        self.test_results = pd.DataFrame(records)
        return self.test_results


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SECTOR DIVERGENCE REPORT — Orchestrator & Visualization
# ═══════════════════════════════════════════════════════════════════════════════

class SectorDivergenceReport:
    """
    Orchestrator for the full Technology vs. Energy sector divergence
    analysis.  Runs the pipeline and generates three publication-quality
    figures and one CSV table.
    """

    def __init__(self, output_dir: str = "sector_divergence_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.return_builder: Optional[SectorPairReturnBuilder] = None
        self.garch: Optional[SectorPairGARCH] = None
        self.spread_analyzer: Optional[FundamentalSpreadAnalyzer] = None
        self.regime_analyzer: Optional[RegimeAnalyzer] = None
        self.rolling_corr: Optional[pd.Series] = None

    def run(self):
        """Execute the full sector divergence pipeline."""
        logger.info("=" * 80)
        logger.info("SECTOR DIVERGENCE ANALYSIS — Technology vs. Energy")
        logger.info("=" * 80)

        # ── Stage 1: Daily returns & GARCH ──
        logger.info("\n── Stage 1/4: Daily returns & GARCH(1,1) ──")
        self.return_builder = SectorPairReturnBuilder()
        self.return_builder.download()
        self.return_builder.compute_log_returns()

        self.garch = SectorPairGARCH(self.return_builder.log_returns)
        self.garch.fit()
        self.rolling_corr = self.garch.compute_rolling_correlation()

        # ── Stage 2: Fundamental spreads ──
        logger.info("\n── Stage 2/4: Fundamental P/E and ROE spreads ──")
        self.spread_analyzer = FundamentalSpreadAnalyzer()
        self.spread_analyzer.load_indicators()
        self.spread_analyzer.compute_spreads()

        # ── Stage 3: Regime-based Welch's t-tests ──
        logger.info("\n── Stage 3/4: Regime analysis & Welch's t-tests ──")
        self.regime_analyzer = RegimeAnalyzer(self.spread_analyzer.spreads)
        self.regime_analyzer.assign_regimes()
        self.regime_analyzer.run_welch_tests()

        # ── Stage 4: Visualisation & export ──
        logger.info("\n── Stage 4/4: Generating figures and tables ──")
        self.plot_tech_energy_correlation()
        self.plot_premium_spreads()
        self.plot_regime_boxplots()
        self.export_tables()

        logger.info("=" * 80)
        logger.info(f"Pipeline complete.  Outputs in: {self.output_dir}/")
        logger.info("=" * 80)

    # ── Shared helpers ─────────────────────────────────────────────────────

    def _shade_regimes(self, ax: plt.Axes):
        """Add colour-coded regime shading to an axis."""
        for regime_name, (start, end) in REGIMES.items():
            color = REGIME_COLORS[regime_name]
            # Clean label for legend (remove newline)
            label = regime_name.replace("\n", " ")
            ax.axvspan(
                pd.Timestamp(start), pd.Timestamp(end),
                alpha=0.15, color=color, label=label,
            )

    # ── Figure 1: Rolling correlation ──────────────────────────────────────

    def plot_tech_energy_correlation(self):
        """
        Fig 1: 63-day rolling Pearson correlation between GARCH-standardized
        residuals of Technology (XLK) and Energy (XLE).
        """
        fig, ax = plt.subplots(figsize=(14, 6))

        series = self.rolling_corr.dropna()
        ax.plot(series.index, series.values, color="#2c3e50", linewidth=1.0)

        self._shade_regimes(ax)

        ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.6)
        ax.set_ylabel("Pearson ρ  (GARCH-standardized residuals)")
        ax.set_title(
            f"Technology vs. Energy: {ROLLING_WINDOW}-Day Rolling Correlation\n"
            "(GARCH(1,1) Volatility-Adjusted — Forbes-Rigobon Corrected)",
            fontweight="bold",
        )
        ax.set_ylim(-0.6, 1.0)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())

        # De-duplicate legend entries
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc="lower left", framealpha=0.9)

        path = os.path.join(self.output_dir, "fig1_tech_energy_correlation.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    # ── Figure 2: Premium spreads ──────────────────────────────────────────

    def plot_premium_spreads(self):
        """
        Fig 2: Dual-axis time-series of the Tech Premium Spread for P/E
        (left axis) and ROE (right axis), with regime shading.
        """
        spreads = self.spread_analyzer.spreads

        fig, ax1 = plt.subplots(figsize=(14, 7))
        ax2 = ax1.twinx()

        # P/E spread on left axis
        color_pe = "#e74c3c"
        ax1.plot(
            spreads.index, spreads["Spread_PE"],
            color=color_pe, linewidth=1.8, marker="o", markersize=3,
            label="Spread$_{P/E}$  (Tech − Energy)",
        )
        ax1.set_ylabel("P/E Spread  (Tech − Energy)", color=color_pe)
        ax1.tick_params(axis="y", labelcolor=color_pe)

        # ROE spread on right axis
        color_roe = "#2980b9"
        ax2.plot(
            spreads.index, spreads["Spread_ROE"],
            color=color_roe, linewidth=1.8, marker="s", markersize=3,
            label="Spread$_{ROE}$  (Tech − Energy)",
        )
        ax2.set_ylabel("ROE Spread (pp)  (Tech − Energy)", color=color_roe)
        ax2.tick_params(axis="y", labelcolor=color_roe)

        self._shade_regimes(ax1)

        ax1.axhline(y=0, color="gray", linestyle="--", linewidth=0.6)

        ax1.set_title(
            "Tech Premium Spread: Valuation (P/E) and Profitability (ROE)\n"
            "Market-Cap-Weighted, Winsorized Sector Aggregates",
            fontweight="bold",
        )
        ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax1.xaxis.set_major_locator(mdates.YearLocator())

        # Combined legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        # Filter out duplicate regime labels
        seen = set()
        combined_lines, combined_labels = [], []
        for line, label in zip(lines1 + lines2, labels1 + labels2):
            if label not in seen:
                combined_lines.append(line)
                combined_labels.append(label)
                seen.add(label)
        ax1.legend(combined_lines, combined_labels, loc="upper left", framealpha=0.9)

        path = os.path.join(self.output_dir, "fig2_premium_spreads.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    # ── Figure 3: Regime boxplots ──────────────────────────────────────────

    def plot_regime_boxplots(self):
        """
        Fig 3: Side-by-side boxplots comparing the distribution of the
        Tech Premium Spread (P/E and ROE) across the three regimes.
        """
        regime_data = self.regime_analyzer.regime_data
        regime_names = list(REGIMES.keys())

        fig, (ax_pe, ax_roe) = plt.subplots(1, 2, figsize=(14, 7))

        for ax, spread_col, title, ylabel in [
            (ax_pe, "Spread_PE", "P/E Spread Distribution", "P/E Spread (Tech − Energy)"),
            (ax_roe, "Spread_ROE", "ROE Spread Distribution", "ROE Spread (pp) (Tech − Energy)"),
        ]:
            box_data = []
            box_labels = []
            box_colors = []
            for rname in regime_names:
                vals = regime_data[rname][spread_col].dropna().values
                box_data.append(vals)
                box_labels.append(rname)
                box_colors.append(REGIME_COLORS[rname])

            bp = ax.boxplot(
                box_data,
                tick_labels=box_labels,
                patch_artist=True,
                widths=0.5,
                showmeans=True,
                meanprops=dict(marker="D", markerfacecolor="black", markersize=6),
                medianprops=dict(color="black", linewidth=1.5),
                flierprops=dict(marker="o", markersize=4, alpha=0.5),
            )
            for patch, color in zip(bp["boxes"], box_colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)

            # Overlay individual data points
            for i, (vals, color) in enumerate(zip(box_data, box_colors)):
                jitter = np.random.default_rng(42).uniform(-0.12, 0.12, len(vals))
                ax.scatter(
                    np.full_like(vals, i + 1) + jitter, vals,
                    color=color, alpha=0.7, s=25, edgecolors="white", linewidth=0.5,
                    zorder=5,
                )

            ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.6)
            ax.set_title(title, fontweight="bold")
            ax.set_ylabel(ylabel)
            ax.tick_params(axis="x", labelsize=8)

            # Annotate with sample size
            for i, rname in enumerate(regime_names):
                n = len(regime_data[rname][spread_col].dropna())
                ax.text(i + 1, ax.get_ylim()[0], f"n={n}",
                        ha="center", va="bottom", fontsize=8, color="gray")

        fig.suptitle(
            "Tech Premium Spread by Macroeconomic Regime\n"
            "(◆ = mean, ─ = median)",
            fontweight="bold", fontsize=13,
        )

        path = os.path.join(self.output_dir, "fig3_regime_boxplots.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    # ── CSV export ─────────────────────────────────────────────────────────

    def export_tables(self):
        """Export Welch's t-test results as a CSV."""
        if self.regime_analyzer.test_results is not None:
            path = os.path.join(self.output_dir, "welchs_t_test_results.csv")
            self.regime_analyzer.test_results.to_csv(path, index=False, float_format="%.4f")
            logger.info(f"Exported: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Sector Divergence Analysis: Technology vs. Energy",
    )
    parser.add_argument(
        "--output-dir",
        default="sector_divergence_output",
        help="Directory for output figures and tables (default: sector_divergence_output/)",
    )
    args = parser.parse_args()

    report = SectorDivergenceReport(output_dir=args.output_dir)
    report.run()


if __name__ == "__main__":
    main()
