"""
COVID-19 Impact Analysis — Sector–Index Correlation Structural Break Testing

This module implements a rigorous econometric pipeline for a PhD dissertation
analyzing whether the correlation between GICS sector returns and S&P 500
index returns experienced a statistically significant structural break during
the COVID-19 pandemic.

Methodology:
  1. Market-cap-weighted sector return construction from daily adjusted close prices.
  2. GARCH(1,1) volatility modelling to extract standardized residuals, removing
     the Forbes-Rigobon (2002) upward bias in correlations during volatile periods.
  3. Fisher z-transformation hypothesis testing (H0: ρ_pre = ρ_covid) at α = 0.05.
  4. Rolling correlation of GARCH-standardized residuals as a proxy for time-varying
     conditional correlation (first stage of DCC-GARCH, Engle 2002).
  5. Market-cap-weighted P/E and ROE divergence with bootstrapped confidence intervals.

Usage:
    python3 covid_impact_analysis.py [--output-dir DIR] [--no-download]

Dependencies: pandas, numpy, yfinance, arch, scipy, matplotlib, seaborn
"""

import os
import json
import glob
import warnings
import argparse
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless environments
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from scipy import stats as sp_stats
from arch import arch_model

from info_picker_2 import download_SP500_data
from helper import safe_div, _to_float

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Analysis time boundaries
START_DATE = "2018-01-01"
END_DATE = "2023-12-31"

# Period definitions for discrete comparison
PERIODS: Dict[str, Tuple[str, str]] = {
    "Pre-COVID":  ("2018-01-01", "2019-12-31"),
    "COVID":      ("2020-01-01", "2021-06-30"),
    "Post-COVID": ("2021-07-01", "2023-12-31"),
}

# Sectors for detailed time-series plots
FOCUS_SECTORS = [
    "Information Technology",
    "Energy",
    "Health Care",
    "Financials",
]

# Rolling correlation window (63 trading days ≈ 1 calendar quarter)
ROLLING_WINDOW = 63

# Significance level
ALPHA = 0.05

# Suppress noisy warnings from yfinance and arch
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*arch.*")

# Matplotlib style for publication-quality figures
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 9,
    "figure.figsize": (12, 7),
})


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SECTOR RETURN BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class SectorReturnBuilder:
    """
    Downloads daily adjusted close prices for S&P 500 constituents,
    constructs market-cap-weighted daily log-return series per GICS sector,
    and retrieves the S&P 500 index return series.

    Market-cap weighting:
        w_{i,t} = mcap_{i,t} / Σ_j mcap_{j,t}   (within sector)
        R_{sector,t} = Σ_i w_{i,t-1} · r_{i,t}   (using lagged weights)
    """

    def __init__(self, start: str = START_DATE, end: str = END_DATE):
        self.start = start
        self.end = end
        self.ticker_to_sector: Dict[str, str] = {}
        self.prices: Optional[pd.DataFrame] = None          # tickers × dates
        self.market_caps: Optional[pd.DataFrame] = None      # tickers × dates
        self.sector_returns: Optional[pd.DataFrame] = None   # sectors × dates
        self.index_returns: Optional[pd.Series] = None       # ^GSPC series

    def load_sp500_sectors(self) -> Dict[str, str]:
        """Load S&P 500 ticker → GICS sector mapping via Wikipedia scraper."""
        logger.info("Loading S&P 500 sector mapping...")
        raw = download_SP500_data()
        # download_SP500_data() returns {ticker: {"sector": ..., "sub_industry": ...}}
        self.ticker_to_sector = {
            ticker: info["sector"]
            for ticker, info in raw.items()
            if isinstance(info, dict) and "sector" in info
        }
        sectors = set(self.ticker_to_sector.values())
        logger.info(
            f"Loaded {len(self.ticker_to_sector)} tickers across "
            f"{len(sectors)} sectors: {sorted(sectors)}"
        )
        return self.ticker_to_sector

    def download_daily_prices(self) -> pd.DataFrame:
        """
        Batch-download daily adjusted close prices from Yahoo Finance.
        Returns a DataFrame indexed by date with ticker columns.
        """
        tickers = sorted(self.ticker_to_sector.keys())
        logger.info(f"Downloading daily prices for {len(tickers)} tickers ({self.start} to {self.end})...")

        # yfinance batch download; auto_adjust=True gives adjusted close as 'Close'
        data = yf.download(
            tickers,
            start=self.start,
            end=self.end,
            auto_adjust=True,
            progress=False,
            threads=True,
        )

        # Extract Close prices; handle multi-level columns from batch download
        if isinstance(data.columns, pd.MultiIndex):
            self.prices = data["Close"].copy()
        else:
            self.prices = data[["Close"]].copy()
            self.prices.columns = tickers[:1]

        # Drop tickers with >50% missing data (delisted, renamed, etc.)
        threshold = len(self.prices) * 0.5
        valid_cols = self.prices.columns[self.prices.count() >= threshold]
        dropped = set(self.prices.columns) - set(valid_cols)
        if dropped:
            logger.warning(f"Dropped {len(dropped)} tickers with >50% missing data")
        self.prices = self.prices[valid_cols].ffill()

        logger.info(f"Price matrix: {self.prices.shape[0]} days × {self.prices.shape[1]} tickers")
        return self.prices

    def download_market_caps(self) -> pd.DataFrame:
        """
        Approximate daily market cap as Close × shares outstanding.
        Shares outstanding is fetched once per ticker (latest available)
        and assumed constant over the analysis window.

        This is a standard approximation in academic finance for
        constructing cap-weighted indices from daily price data.
        """
        logger.info("Computing market capitalizations...")
        if self.prices is None:
            raise RuntimeError("Call download_daily_prices() first")

        shares = {}
        for ticker in self.prices.columns:
            try:
                info = yf.Ticker(ticker).info
                so = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                if so and so > 0:
                    shares[ticker] = float(so)
            except Exception:
                continue

        logger.info(f"Retrieved shares outstanding for {len(shares)}/{len(self.prices.columns)} tickers")

        # Build market cap DataFrame: price × shares
        valid_tickers = [t for t in self.prices.columns if t in shares]
        shares_series = pd.Series({t: shares[t] for t in valid_tickers})
        self.market_caps = self.prices[valid_tickers].multiply(shares_series, axis=1)

        # Update ticker_to_sector to only include tickers with valid data
        self.ticker_to_sector = {
            t: s for t, s in self.ticker_to_sector.items() if t in valid_tickers
        }
        self.prices = self.prices[valid_tickers]

        logger.info(f"Market cap matrix: {self.market_caps.shape}")
        return self.market_caps

    def compute_sector_returns(self) -> pd.DataFrame:
        """
        Compute market-cap-weighted daily log returns per GICS sector.

        Log returns r_{i,t} = ln(P_{i,t} / P_{i,t-1}) are used for
        time-additivity and approximate normality.

        Sector return: R_{s,t} = Σ_i w_{i,t-1} · r_{i,t}
        where w_{i,t-1} are lagged market-cap weights (avoids look-ahead bias).
        """
        logger.info("Computing market-cap-weighted sector returns...")
        if self.prices is None or self.market_caps is None:
            raise RuntimeError("Call download_daily_prices() and download_market_caps() first")

        # Individual log returns
        log_returns = np.log(self.prices / self.prices.shift(1)).iloc[1:]

        # Lagged market caps for weights (avoids look-ahead bias)
        lagged_mcap = self.market_caps.shift(1).iloc[1:]

        # Group by sector
        sectors = sorted(set(self.ticker_to_sector.values()))
        sector_ret_dict = {}

        for sector in sectors:
            sector_tickers = [t for t, s in self.ticker_to_sector.items()
                              if s == sector and t in log_returns.columns]
            if len(sector_tickers) < 3:
                logger.warning(f"Sector '{sector}' has only {len(sector_tickers)} tickers; skipping")
                continue

            ret_s = log_returns[sector_tickers]
            mcap_s = lagged_mcap[sector_tickers]

            # Normalize weights per day (w_{i,t} = mcap_{i,t} / Σ_j mcap_{j,t})
            weights = mcap_s.div(mcap_s.sum(axis=1), axis=0)

            # Weighted return: element-wise multiply then sum across tickers
            weighted_ret = (ret_s * weights).sum(axis=1)
            sector_ret_dict[sector] = weighted_ret

        self.sector_returns = pd.DataFrame(sector_ret_dict).dropna(how="all")
        logger.info(f"Sector return series: {self.sector_returns.shape[0]} days × {self.sector_returns.shape[1]} sectors")
        return self.sector_returns

    def get_sp500_index_returns(self) -> pd.Series:
        """
        Download S&P 500 (^GSPC) daily log returns as the benchmark.
        """
        logger.info("Downloading S&P 500 index returns...")
        spx = yf.download("^GSPC", start=self.start, end=self.end,
                           auto_adjust=True, progress=False)

        # Handle potential MultiIndex from newer yfinance versions
        if isinstance(spx.columns, pd.MultiIndex):
            close = spx[("Close", "^GSPC")]
        else:
            close = spx["Close"]

        self.index_returns = np.log(close / close.shift(1)).dropna()
        self.index_returns.name = "SP500"
        logger.info(f"S&P 500 return series: {len(self.index_returns)} observations")
        return self.index_returns


