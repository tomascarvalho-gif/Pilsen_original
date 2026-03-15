"""
AI Investment & Tech Sector Valuation — Exploratory Question 4

This module empirically tests whether Capital Expenditure (CAPEX) intensity
drove Price-to-Earnings multiple expansion among AI-infrastructure sub-sectors
during the 2023–2025 investment boom.

Methodology:
  1. Sub-sector-targeted extraction from XBRL JSON filings, filtering to:
        - Semiconductors
        - Semiconductor Materials & Equipment
        - Systems Software
        - Technology Hardware, Storage & Peripherals

  2. Metric Engineering:
        - CAPEX Intensity = |CAPEX| / Revenue  (per company, per quarter)
        - P/E = Market Cap / Net Income         (capped at 300; negative → NaN)
        - Period averages: Pre-AI (2021–2022) vs AI Boom (2023–2025)
        - Δ CAPEX Intensity and Δ P/E per company

  3. Cross-Sectional OLS Regression:
        Δ P/E  ~  Δ CAPEX Intensity
        (HC3 robust standard errors via statsmodels)

Output (in ai_valuation_output/):
  - fig1_capex_pe_regression.png
  - ai_regression_summary.csv

Usage:
    python3 ai_capex_valuation_analysis.py [--output-dir DIR]

Dependencies: pandas, numpy, matplotlib, seaborn, statsmodels
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
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm

from info_picker_2 import download_SP500_data
from helper import _to_float

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=FutureWarning)

# Study window
START_DATE = "2021-01-01"
END_DATE = "2025-12-31"

# Regime boundaries
PRE_AI_END = "2022-12-31"      # Pre-AI: 2021-01-01 → 2022-12-31
AI_BOOM_START = "2023-01-01"   # AI Boom: 2023-01-01 → 2025-12-31

# Target GICS sub-industries (AI infrastructure)
TARGET_SUB_INDUSTRIES = {
    "Semiconductors",
    "Semiconductor Materials & Equipment",
    "Systems Software",
    "Technology Hardware, Storage & Peripherals",
}

# P/E outlier treatment (consistent with Phase 1)
PE_MAX = 300.0

# Shares outstanding GAAP tags (priority order)
_SHARES_TAGS = [
    "us-gaap_CommonStockSharesOutstanding",
    "us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
    "us-gaap_WeightedAverageNumberOfSharesOutstandingDiluted",
    "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic",
]

# Revenue GAAP tags (priority order — ASC 606 first, then legacy)
_REVENUE_TAGS = [
    "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap_Revenues",
    "us-gaap_SalesRevenueNet",
]

# CAPEX keywords for cashflow-section fallback
_CAPEX_CF_KEYWORDS = [
    "capital expenditure",
    "purchases related to property",
    "purchases of property",
    "acquisition of property",
    "payments for property",
]

# Plot style
sns.set_theme(style="whitegrid", font_scale=1.15)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SUB-SECTOR DATA EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════════

class AISubSectorExtractor:
    """
    Scans XBRL JSON filings for companies in the target AI-infrastructure
    sub-industries and extracts quarterly fundamentals.
    """

    def __init__(
        self,
        json_dir: str = "xbrl_data_json",
        sp500_data: Optional[Dict] = None,
    ):
        self.json_dir = json_dir
        self.sp500_data = sp500_data or {}
        self.company_df: Optional[pd.DataFrame] = None

    # ── helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _read_json(filepath: str) -> Optional[dict]:
        try:
            if os.path.getsize(filepath) == 0:
                return None
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def _get_shares(base: dict) -> Optional[float]:
        for tag in _SHARES_TAGS:
            val = _to_float(base.get(tag))
            if val is not None and val > 0:
                return val
        return None

    @staticmethod
    def _get_revenue(base: dict) -> Optional[float]:
        """Extract revenue using priority-ordered GAAP tags."""
        for tag in _REVENUE_TAGS:
            val = _to_float(base.get(tag))
            if val is not None and val > 0:
                return val
        return None

    @staticmethod
    def _get_capex(data: dict) -> Optional[float]:
        """
        Extract CAPEX (absolute value).

        Strategy:
          1. Primary: base['us-gaap_PaymentsToAcquirePropertyPlantAndEquipment']
             (reported as negative cash outflow → take abs)
          2. Fallback: scan the cashflow statement for rows matching
             CAPEX-related keywords (handles NVDA, QCOM, etc.)
        """
        base = data.get("base") or {}

        # Primary tag
        capex = _to_float(base.get("us-gaap_PaymentsToAcquirePropertyPlantAndEquipment"))
        if capex is not None:
            return abs(capex)

        # Fallback: search cashflow section
        cf = data.get("cashflow") or {}
        # Get the most recent period in the cashflow dict
        for period_key, items in cf.items():
            if not isinstance(items, dict):
                continue
            for label, value in items.items():
                label_lower = label.lower()
                if any(kw in label_lower for kw in _CAPEX_CF_KEYWORDS):
                    val = _to_float(value)
                    if val is not None:
                        return abs(val)
            break  # Only check the first (most recent) period

        return None

    # ── price fetcher ────────────────────────────────────────────────────

    @staticmethod
    def _fetch_quarter_end_prices(tickers: List[str]) -> pd.DataFrame:
        """
        Batch-download daily adjusted close prices from yfinance and return
        a DataFrame indexed by date with ticker columns.

        This is used to fill in stock prices for filings that lack yf_value.
        """
        logger.info(f"Fetching daily prices for {len(tickers)} AI-infra tickers …")
        data = yf.download(
            tickers,
            start=START_DATE,
            end=END_DATE,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if isinstance(data.columns, pd.MultiIndex):
            prices = data["Close"].copy()
        else:
            prices = data[["Close"]].copy()
            prices.columns = tickers[:1]

        prices = prices.ffill()
        logger.info(f"Price matrix: {prices.shape[0]} days × {prices.shape[1]} tickers")
        return prices

    @staticmethod
    def _lookup_price(prices_df: pd.DataFrame, ticker: str, date: pd.Timestamp) -> Optional[float]:
        """
        Look up the closest available price on or before the filing date.
        Falls back to forward-fill if no exact match (weekends/holidays).
        """
        if ticker not in prices_df.columns:
            return None
        # Get the closest available date on or before the filing date
        valid_dates = prices_df.index[prices_df.index <= date]
        if valid_dates.empty:
            return None
        closest = valid_dates[-1]
        val = prices_df.loc[closest, ticker]
        return float(val) if pd.notna(val) else None

    # ── main loader ───────────────────────────────────────────────────────

    def load_filings(self) -> pd.DataFrame:
        """
        Extract (date, ticker, sub_industry, Net_Income, Revenue, CAPEX,
        market_cap, P_E) from filings within the study window.

        Stock prices are batch-downloaded from yfinance to compute market cap
        for filings lacking the yf_value field.
        """
        logger.info("Scanning JSON filings for AI sub-sector fundamentals …")

        # Build target ticker set
        target_tickers: Dict[str, str] = {}  # ticker → sub_industry
        for ticker, info in self.sp500_data.items():
            if not isinstance(info, dict):
                continue
            sub = info.get("sub_industry", "")
            if sub in TARGET_SUB_INDUSTRIES:
                target_tickers[ticker] = sub

        logger.info(
            f"Target tickers: {len(target_tickers)} companies across "
            f"{len(TARGET_SUB_INDUSTRIES)} sub-industries"
        )

        # ── Phase A: Extract raw fundamentals from JSON ──
        raw_records: List[dict] = []

        for ticker, sub_industry in sorted(target_tickers.items()):
            ticker_dir = os.path.join(self.json_dir, ticker)
            if not os.path.isdir(ticker_dir):
                continue

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

                if date < pd.Timestamp(START_DATE) or date > pd.Timestamp(END_DATE):
                    continue

                base = data.get("base") or {}
                yf_val = _to_float(data.get("yf_value"))

                net_income = _to_float(base.get("us-gaap_NetIncomeLoss"))
                revenue = self._get_revenue(base)
                capex = self._get_capex(data)
                shares = self._get_shares(base)

                raw_records.append({
                    "date": date,
                    "ticker": ticker,
                    "sub_industry": sub_industry,
                    "Net_Income": net_income,
                    "Revenue": revenue,
                    "CAPEX": capex,
                    "shares": shares,
                    "yf_value": yf_val,
                })

        df = pd.DataFrame(raw_records)
        if df.empty:
            raise RuntimeError("No filings found for target sub-industries")

        df.sort_values(["ticker", "date"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Assign calendar quarter and deduplicate
        df["quarter"] = df["date"].dt.to_period("Q")
        df.sort_values(["ticker", "quarter", "date"], inplace=True)
        df = df.drop_duplicates(subset=["ticker", "quarter"], keep="last")

        # ── Phase B: Fetch stock prices to fill missing yf_value ──
        tickers_need_price = df.loc[df["yf_value"].isna(), "ticker"].unique().tolist()
        all_tickers = df["ticker"].unique().tolist()

        if tickers_need_price:
            logger.info(
                f"{len(tickers_need_price)}/{len(all_tickers)} tickers need "
                f"price data from yfinance"
            )
            prices_df = self._fetch_quarter_end_prices(all_tickers)

            # Fill missing yf_value from downloaded prices
            for idx, row in df[df["yf_value"].isna()].iterrows():
                price = self._lookup_price(prices_df, row["ticker"], row["date"])
                if price is not None:
                    df.at[idx, "yf_value"] = price

        # ── Phase C: Compute market cap and P/E ──
        df["market_cap"] = np.where(
            df["yf_value"].notna() & df["shares"].notna(),
            df["yf_value"] * df["shares"],
            np.nan,
        )

        # P/E = Market Cap / Net Income
        df["P_E"] = np.nan
        pos_ni = df["Net_Income"].notna() & (df["Net_Income"] > 0) & df["market_cap"].notna()
        neg_ni = df["Net_Income"].notna() & (df["Net_Income"] <= 0)
        df.loc[pos_ni, "P_E"] = df.loc[pos_ni, "market_cap"] / df.loc[pos_ni, "Net_Income"]

        # Outlier treatment: cap at PE_MAX
        df.loc[df["P_E"] > PE_MAX, "P_E"] = np.nan

        # Drop helper columns
        df.drop(columns=["shares", "yf_value"], inplace=True)

        self.company_df = df
        logger.info(
            f"Loaded {len(df)} (ticker, quarter) observations "
            f"from {df['ticker'].nunique()} companies"
        )

        # Data coverage summary
        for col in ["Net_Income", "Revenue", "CAPEX", "market_cap", "P_E"]:
            pct = df[col].notna().mean() * 100
            logger.info(f"  {col}: {pct:.1f}% coverage")

        return self.company_df


# ═══════════════════════════════════════════════════════════════════════════════
# 2. METRIC ENGINEER
# ═══════════════════════════════════════════════════════════════════════════════

class MetricEngineer:
    """
    Computes CAPEX Intensity, assigns regimes, and calculates per-company
    deltas between Pre-AI and AI Boom periods.
    """

    def __init__(self, company_df: pd.DataFrame):
        self.company_df = company_df
        self.delta_df: Optional[pd.DataFrame] = None

    def compute_capex_intensity(self) -> pd.DataFrame:
        """CAPEX Intensity = CAPEX / Revenue (both positive)."""
        df = self.company_df.copy()
        mask = (df["CAPEX"].notna()) & (df["Revenue"].notna()) & (df["Revenue"] > 0)
        df.loc[mask, "CAPEX_Intensity"] = df.loc[mask, "CAPEX"] / df.loc[mask, "Revenue"]
        df.loc[~mask, "CAPEX_Intensity"] = np.nan

        n_valid = df["CAPEX_Intensity"].notna().sum()
        logger.info(f"CAPEX Intensity computed: {n_valid}/{len(df)} valid observations")
        self.company_df = df
        return self.company_df

    def compute_regime_deltas(self) -> pd.DataFrame:
        """
        For each company, compute:
          avg_CAPEX_Intensity_pre, avg_CAPEX_Intensity_boom,
          avg_PE_pre, avg_PE_boom,
          delta_CAPEX_Intensity, delta_PE
        """
        df = self.company_df.copy()
        df["regime"] = np.where(
            df["date"] <= pd.Timestamp(PRE_AI_END), "Pre-AI", "AI Boom"
        )

        records = []
        for ticker, tgroup in df.groupby("ticker"):
            sub_ind = tgroup["sub_industry"].iloc[0]

            row = {"ticker": ticker, "sub_industry": sub_ind}

            for regime in ["Pre-AI", "AI Boom"]:
                rdata = tgroup[tgroup["regime"] == regime]

                ci = rdata["CAPEX_Intensity"].dropna()
                pe = rdata["P_E"].dropna()

                suffix = "pre" if regime == "Pre-AI" else "boom"
                row[f"avg_CAPEX_Intensity_{suffix}"] = ci.mean() if len(ci) >= 2 else np.nan
                row[f"avg_PE_{suffix}"] = pe.mean() if len(pe) >= 2 else np.nan
                row[f"n_quarters_{suffix}"] = len(rdata)

            # Deltas
            if not np.isnan(row.get("avg_CAPEX_Intensity_pre", np.nan)) and \
               not np.isnan(row.get("avg_CAPEX_Intensity_boom", np.nan)):
                row["delta_CAPEX_Intensity"] = (
                    row["avg_CAPEX_Intensity_boom"] - row["avg_CAPEX_Intensity_pre"]
                )
            else:
                row["delta_CAPEX_Intensity"] = np.nan

            if not np.isnan(row.get("avg_PE_pre", np.nan)) and \
               not np.isnan(row.get("avg_PE_boom", np.nan)):
                row["delta_PE"] = row["avg_PE_boom"] - row["avg_PE_pre"]
            else:
                row["delta_PE"] = np.nan

            records.append(row)

        self.delta_df = pd.DataFrame(records)
        n_complete = self.delta_df.dropna(
            subset=["delta_CAPEX_Intensity", "delta_PE"]
        ).shape[0]
        logger.info(
            f"Regime deltas computed: {len(self.delta_df)} companies, "
            f"{n_complete} with complete delta pairs"
        )
        return self.delta_df


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CROSS-SECTIONAL OLS REGRESSION
# ═══════════════════════════════════════════════════════════════════════════════

class CAPEXValuationRegression:
    """
    Fits an OLS regression:  Δ P/E  ~  Δ CAPEX Intensity
    with HC3 robust standard errors.
    """

    def __init__(self):
        self.results: Optional[sm.regression.linear_model.RegressionResultsWrapper] = None
        self.beta_0: Optional[float] = None
        self.beta_1: Optional[float] = None
        self.r_squared: Optional[float] = None
        self.p_value: Optional[float] = None
        self.t_stat: Optional[float] = None
        self.n_obs: int = 0

    def fit(self, delta_df: pd.DataFrame) -> "CAPEXValuationRegression":
        """
        Fit OLS:  delta_PE = β0 + β1 · delta_CAPEX_Intensity + ε
        with HC3 heteroskedasticity-robust standard errors.
        """
        clean = delta_df.dropna(subset=["delta_CAPEX_Intensity", "delta_PE"]).copy()
        self.n_obs = len(clean)

        if self.n_obs < 5:
            raise ValueError(
                f"Only {self.n_obs} complete observations — insufficient for OLS"
            )

        X = sm.add_constant(clean["delta_CAPEX_Intensity"].values)
        y = clean["delta_PE"].values

        model = sm.OLS(y, X)
        self.results = model.fit(cov_type="HC3")

        self.beta_0 = self.results.params[0]
        self.beta_1 = self.results.params[1]
        self.r_squared = self.results.rsquared
        self.t_stat = self.results.tvalues[1]
        self.p_value = self.results.pvalues[1]

        logger.info(
            f"OLS fit (n={self.n_obs}): "
            f"β1={self.beta_1:.4f}, t={self.t_stat:.4f}, "
            f"p={self.p_value:.6f}, R²={self.r_squared:.4f}"
        )
        return self


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VISUALISATION & REPORT
# ═══════════════════════════════════════════════════════════════════════════════

class AIValuationReport:
    """
    Orchestrates the full pipeline: extract → engineer → regress → plot → export.
    """

    def __init__(self, output_dir: str = "ai_valuation_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ── Scatter plot with OLS line ────────────────────────────────────────

    def _plot_regression(
        self,
        delta_df: pd.DataFrame,
        regression: CAPEXValuationRegression,
    ) -> None:
        """
        Scatter: Δ CAPEX Intensity (x) vs Δ P/E (y)
        with OLS regression line and annotation box.
        """
        clean = delta_df.dropna(subset=["delta_CAPEX_Intensity", "delta_PE"]).copy()
        x = clean["delta_CAPEX_Intensity"].values
        y = clean["delta_PE"].values

        # Sub-industry colour coding
        sub_colors = {
            "Semiconductors": "#1f77b4",
            "Semiconductor Materials & Equipment": "#2ca02c",
            "Systems Software": "#ff7f0e",
            "Technology Hardware, Storage & Peripherals": "#d62728",
        }

        fig, ax = plt.subplots(figsize=(11, 7.5))

        # Scatter by sub-industry
        for sub_ind, color in sub_colors.items():
            mask = clean["sub_industry"] == sub_ind
            if mask.sum() == 0:
                continue
            ax.scatter(
                clean.loc[mask, "delta_CAPEX_Intensity"] * 100,
                clean.loc[mask, "delta_PE"],
                color=color,
                alpha=0.7,
                edgecolors="black",
                linewidths=0.5,
                s=70,
                label=sub_ind,
                zorder=3,
            )

        # Label notable companies
        for _, row in clean.iterrows():
            if abs(row["delta_PE"]) > np.percentile(np.abs(y), 85) or \
               abs(row["delta_CAPEX_Intensity"]) > np.percentile(np.abs(x), 85):
                ax.annotate(
                    row["ticker"],
                    (row["delta_CAPEX_Intensity"] * 100, row["delta_PE"]),
                    fontsize=7.5,
                    fontweight="bold",
                    alpha=0.8,
                    xytext=(4, 4),
                    textcoords="offset points",
                )

        # OLS regression line
        x_range = np.linspace(x.min(), x.max(), 200)
        y_hat = regression.beta_0 + regression.beta_1 * x_range
        ax.plot(
            x_range * 100, y_hat,
            color="red",
            linewidth=2.5,
            linestyle="--",
            label="OLS fit",
            zorder=4,
        )

        # Statistics text box
        sig_marker = "★★★" if regression.p_value < 0.001 else \
                     "★★" if regression.p_value < 0.01 else \
                     "★" if regression.p_value < 0.05 else "n.s."
        textstr = (
            f"$\\beta_1$ = {regression.beta_1:.2f}\n"
            f"$R^2$ = {regression.r_squared:.4f}\n"
            f"$t$ = {regression.t_stat:.3f}\n"
            f"$p$ = {regression.p_value:.4f} {sig_marker}\n"
            f"$n$ = {regression.n_obs}"
        )
        props = dict(boxstyle="round,pad=0.5", facecolor="lightyellow",
                     edgecolor="gray", alpha=0.9)
        ax.text(
            0.03, 0.97, textstr,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment="top",
            bbox=props,
        )

        ax.axhline(0, color="gray", linewidth=0.5, linestyle=":")
        ax.axvline(0, color="gray", linewidth=0.5, linestyle=":")

        ax.set_xlabel("Δ CAPEX Intensity (pp)", fontsize=12)
        ax.set_ylabel("Δ P/E Ratio", fontsize=12)
        ax.set_title(
            "AI Infrastructure: CAPEX Intensity vs. P/E Multiple Expansion\n"
            "(Pre-AI 2021–2022 → AI Boom 2023–2025, HC3 Robust OLS)",
            fontsize=13,
        )
        ax.legend(loc="lower right", fontsize=9, framealpha=0.9)
        sns.despine(ax=ax)

        fig.tight_layout()
        outpath = os.path.join(self.output_dir, "fig1_capex_pe_regression.png")
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved: {outpath}")

    # ── CSV export ────────────────────────────────────────────────────────

    def _export_csv(self, regression: CAPEXValuationRegression) -> None:
        """Export the formal OLS summary table."""
        res = regression.results

        # Build a clean summary DataFrame
        rows = []
        param_names = ["const (β₀)", "Δ CAPEX Intensity (β₁)"]
        for i, name in enumerate(param_names):
            rows.append({
                "Variable": name,
                "Coefficient": round(res.params[i], 6),
                "Std_Error_HC3": round(res.bse[i], 6),
                "t_statistic": round(res.tvalues[i], 4),
                "p_value": round(res.pvalues[i], 6),
                "CI_lower_95": round(res.conf_int()[i, 0], 4),
                "CI_upper_95": round(res.conf_int()[i, 1], 4),
            })

        csv_df = pd.DataFrame(rows)

        # Append model diagnostics as metadata rows
        diag = pd.DataFrame([
            {"Variable": "R_squared", "Coefficient": round(res.rsquared, 6)},
            {"Variable": "Adj_R_squared", "Coefficient": round(res.rsquared_adj, 6)},
            {"Variable": "F_statistic", "Coefficient": round(res.fvalue, 4)},
            {"Variable": "F_p_value", "Coefficient": round(res.f_pvalue, 6)},
            {"Variable": "n_observations", "Coefficient": res.nobs},
        ])
        csv_df = pd.concat([csv_df, diag], ignore_index=True)

        outpath = os.path.join(self.output_dir, "ai_regression_summary.csv")
        csv_df.to_csv(outpath, index=False)
        logger.info(f"Saved: {outpath}")
        logger.info(f"\n{csv_df.to_string(index=False)}")

    # ── Main pipeline ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full AI CAPEX-valuation pipeline."""
        logger.info("=" * 72)
        logger.info("AI INVESTMENT & TECH SECTOR VALUATION — EXPLORATORY QUESTION 4")
        logger.info("=" * 72)

        # 1. S&P 500 mapping
        sp500 = download_SP500_data()
        logger.info(f"S&P 500 mapping loaded: {len(sp500)} companies")

        # 2. Extract sub-sector filings
        extractor = AISubSectorExtractor(sp500_data=sp500)
        extractor.load_filings()

        # 3. Engineer metrics
        engineer = MetricEngineer(extractor.company_df)
        engineer.compute_capex_intensity()
        delta_df = engineer.compute_regime_deltas()

        # Log per-company deltas
        complete = delta_df.dropna(subset=["delta_CAPEX_Intensity", "delta_PE"])
        logger.info(f"\nPer-company deltas (complete cases: {len(complete)}):")
        for _, r in complete.sort_values("delta_PE", ascending=False).iterrows():
            logger.info(
                f"  {r['ticker']:6s}  ({r['sub_industry'][:20]:20s})  "
                f"ΔCAPEX_Int={r['delta_CAPEX_Intensity']:+.4f}  "
                f"ΔP/E={r['delta_PE']:+.1f}"
            )

        # 4. OLS regression
        regression = CAPEXValuationRegression()
        regression.fit(delta_df)

        # 5. Outputs
        self._plot_regression(delta_df, regression)
        self._export_csv(regression)

        # Print full statsmodels summary
        logger.info(f"\n{regression.results.summary()}")

        logger.info("\n" + "=" * 72)
        logger.info("AI VALUATION ANALYSIS COMPLETE")
        logger.info("=" * 72)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="AI Investment & Tech Sector Valuation (Q4)",
    )
    parser.add_argument(
        "--output-dir",
        default="ai_valuation_output",
        help="Directory for output figures and tables (default: ai_valuation_output/)",
    )
    args = parser.parse_args()

    report = AIValuationReport(output_dir=args.output_dir)
    report.run()


if __name__ == "__main__":
    main()