# ═══════════════════════════════════════════════════════════════════════════════
# 2. GARCH VOLATILITY ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class GARCHVolatilityAnalyzer:
    """
    Fits univariate GARCH(1,1) models to each return series and extracts
    standardized residuals ε_t = r_t / σ_t.

    This addresses the Forbes-Rigobon (2002) critique: raw Pearson correlation
    between two series is mechanically biased upward during high-volatility
    periods. By dividing returns by their conditional standard deviation σ_t
    (estimated via GARCH), we obtain residuals with approximately constant
    variance, making correlation comparisons across periods valid.

    Model specification:
        Mean:     r_t = μ + ε_t
        Variance: σ²_t = ω + α·ε²_{t-1} + β·σ²_{t-1}
        Distribution: Normal (Gaussian)

    Returns are scaled by 100 before fitting (standard practice with the
    `arch` library for numerical stability).
    """

    SCALE = 100  # Numerical scaling factor

    def __init__(
        self,
        sector_returns: pd.DataFrame,
        index_returns: pd.Series,
    ):
        self.sector_returns = sector_returns
        self.index_returns = index_returns
        self.garch_results: Dict[str, object] = {}
        self.std_residuals_sectors: Optional[pd.DataFrame] = None
        self.std_residuals_index: Optional[pd.Series] = None

    def _fit_garch(self, series: pd.Series, name: str) -> Optional[object]:
        """
        Fit GARCH(1,1) to a single return series.

        Parameters
        ----------
        series : pd.Series
            Daily log-return series.
        name : str
            Label for logging.

        Returns
        -------
        arch.ARCHModelResult or None if fitting fails.
        """
        scaled = series.dropna() * self.SCALE
        if len(scaled) < 100:
            logger.warning(f"GARCH: insufficient data for '{name}' ({len(scaled)} obs)")
            return None

        try:
            model = arch_model(
                scaled,
                mean="Constant",
                vol="GARCH",
                p=1, q=1,
                dist="Normal",
                rescale=False,
            )
            result = model.fit(disp="off", show_warning=False)
            logger.debug(f"GARCH({name}): ω={result.params['omega']:.4f}, "
                         f"α={result.params['alpha[1]']:.4f}, β={result.params['beta[1]']:.4f}")
            return result
        except Exception as e:
            logger.warning(f"GARCH fit failed for '{name}': {e}")
            return None

    def fit_all(self):
        """Fit GARCH(1,1) to every sector return series and the S&P 500 index."""
        logger.info("Fitting GARCH(1,1) models...")

        # Align dates
        common_idx = self.sector_returns.index.intersection(self.index_returns.index)
        sectors = self.sector_returns.loc[common_idx]
        index = self.index_returns.loc[common_idx]

        # Fit each sector
        for sector in sectors.columns:
            result = self._fit_garch(sectors[sector], sector)
            if result is not None:
                self.garch_results[sector] = result

        # Fit index
        idx_result = self._fit_garch(index, "SP500")
        if idx_result is not None:
            self.garch_results["SP500"] = idx_result

        logger.info(f"Successfully fitted GARCH models for {len(self.garch_results)} series")

    def get_standardized_residuals(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extract standardized residuals ε_t = (r_t - μ) / σ_t from GARCH fits.

        These residuals have approximately unit variance and no volatility
        clustering, making Pearson correlation comparisons valid across
        high- and low-volatility regimes.

        Returns
        -------
        (sector_residuals, index_residuals) : (pd.DataFrame, pd.Series)
        """
        if not self.garch_results:
            raise RuntimeError("Call fit_all() first")

        sector_resid = {}
        for sector in self.sector_returns.columns:
            if sector in self.garch_results:
                res = self.garch_results[sector]
                # std_resid = residuals / conditional_volatility
                sector_resid[sector] = res.std_resid

        self.std_residuals_sectors = pd.DataFrame(sector_resid)

        if "SP500" in self.garch_results:
            self.std_residuals_index = self.garch_results["SP500"].std_resid
            self.std_residuals_index.name = "SP500"
        else:
            raise RuntimeError("GARCH fit for SP500 not available")

        # Align indices
        common = self.std_residuals_sectors.index.intersection(
            self.std_residuals_index.index
        )
        self.std_residuals_sectors = self.std_residuals_sectors.loc[common]
        self.std_residuals_index = self.std_residuals_index.loc[common]

        logger.info(f"Standardized residuals: {self.std_residuals_sectors.shape}")
        return self.std_residuals_sectors, self.std_residuals_index


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CORRELATION ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class CorrelationAnalyzer:
    """
    Performs three analyses on GARCH-standardized residuals:

    1. Period correlations: Pearson ρ for each (sector, period) pair.
    2. Fisher z-test: Tests H0: ρ_period1 = ρ_period2 for adjacent periods.
    3. Rolling correlation: Time-varying ρ_t as a DCC proxy.

    Fisher z-transformation (Fisher, 1921):
        z = 0.5 · ln((1+r)/(1-r))        (arctanh)
        Var(z) ≈ 1/(n-3)                  (asymptotic)
        Test: Z = (z1 - z2) / √(1/(n1-3) + 1/(n2-3))
        Under H0, Z ~ N(0,1)
    """

    def __init__(
        self,
        std_residuals: pd.DataFrame,
        index_residuals: pd.Series,
        periods: Dict[str, Tuple[str, str]] = PERIODS,
    ):
        self.residuals = std_residuals
        self.index_resid = index_residuals
        self.periods = periods
        self.period_corrs: Optional[pd.DataFrame] = None
        self.test_results: Optional[pd.DataFrame] = None
        self.rolling_corrs: Optional[pd.DataFrame] = None

    def compute_period_correlations(self) -> pd.DataFrame:
        """
        Compute Pearson correlation between each sector's standardized
        residuals and the S&P 500's standardized residuals for each period.

        Returns a DataFrame: sectors × periods.
        """
        logger.info("Computing period correlations on standardized residuals...")
        records = []
        for sector in self.residuals.columns:
            row = {"Sector": sector}
            for period_name, (start, end) in self.periods.items():
                mask = (self.residuals.index >= start) & (self.residuals.index <= end)
                s_resid = self.residuals.loc[mask, sector].dropna()
                i_resid = self.index_resid.loc[mask].dropna()

                # Align
                common = s_resid.index.intersection(i_resid.index)
                if len(common) < 30:
                    row[period_name] = np.nan
                    row[f"n_{period_name}"] = len(common)
                    continue

                r, _ = sp_stats.pearsonr(s_resid.loc[common], i_resid.loc[common])
                row[period_name] = r
                row[f"n_{period_name}"] = len(common)
            records.append(row)

        self.period_corrs = pd.DataFrame(records).set_index("Sector")
        logger.info("Period correlations computed.")
        return self.period_corrs

    @staticmethod
    def fisher_z_test(
        r1: float, n1: int, r2: float, n2: int
    ) -> Tuple[float, float]:
        """
        Test H0: ρ1 = ρ2 using the Fisher z-transformation.

        Parameters
        ----------
        r1, r2 : float
            Sample Pearson correlations for the two periods.
        n1, n2 : int
            Sample sizes (number of observations in each period).

        Returns
        -------
        (z_stat, p_value) : (float, float)
            Two-sided p-value from the standard normal distribution.

        Notes
        -----
        z_i = arctanh(r_i) = 0.5 · ln((1+r_i)/(1-r_i))
        Z = (z1 - z2) / sqrt(1/(n1-3) + 1/(n2-3))
        """
        # Clamp to avoid arctanh(±1) = ±inf
        r1 = np.clip(r1, -0.9999, 0.9999)
        r2 = np.clip(r2, -0.9999, 0.9999)

        z1 = np.arctanh(r1)
        z2 = np.arctanh(r2)

        se = np.sqrt(1.0 / (n1 - 3) + 1.0 / (n2 - 3))
        z_stat = (z1 - z2) / se

        p_value = 2.0 * sp_stats.norm.sf(abs(z_stat))  # two-sided
        return z_stat, p_value

    def run_all_tests(self) -> pd.DataFrame:
        """
        Run Fisher z-tests comparing adjacent periods for every sector.

        Returns a DataFrame with columns:
            Sector, r_pre, r_covid, r_post,
            z_pre_vs_covid, p_pre_vs_covid, sig_pre_covid,
            z_covid_vs_post, p_covid_vs_post, sig_covid_post
        """
        if self.period_corrs is None:
            self.compute_period_correlations()

        logger.info("Running Fisher z-tests for structural break detection...")
        period_names = list(self.periods.keys())
        records = []

        for sector in self.period_corrs.index:
            row = {"Sector": sector}

            r_vals = {}
            n_vals = {}
            for pname in period_names:
                r_vals[pname] = self.period_corrs.loc[sector, pname]
                n_vals[pname] = int(self.period_corrs.loc[sector, f"n_{pname}"])
                row[f"r_{pname}"] = r_vals[pname]
                row[f"n_{pname}"] = n_vals[pname]

            # Test 1: Pre-COVID vs COVID
            if not (np.isnan(r_vals[period_names[0]]) or np.isnan(r_vals[period_names[1]])):
                z, p = self.fisher_z_test(
                    r_vals[period_names[0]], n_vals[period_names[0]],
                    r_vals[period_names[1]], n_vals[period_names[1]],
                )
                row["z_pre_vs_covid"] = z
                row["p_pre_vs_covid"] = p
                row["sig_pre_covid"] = p < ALPHA
            else:
                row["z_pre_vs_covid"] = np.nan
                row["p_pre_vs_covid"] = np.nan
                row["sig_pre_covid"] = False

            # Test 2: COVID vs Post-COVID
            if not (np.isnan(r_vals[period_names[1]]) or np.isnan(r_vals[period_names[2]])):
                z, p = self.fisher_z_test(
                    r_vals[period_names[1]], n_vals[period_names[1]],
                    r_vals[period_names[2]], n_vals[period_names[2]],
                )
                row["z_covid_vs_post"] = z
                row["p_covid_vs_post"] = p
                row["sig_covid_post"] = p < ALPHA
            else:
                row["z_covid_vs_post"] = np.nan
                row["p_covid_vs_post"] = np.nan
                row["sig_covid_post"] = False

            records.append(row)

        self.test_results = pd.DataFrame(records).set_index("Sector")
        sig_count = self.test_results["sig_pre_covid"].sum()
        logger.info(
            f"Fisher z-tests complete. {sig_count}/{len(self.test_results)} sectors "
            f"show significant Pre→COVID correlation shift at α={ALPHA}"
        )
        return self.test_results

    def compute_rolling_correlation(self, window: int = ROLLING_WINDOW) -> pd.DataFrame:
        """
        Compute rolling Pearson correlation between each sector's standardized
        residuals and the S&P 500, using a window of `window` trading days.

        This serves as a proxy for the time-varying conditional correlation
        ρ_t from a DCC-GARCH model (Engle, 2002). The GARCH standardization
        removes volatility clustering; the rolling window captures time-variation
        in the co-movement structure.

        Parameters
        ----------
        window : int
            Rolling window size in trading days. Default 63 ≈ 1 quarter.

        Returns
        -------
        pd.DataFrame : rolling correlation per sector.
        """
        logger.info(f"Computing rolling correlation (window={window} days)...")
        rolling_dict = {}
        for sector in self.residuals.columns:
            aligned = pd.concat(
                [self.residuals[sector], self.index_resid], axis=1
            ).dropna()
            rolling_dict[sector] = aligned.iloc[:, 0].rolling(window).corr(aligned.iloc[:, 1])

        self.rolling_corrs = pd.DataFrame(rolling_dict)
        logger.info(f"Rolling correlations: {self.rolling_corrs.shape}")
        return self.rolling_corrs


# ═══════════════════════════════════════════════════════════════════════════════
# 4. INDICATOR DIVERGENCE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class IndicatorDivergenceAnalyzer:
    """
    Loads quarterly P/E and ROE from the local JSON filings (xbrl_data_json/),
    aggregates by sector using market-cap weights, and computes bootstrapped
    confidence intervals around the rolling 4-quarter weighted mean.

    Market-cap weight for indicator aggregation:
        w_i = yf_value_i × shares_outstanding_i / Σ_j(yf_value_j × shares_outstanding_j)
    where the sum runs over all companies in the sector for that quarter.

    Outlier treatment (applied at the individual-company level BEFORE aggregation):
        P/E : Negative values → NaN (negative earnings make P/E economically
              uninterpretable for valuation; standard practice per Damodaran, 2012).
              Values > 300 → NaN (extreme multiples from near-zero earnings).
        ROE : Clamped to [-100%, +100%]. Values outside this range are almost
              always the "denominator effect" (tiny or near-zero equity producing
              astronomical ratios), not genuine profitability signals.
    """

    # Winsorization bounds
    PE_MIN = 0.0      # Negative P/E → NaN (loss-making firms excluded)
    PE_MAX = 300.0     # Extreme multiples from near-zero EPS → NaN
    ROE_MIN = -100.0   # Floor: -100%
    ROE_MAX = 100.0    # Ceiling: +100%

    # Shares outstanding GAAP tags (priority order)
    _SHARES_TAGS = [
        "us-gaap_CommonStockSharesOutstanding",
        "us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
        "us-gaap_WeightedAverageNumberOfSharesOutstandingDiluted",
        "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic",
    ]

    def __init__(
        self,
        json_dir: str = "xbrl_data_json",
        sp500_sectors: Optional[Dict[str, str]] = None,
    ):
        self.json_dir = json_dir
        self.sp500_sectors = sp500_sectors or {}
        self.indicator_df: Optional[pd.DataFrame] = None
        self.sector_agg: Optional[pd.DataFrame] = None

    def _read_json(self, filepath: str) -> Optional[dict]:
        """Read a JSON filing, returning None on any error."""
        try:
            if os.path.getsize(filepath) == 0:
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _get_shares(self, base: dict) -> Optional[float]:
        """Extract shares outstanding from base GAAP variables."""
        for tag in self._SHARES_TAGS:
            val = _to_float(base.get(tag))
            if val is not None and val > 0:
                return val
        return None

    def _winsorize_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply econometrically motivated outlier treatment at the individual-
        company level, BEFORE any sector aggregation.

        P/E treatment:
            Negative P/E → NaN.  A negative price-to-earnings ratio implies
            negative earnings.  These firms are excluded from the P/E
            aggregate because the ratio loses its economic meaning as a
            valuation multiple (Damodaran, 2012, "Investment Valuation").
            Values above PE_MAX (300) are also excluded: they arise from
            near-zero denominators and would dominate the cap-weighted mean.

        ROE treatment:
            Clamp to [ROE_MIN, ROE_MAX] = [-100%, +100%].  Extreme ROE
            values are the classic "denominator effect" — a company with
            $1M net income but only $50K equity shows ROE = 2000%.  This
            is arithmetically correct but statistically distortive in a
            sector aggregate.  Clamping preserves the sign and direction
            while bounding the influence of any single firm.

        Parameters
        ----------
        df : pd.DataFrame
            Must contain columns 'P/E' and 'ROE'.

        Returns
        -------
        pd.DataFrame
            Same DataFrame with outliers treated in-place.
        """
        n_before_pe = df["P/E"].notna().sum()
        n_before_roe = df["ROE"].notna().sum()

        # ── P/E: negative → NaN, extreme positive → NaN ──
        df.loc[df["P/E"] < self.PE_MIN, "P/E"] = np.nan
        df.loc[df["P/E"] > self.PE_MAX, "P/E"] = np.nan

        # ── ROE: clamp to [-100, +100] ──
        df["ROE"] = df["ROE"].clip(lower=self.ROE_MIN, upper=self.ROE_MAX)

        n_after_pe = df["P/E"].notna().sum()
        n_after_roe = df["ROE"].notna().sum()

        pe_removed = n_before_pe - n_after_pe
        roe_clamped = ((df["ROE"] == self.ROE_MIN) | (df["ROE"] == self.ROE_MAX)).sum()
        logger.info(
            f"Winsorization: P/E removed {pe_removed} outliers "
            f"(negative or >{self.PE_MAX}); "
            f"ROE clamped {roe_clamped} values to [{self.ROE_MIN}%, {self.ROE_MAX}%]"
        )
        return df

    def load_quarterly_indicators(self) -> pd.DataFrame:
        """
        Scan all JSON filings and extract (date, ticker, sector, P/E, ROE, market_cap).

        Market cap is approximated as yf_value × shares_outstanding for the purpose
        of weighting the sector aggregate.
        """
        logger.info("Loading quarterly P/E and ROE from JSON filings...")
        records = []
        sp500_tickers = set(self.sp500_sectors.keys())

        for ticker_dir in sorted(glob.glob(os.path.join(self.json_dir, "*"))):
            ticker = os.path.basename(ticker_dir)
            if ticker not in sp500_tickers:
                continue
            sector = self.sp500_sectors[ticker]

            for fpath in sorted(glob.glob(os.path.join(ticker_dir, "*.json"))):
                data = self._read_json(fpath)
                if data is None:
                    continue

                date_str = data.get("date")
                if not date_str:
                    continue
                try:
                    date = pd.Timestamp(date_str)
                except Exception:
                    continue

                # Filter to analysis window
                if date < pd.Timestamp(START_DATE) or date > pd.Timestamp(END_DATE):
                    continue

                computed = data.get("computed") or {}
                base = data.get("base") or {}
                yf_val = _to_float(data.get("yf_value"))

                pe = _to_float(computed.get("P/E"))
                roe = _to_float(computed.get("ROE"))

                # Market cap for weighting
                shares = self._get_shares(base)
                mcap = (yf_val * shares) if (yf_val and shares) else None

                # Skip filings with no usable data
                if pe is None and roe is None:
                    continue

                records.append({
                    "date": date,
                    "ticker": ticker,
                    "sector": sector,
                    "P/E": pe,
                    "ROE": roe,
                    "market_cap": mcap,
                })

        self.indicator_df = pd.DataFrame(records)
        if not self.indicator_df.empty:
            self.indicator_df.sort_values("date", inplace=True)
            self.indicator_df.reset_index(drop=True, inplace=True)

            # Apply winsorization at the individual-company level.
            # This MUST happen before any aggregation to prevent the
            # denominator effect from propagating into sector means.
            self._winsorize_indicators(self.indicator_df)

        logger.info(f"Loaded {len(self.indicator_df)} filing records from {len(sp500_tickers)} tickers")
        return self.indicator_df

    def aggregate_by_sector_mcap(self) -> pd.DataFrame:
        """
        Compute market-cap-weighted P/E and ROE per sector per quarter.

        For each (sector, quarter) group:
            weighted_PE = Σ_i(w_i × PE_i) / Σ_i(w_i)     (where w_i = mcap_i)
            weighted_ROE = Σ_i(w_i × ROE_i) / Σ_i(w_i)

        Companies without market cap data fall back to equal weighting within
        the group.  Outlier treatment (negative P/E → NaN, ROE clamped to
        ±100%) is already applied at load time by _winsorize_indicators().
        """
        if self.indicator_df is None or self.indicator_df.empty:
            raise RuntimeError("Call load_quarterly_indicators() first")

        logger.info("Aggregating indicators by sector (market-cap weighted)...")
        df = self.indicator_df.copy()

        # Assign to calendar quarter
        df["quarter"] = df["date"].dt.to_period("Q")

        records = []
        for (sector, quarter), group in df.groupby(["sector", "quarter"]):
            row = {"sector": sector, "quarter": quarter, "date": quarter.to_timestamp()}

            for indicator in ["P/E", "ROE"]:
                valid = group.dropna(subset=[indicator])
                if valid.empty:
                    row[f"weighted_{indicator}"] = np.nan
                    row[f"n_{indicator}"] = 0
                    continue

                # Market-cap weighted mean
                has_mcap = valid["market_cap"].notna()
                if has_mcap.sum() >= 3:
                    weights = valid.loc[has_mcap, "market_cap"]
                    values = valid.loc[has_mcap, indicator]
                    row[f"weighted_{indicator}"] = np.average(values, weights=weights)
                else:
                    # Fallback to equal weight
                    row[f"weighted_{indicator}"] = valid[indicator].mean()
                row[f"n_{indicator}"] = len(valid)

            records.append(row)

        self.sector_agg = pd.DataFrame(records)
        self.sector_agg.sort_values(["sector", "date"], inplace=True)
        logger.info(f"Sector aggregation: {len(self.sector_agg)} (sector, quarter) observations")
        return self.sector_agg

    def compute_confidence_intervals(
        self,
        n_bootstrap: int = 1000,
        window: int = 4,
    ) -> pd.DataFrame:
        """
        Compute bootstrapped 95% confidence intervals around the rolling
        `window`-quarter weighted mean for each (sector, indicator).

        Bootstrap procedure:
            For each rolling window of `window` quarters, resample the
            constituent company-level observations (with replacement)
            `n_bootstrap` times, compute the weighted mean each time,
            and take the 2.5th and 97.5th percentiles as the CI bounds.

        Parameters
        ----------
        n_bootstrap : int
            Number of bootstrap resamples. Default 1000.
        window : int
            Rolling window in quarters. Default 4 (= 1 year).

        Returns
        -------
        Updated self.sector_agg with added columns:
            weighted_P/E_lower, weighted_P/E_upper,
            weighted_ROE_lower, weighted_ROE_upper
        """
        if self.indicator_df is None or self.sector_agg is None:
            raise RuntimeError("Call aggregate_by_sector_mcap() first")

        logger.info(f"Computing bootstrapped CIs (n={n_bootstrap}, window={window}Q)...")
        df = self.indicator_df.copy()
        df["quarter"] = df["date"].dt.to_period("Q")

        # No ad-hoc winsorization here — already applied at load time
        # by _winsorize_indicators() in load_quarterly_indicators().

        for indicator in ["P/E", "ROE"]:
            ci_lower = []
            ci_upper = []

            for _, agg_row in self.sector_agg.iterrows():
                sector = agg_row["sector"]
                current_q = agg_row["quarter"]

                # Collect data from the rolling window of quarters
                window_quarters = pd.period_range(
                    end=current_q, periods=window, freq="Q"
                )
                pool = df[
                    (df["sector"] == sector)
                    & (df["quarter"].isin(window_quarters))
                    & (df[indicator].notna())
                ]

                if len(pool) < 5:
                    ci_lower.append(np.nan)
                    ci_upper.append(np.nan)
                    continue

                # Bootstrap
                boot_means = np.empty(n_bootstrap)
                values = pool[indicator].values
                weights = pool["market_cap"].values
                has_weights = np.isfinite(weights) & (weights > 0)

                if has_weights.sum() >= 3:
                    vals_w = values[has_weights]
                    wts_w = weights[has_weights]
                    n = len(vals_w)
                    rng = np.random.default_rng(42)
                    for b in range(n_bootstrap):
                        idx = rng.integers(0, n, size=n)
                        boot_means[b] = np.average(vals_w[idx], weights=wts_w[idx])
                else:
                    vals_arr = values
                    n = len(vals_arr)
                    rng = np.random.default_rng(42)
                    for b in range(n_bootstrap):
                        idx = rng.integers(0, n, size=n)
                        boot_means[b] = np.mean(vals_arr[idx])

                ci_lower.append(np.percentile(boot_means, 2.5))
                ci_upper.append(np.percentile(boot_means, 97.5))

            self.sector_agg[f"weighted_{indicator}_lower"] = ci_lower
            self.sector_agg[f"weighted_{indicator}_upper"] = ci_upper

        logger.info("Confidence intervals computed.")
        return self.sector_agg


# ═══════════════════════════════════════════════════════════════════════════════
# 5. COVID IMPACT REPORT — Orchestrator & Visualization
# ═══════════════════════════════════════════════════════════════════════════════

class COVIDImpactReport:
    """
    Orchestrator that runs the full analysis pipeline and generates
    publication-quality figures and CSV tables.

    Outputs (saved to output_dir):
        fig1_correlation_heatmap.png   — Sector × Period correlation heatmap
        fig2_rolling_correlation.png   — Time-varying ρ_t for focus sectors
        fig3_fisher_z_results.png      — Z-statistics with significance markers
        fig4_pe_divergence.png         — Sector P/E with CI bands
        fig5_roe_divergence.png        — Sector ROE with CI bands
        fisher_z_results.csv           — Full hypothesis test results
        period_correlations.csv        — Period correlations
        sector_indicators.csv          — Weighted P/E and ROE time series
    """

    # COVID shading region
    COVID_START = "2020-01-01"
    COVID_END = "2021-06-30"

    def __init__(self, output_dir: str = "covid_analysis_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Pipeline components (populated during run())
        self.builder: Optional[SectorReturnBuilder] = None
        self.garch: Optional[GARCHVolatilityAnalyzer] = None
        self.corr_analyzer: Optional[CorrelationAnalyzer] = None
        self.indicator_analyzer: Optional[IndicatorDivergenceAnalyzer] = None

    def run(self):
        """Execute the full COVID-19 impact analysis pipeline."""
        logger.info("=" * 80)
        logger.info("COVID-19 IMPACT ANALYSIS — Starting Pipeline")
        logger.info("=" * 80)

        # ── Stage 1: Data preparation ──
        logger.info("\n── Stage 1/5: Building sector return series ──")
        self.builder = SectorReturnBuilder()
        self.builder.load_sp500_sectors()
        self.builder.download_daily_prices()
        self.builder.download_market_caps()
        self.builder.compute_sector_returns()
        self.builder.get_sp500_index_returns()

        # ── Stage 2: GARCH volatility modelling ──
        logger.info("\n── Stage 2/5: Fitting GARCH(1,1) models ──")
        self.garch = GARCHVolatilityAnalyzer(
            self.builder.sector_returns,
            self.builder.index_returns,
        )
        self.garch.fit_all()
        std_resid_sectors, std_resid_index = self.garch.get_standardized_residuals()

        # ── Stage 3: Correlation analysis & hypothesis testing ──
        logger.info("\n── Stage 3/5: Correlation analysis & Fisher z-tests ──")
        self.corr_analyzer = CorrelationAnalyzer(std_resid_sectors, std_resid_index)
        self.corr_analyzer.compute_period_correlations()
        self.corr_analyzer.run_all_tests()
        self.corr_analyzer.compute_rolling_correlation()

        # ── Stage 4: Indicator divergence ──
        logger.info("\n── Stage 4/5: P/E and ROE divergence analysis ──")
        self.indicator_analyzer = IndicatorDivergenceAnalyzer(
            sp500_sectors=self.builder.ticker_to_sector,
        )
        self.indicator_analyzer.load_quarterly_indicators()
        self.indicator_analyzer.aggregate_by_sector_mcap()
        self.indicator_analyzer.compute_confidence_intervals()

        # ── Stage 5: Visualization & export ──
        logger.info("\n── Stage 5/5: Generating figures and tables ──")
        self.plot_correlation_heatmap()
        self.plot_rolling_correlation()
        self.plot_fisher_z_results()
        self.plot_pe_divergence()
        self.plot_roe_divergence()
        self.export_tables()

        logger.info("=" * 80)
        logger.info(f"Pipeline complete. All outputs saved to: {self.output_dir}/")
        logger.info("=" * 80)

    # ── Visualization methods ──────────────────────────────────────────────

    def _add_covid_shading(self, ax: plt.Axes):
        """Add a semi-transparent red band marking the COVID period."""
        ax.axvspan(
            pd.Timestamp(self.COVID_START),
            pd.Timestamp(self.COVID_END),
            alpha=0.12, color="red", label="COVID period",
        )

    def plot_correlation_heatmap(self):
        """
        Figure 1: Heatmap of sector–SPX correlations across three periods.
        Uses GARCH-standardized residual correlations (Forbes-Rigobon corrected).
        """
        corr_df = self.corr_analyzer.period_corrs
        period_names = list(PERIODS.keys())

        # Extract just the correlation columns (not the n_ columns)
        plot_data = corr_df[period_names].astype(float)
        plot_data = plot_data.sort_index()

        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(
            plot_data,
            annot=True, fmt=".3f",
            cmap="RdYlGn", center=0.5,
            vmin=0, vmax=1,
            linewidths=0.5,
            ax=ax,
            cbar_kws={"label": "Pearson ρ (GARCH-standardized)"},
        )
        ax.set_title(
            "Sector–S&P 500 Correlation by Period\n"
            "(GARCH(1,1) Standardized Residuals — Forbes-Rigobon Adjusted)",
            fontweight="bold",
        )
        ax.set_ylabel("")
        ax.set_xlabel("")

        path = os.path.join(self.output_dir, "fig1_correlation_heatmap.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    def plot_rolling_correlation(self):
        """
        Figure 2: Time-varying rolling correlation ρ_t for focus sectors.
        Serves as a DCC-GARCH proxy using GARCH-standardized residuals.
        """
        rolling = self.corr_analyzer.rolling_corrs
        available = [s for s in FOCUS_SECTORS if s in rolling.columns]

        if not available:
            logger.warning("No focus sectors available for rolling correlation plot")
            return

        fig, ax = plt.subplots(figsize=(14, 7))
        colors = sns.color_palette("husl", len(available))

        for sector, color in zip(available, colors):
            series = rolling[sector].dropna()
            ax.plot(series.index, series.values, label=sector, color=color, linewidth=1.2)

        self._add_covid_shading(ax)

        ax.set_title(
            f"Rolling {ROLLING_WINDOW}-Day Correlation with S&P 500\n"
            "(GARCH(1,1) Standardized Residuals)",
            fontweight="bold",
        )
        ax.set_ylabel("Pearson ρ (standardized residuals)")
        ax.set_xlabel("")
        ax.legend(loc="lower left", framealpha=0.9)
        ax.set_ylim(-0.2, 1.0)
        ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.5)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        fig.autofmt_xdate()

        path = os.path.join(self.output_dir, "fig2_rolling_correlation.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    def plot_fisher_z_results(self):
        """
        Figure 3: Grouped bar chart of Fisher z-statistics with significance markers.
        Shows the magnitude and direction of the correlation shift between periods.
        """
        results = self.corr_analyzer.test_results
        if results is None:
            return

        sectors = results.index.tolist()
        z_pre = results["z_pre_vs_covid"].values
        z_post = results["z_covid_vs_post"].values

        x = np.arange(len(sectors))
        width = 0.35

        fig, ax = plt.subplots(figsize=(14, 7))
        bars1 = ax.bar(x - width / 2, z_pre, width, label="Pre→COVID", color="#e74c3c", alpha=0.8)
        bars2 = ax.bar(x + width / 2, z_post, width, label="COVID→Post", color="#3498db", alpha=0.8)

        # Add significance markers
        for i, sector in enumerate(sectors):
            if results.loc[sector, "sig_pre_covid"]:
                ax.text(i - width / 2, z_pre[i] + 0.1 * np.sign(z_pre[i]),
                        "*", ha="center", fontsize=14, fontweight="bold", color="#e74c3c")
            if results.loc[sector, "sig_covid_post"]:
                ax.text(i + width / 2, z_post[i] + 0.1 * np.sign(z_post[i]),
                        "*", ha="center", fontsize=14, fontweight="bold", color="#3498db")

        # Critical value lines
        z_crit = sp_stats.norm.ppf(1 - ALPHA / 2)
        ax.axhline(y=z_crit, color="gray", linestyle="--", linewidth=0.8, label=f"±z_{{0.025}} = ±{z_crit:.2f}")
        ax.axhline(y=-z_crit, color="gray", linestyle="--", linewidth=0.8)
        ax.axhline(y=0, color="black", linewidth=0.5)

        ax.set_xticks(x)
        ax.set_xticklabels(sectors, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel("Fisher Z-statistic")
        ax.set_title(
            "Fisher Z-Test: Structural Break in Sector–SPX Correlation\n"
            f"(* significant at α = {ALPHA})",
            fontweight="bold",
        )
        ax.legend(loc="upper right")

        path = os.path.join(self.output_dir, "fig3_fisher_z_results.png")
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    def _plot_indicator_divergence(self, indicator: str, ylabel: str, filename: str):
        """
        Shared logic for P/E and ROE divergence plots.
        Shows market-cap-weighted sector aggregates with bootstrapped CI bands.
        """
        agg = self.indicator_analyzer.sector_agg
        if agg is None or agg.empty:
            return

        weighted_col = f"weighted_{indicator}"
        lower_col = f"weighted_{indicator}_lower"
        upper_col = f"weighted_{indicator}_upper"

        available_sectors = [s for s in FOCUS_SECTORS if s in agg["sector"].unique()]
        if not available_sectors:
            available_sectors = sorted(agg["sector"].unique())[:6]

        fig, ax = plt.subplots(figsize=(14, 7))
        colors = sns.color_palette("husl", len(available_sectors))

        for sector, color in zip(available_sectors, colors):
            sector_data = agg[agg["sector"] == sector].sort_values("date")
            dates = sector_data["date"]
            values = sector_data[weighted_col]

            ax.plot(dates, values, label=sector, color=color, linewidth=1.5, marker="o", markersize=3)

            # Confidence interval band
            if lower_col in sector_data.columns:
                lower = sector_data[lower_col]
                upper = sector_data[upper_col]
                ax.fill_between(dates, lower, upper, color=color, alpha=0.15)

        self._add_covid_shading(ax)

        ax.set_title(
            f"Market-Cap-Weighted {indicator} by Sector\n"
            "(95% Bootstrapped Confidence Intervals, 4-Quarter Rolling Window)",
            fontweight="bold",
        )
        ax.set_ylabel(ylabel)
        ax.set_xlabel("")
        ax.legend(loc="best", framealpha=0.9)
        def quarter_fmt(x, pos):
            dt = mdates.num2date(x)
            quarter = (dt.month - 1) // 3 + 1
            return f"{dt.year}-Q{quarter}"
        import matplotlib.ticker as ticker
        ax.xaxis.set_major_formatter(ticker.FuncFormatter(quarter_fmt))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
        fig.autofmt_xdate()

        path = os.path.join(self.output_dir, filename)
        fig.tight_layout()
        fig.savefig(path)
        plt.close(fig)
        logger.info(f"Saved: {path}")

    def plot_pe_divergence(self):
        """Figure 4: P/E ratio divergence by sector."""
        self._plot_indicator_divergence("P/E", "Price-to-Earnings Ratio", "fig4_pe_divergence.png")

    def plot_roe_divergence(self):
        """Figure 5: ROE divergence by sector."""
        self._plot_indicator_divergence("ROE", "Return on Equity (%)", "fig5_roe_divergence.png")

    def export_tables(self):
        """Export analysis results as CSV files for inclusion in the dissertation."""
        # Fisher z-test results
        if self.corr_analyzer.test_results is not None:
            path = os.path.join(self.output_dir, "fisher_z_results.csv")
            self.corr_analyzer.test_results.to_csv(path, float_format="%.4f")
            logger.info(f"Exported: {path}")

        # Period correlations
        if self.corr_analyzer.period_corrs is not None:
            path = os.path.join(self.output_dir, "period_correlations.csv")
            self.corr_analyzer.period_corrs.to_csv(path, float_format="%.4f")
            logger.info(f"Exported: {path}")

        # Sector indicators
        if self.indicator_analyzer.sector_agg is not None:
            path = os.path.join(self.output_dir, "sector_indicators.csv")
            export = self.indicator_analyzer.sector_agg.copy()
            # Convert Period to string for CSV compatibility
            if "quarter" in export.columns:
                export["quarter"] = export["quarter"].astype(str)
            export.to_csv(path, index=False, float_format="%.4f")
            logger.info(f"Exported: {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="COVID-19 Impact Analysis: Sector–Index Correlation Structural Break Testing",
    )
    parser.add_argument(
        "--output-dir",
        default="covid_analysis_output",
        help="Directory for output figures and CSV tables (default: covid_analysis_output/)",
    )
    args = parser.parse_args()

    report = COVIDImpactReport(output_dir=args.output_dir)
    report.run()


if __name__ == "__main__":
    main()
