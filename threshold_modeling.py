"""
Weighted-Share Decline Threshold Modelling — Logistic Regression

This module answers Question C of the dissertation:
    "What exact percentage of total S&P 500 market capitalisation must exhibit
     a Quarter-over-Quarter (QoQ) decline in a fundamental indicator to push the
     aggregate (market-cap-weighted) index-level indicator into decline?"

Methodology:
  1. Company-Level Construction
        For each (ticker, quarter) pair, extract Net Income and ROE from the
        XBRL JSON filings.  Compute the QoQ change (Δ) for each company.
        Construct a binary decline indicator D_{i,t} = 1 if Δ < 0, else 0.

  2. Aggregate Market & Weighted Decline Share
        For each quarter t:
          X_t = Σ_{i: D_{i,t}=1} w_{i,t}      (weighted share of declining firms)
        where  w_{i,t} = mcap_{i,t} / Σ_j mcap_{j,t}.

        Y_t = 1 if the market-cap-weighted aggregate indicator declined QoQ, else 0.

  3. Logistic Regression & Decision Boundary
        Fit  P(Y_t = 1 | X_t) = σ(β_0 + β_1 · X_t).
        Critical threshold:  X_critical = −β_0 / β_1   (50 % probability).
        Model fit:  McFadden's pseudo-R².

Output (in threshold_output/):
  - fig1_logistic_curve_ni.png   — Logistic S-curve for Net Income
  - fig2_logistic_curve_roe.png  — Logistic S-curve for ROE
  - logistic_threshold_results.csv

Usage:
    python3 threshold_modeling.py [--output-dir DIR]

Dependencies: pandas, numpy, scipy, matplotlib, seaborn, scikit-learn
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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from sklearn.linear_model import LogisticRegression

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

# Full study window — broadest available range for maximum statistical power
START_DATE = "2009-01-01"
END_DATE = "2025-12-31"

# Winsorisation bounds (consistent with Phase 1 outlier treatment)
ROE_MIN = -100.0
ROE_MAX = 100.0

# Shares outstanding GAAP tags (priority order, same as IndicatorDivergenceAnalyzer)
_SHARES_TAGS = [
    "us-gaap_CommonStockSharesOutstanding",
    "us-gaap_WeightedAverageNumberOfDilutedSharesOutstanding",
    "us-gaap_WeightedAverageNumberOfSharesOutstandingDiluted",
    "us-gaap_WeightedAverageNumberOfSharesOutstandingBasic",
]

# Plot style
sns.set_theme(style="whitegrid", font_scale=1.15)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. COMPANY-LEVEL DATA BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

class CompanyQuarterlyBuilder:
    """
    Scans XBRL JSON filings and builds a company-level panel:
        (ticker, quarter) → Net Income, ROE, market_cap

    For each indicator, computes the QoQ change (Δ) and a binary decline
    indicator D_{i,t} = 1 if Δ < 0.
    """

    def __init__(
        self,
        json_dir: str = "xbrl_data_json",
        sp500_sectors: Optional[Dict[str, str]] = None,
    ):
        self.json_dir = json_dir
        self.sp500_sectors = sp500_sectors or {}
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

    # ── main loader ───────────────────────────────────────────────────────

    def load_filings(self) -> pd.DataFrame:
        """
        Extract (date, ticker, Net_Income, ROE, market_cap) from every JSON
        filing within [START_DATE, END_DATE].

        Net Income source:  base["us-gaap_NetIncomeLoss"]
        ROE source:         computed["ROE"]  (already calculated by indicators.py)
        Market cap:         yf_value × shares_outstanding
        """
        logger.info("Scanning JSON filings for company-level fundamentals …")
        sp500_tickers = set(self.sp500_sectors.keys())
        records: List[dict] = []

        for ticker_dir in sorted(glob.glob(os.path.join(self.json_dir, "*"))):
            ticker = os.path.basename(ticker_dir)
            if ticker not in sp500_tickers:
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
                computed = data.get("computed") or {}
                yf_val = _to_float(data.get("yf_value"))

                net_income = _to_float(base.get("us-gaap_NetIncomeLoss"))
                roe = _to_float(computed.get("ROE"))

                # Winsorise ROE (consistent with Phase 1)
                if roe is not None:
                    roe = max(ROE_MIN, min(ROE_MAX, roe))

                # Market cap
                shares = self._get_shares(base)
                mcap = (yf_val * shares) if (yf_val and shares) else None

                if net_income is None and roe is None:
                    continue

                records.append({
                    "date": date,
                    "ticker": ticker,
                    "Net_Income": net_income,
                    "ROE": roe,
                    "market_cap": mcap,
                })

        df = pd.DataFrame(records)
        if df.empty:
            raise RuntimeError("No filings found — check json_dir and S&P 500 mapping")

        df.sort_values(["ticker", "date"], inplace=True)
        df.reset_index(drop=True, inplace=True)

        # Assign calendar quarter
        df["quarter"] = df["date"].dt.to_period("Q")

        # De-duplicate: keep one observation per (ticker, quarter).
        # If a company filed twice in the same quarter, keep the later filing.
        df.sort_values(["ticker", "quarter", "date"], inplace=True)
        df = df.drop_duplicates(subset=["ticker", "quarter"], keep="last")

        logger.info(
            f"Loaded {len(df)} (ticker, quarter) observations "
            f"from {df['ticker'].nunique()} companies"
        )
        self.company_df = df
        return self.company_df

    # ── QoQ change & binary decline indicator ─────────────────────────────

    def compute_qoq_changes(self) -> pd.DataFrame:
        """
        For each company, compute the QoQ change (Δ) and binary decline
        indicator D = 1{Δ < 0} for both Net Income and ROE.

        The Δ is computed as a simple first difference within each ticker's
        time series (sorted by quarter).  Only consecutive quarters yield a
        valid Δ; the first quarter of each ticker's history is NaN.
        """
        if self.company_df is None:
            raise RuntimeError("Call load_filings() first")

        df = self.company_df.copy()
        df.sort_values(["ticker", "quarter"], inplace=True)

        for indicator in ["Net_Income", "ROE"]:
            col_delta = f"delta_{indicator}"
            col_decline = f"D_{indicator}"

            # QoQ difference within each company
            df[col_delta] = df.groupby("ticker")[indicator].diff()

            # Binary decline indicator
            df[col_decline] = np.where(df[col_delta] < 0, 1, 0)
            # NaN deltas (first quarter for each ticker) → NaN decline indicator
            df.loc[df[col_delta].isna(), col_decline] = np.nan

        self.company_df = df
        logger.info("QoQ changes and binary decline indicators computed")
        return self.company_df


# ═══════════════════════════════════════════════════════════════════════════════
# 2. AGGREGATE MARKET & WEIGHTED DECLINE SHARE
# ═══════════════════════════════════════════════════════════════════════════════

class AggregateMarketBuilder:
    """
    From the company-level panel, compute for each quarter:

    X_t (independent variable):
        The sum of market-cap weights of all companies where D_{i,t}=1.

    Y_t (dependent variable):
        1 if the market-cap-weighted aggregate indicator declined QoQ, else 0.
    """

    def __init__(self, company_df: pd.DataFrame):
        self.company_df = company_df
        self.quarterly_df: Optional[pd.DataFrame] = None

    def build(self) -> pd.DataFrame:
        """
        Build one row per quarter with columns:
            quarter, date,
            X_Net_Income, Y_Net_Income,
            X_ROE, Y_ROE,
            agg_Net_Income, agg_ROE,
            n_companies
        """
        df = self.company_df.copy()
        records: List[dict] = []

        for quarter, qgroup in df.groupby("quarter"):
            row: dict = {"quarter": quarter, "date": quarter.to_timestamp()}
            row["n_companies"] = qgroup["ticker"].nunique()

            for indicator in ["Net_Income", "ROE"]:
                col_decline = f"D_{indicator}"

                # ── Filter to companies with valid Δ and market cap ──
                valid = qgroup.dropna(subset=[col_decline, "market_cap", indicator])
                if len(valid) < 5:
                    # Too few companies — skip quarter to avoid spurious results
                    row[f"X_{indicator}"] = np.nan
                    row[f"Y_{indicator}"] = np.nan
                    row[f"agg_{indicator}"] = np.nan
                    continue

                # Total market cap for normalisation
                total_mcap = valid["market_cap"].sum()
                if total_mcap <= 0:
                    row[f"X_{indicator}"] = np.nan
                    row[f"Y_{indicator}"] = np.nan
                    row[f"agg_{indicator}"] = np.nan
                    continue

                # ── X_t: Weighted decline share ──
                declining = valid[valid[col_decline] == 1]
                weighted_decline_share = declining["market_cap"].sum() / total_mcap
                row[f"X_{indicator}"] = weighted_decline_share

                # ── Aggregate weighted indicator ──
                weights = valid["market_cap"].values
                values = valid[indicator].values
                agg_value = np.average(values, weights=weights)
                row[f"agg_{indicator}"] = agg_value

            records.append(row)

        quarterly = pd.DataFrame(records)
        quarterly.sort_values("quarter", inplace=True)
        quarterly.reset_index(drop=True, inplace=True)

        # ── Y_t: 1 if aggregate declined QoQ ──
        for indicator in ["Net_Income", "ROE"]:
            agg_col = f"agg_{indicator}"
            y_col = f"Y_{indicator}"
            quarterly[f"agg_delta_{indicator}"] = quarterly[agg_col].diff()
            quarterly[y_col] = np.where(
                quarterly[f"agg_delta_{indicator}"] < 0, 1, 0
            )
            # First quarter has no previous → NaN
            quarterly.loc[quarterly[f"agg_delta_{indicator}"].isna(), y_col] = np.nan

        self.quarterly_df = quarterly
        n_valid = quarterly.dropna(subset=["X_Net_Income", "Y_Net_Income"]).shape[0]
        logger.info(
            f"Quarterly aggregation complete: {len(quarterly)} quarters, "
            f"{n_valid} with valid (X, Y) pairs for Net Income"
        )
        return self.quarterly_df


# ═══════════════════════════════════════════════════════════════════════════════
# 3. LOGISTIC REGRESSION & THRESHOLD CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ThresholdModeller:
    """
    Fits a logistic regression  Y_t ~ X_t  and extracts the decision boundary.

    Attributes after fit():
        beta_0       : intercept
        beta_1       : coefficient on X_t
        x_critical   : −β_0 / β_1  (the 50 % probability threshold)
        pseudo_r2    : McFadden's pseudo-R²
    """

    def __init__(self):
        self.beta_0: Optional[float] = None
        self.beta_1: Optional[float] = None
        self.x_critical: Optional[float] = None
        self.pseudo_r2: Optional[float] = None
        self._model: Optional[LogisticRegression] = None
        self._X: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "ThresholdModeller":
        """
        Fit logistic regression.

        Parameters
        ----------
        X : array-like, shape (n,)
            Weighted decline share in [0, 1].
        y : array-like, shape (n,)
            Binary aggregate decline indicator (0/1).
        """
        X = np.asarray(X, dtype=float).reshape(-1, 1)
        y = np.asarray(y, dtype=float).ravel()

        # Remove any NaN
        mask = ~(np.isnan(X.ravel()) | np.isnan(y))
        X = X[mask]
        y = y[mask]

        if len(np.unique(y)) < 2:
            raise ValueError(
                "Cannot fit logistic regression — only one class present in y. "
                "Check that the aggregate indicator has both declining and "
                "non-declining quarters."
            )

        self._X = X
        self._y = y

        # sklearn logistic regression — no regularisation (C=∞)
        model = LogisticRegression(
            C=np.inf,
            solver="lbfgs",
            max_iter=5000,
            fit_intercept=True,
        )
        model.fit(X, y)
        self._model = model

        self.beta_0 = float(model.intercept_[0])
        self.beta_1 = float(model.coef_[0, 0])

        # Critical threshold: point where P(Y=1) = 0.5  ⟹  β0 + β1·x = 0
        if abs(self.beta_1) > 1e-12:
            self.x_critical = -self.beta_0 / self.beta_1
        else:
            self.x_critical = np.nan
            logger.warning("β1 ≈ 0 — no meaningful threshold can be extracted")

        # McFadden's pseudo-R²
        self.pseudo_r2 = self._mcfadden_r2(X, y)

        logger.info(
            f"Logistic fit: β0={self.beta_0:.4f}, β1={self.beta_1:.4f}, "
            f"X_critical={self.x_critical:.4f} ({self.x_critical*100:.2f}%), "
            f"McFadden R²={self.pseudo_r2:.4f}"
        )
        return self

    def _mcfadden_r2(self, X: np.ndarray, y: np.ndarray) -> float:
        """
        McFadden's pseudo-R² = 1 − LL_full / LL_null

        LL_full : log-likelihood of the fitted model
        LL_null : log-likelihood of the intercept-only (null) model
        """
        # Full model log-likelihood
        probs_full = self._model.predict_proba(X)
        eps = 1e-15
        ll_full = np.sum(
            y * np.log(probs_full[:, 1] + eps) +
            (1 - y) * np.log(probs_full[:, 0] + eps)
        )

        # Null model: predict the base rate
        p_bar = y.mean()
        ll_null = np.sum(
            y * np.log(p_bar + eps) +
            (1 - y) * np.log(1 - p_bar + eps)
        )

        if abs(ll_null) < eps:
            return 0.0
        return 1.0 - (ll_full / ll_null)

    def predict_proba(self, x_grid: np.ndarray) -> np.ndarray:
        """Return P(Y=1) for an array of X values."""
        return self._model.predict_proba(x_grid.reshape(-1, 1))[:, 1]


# ═══════════════════════════════════════════════════════════════════════════════
# 4. VISUALISATION & REPORT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class ThresholdReport:
    """
    Orchestrates the full pipeline:
        load → build → fit → plot → export CSV
    """

    # Friendly labels for each indicator
    _LABELS = {
        "Net_Income": "Net Income",
        "ROE": "ROE (%)",
    }

    def __init__(self, output_dir: str = "threshold_output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Pipeline objects (populated during run())
        self._builder: Optional[CompanyQuarterlyBuilder] = None
        self._aggregator: Optional[AggregateMarketBuilder] = None
        self._models: Dict[str, ThresholdModeller] = {}

    # ── S&P 500 mapping ───────────────────────────────────────────────────

    @staticmethod
    def _load_sp500_sectors() -> Dict[str, str]:
        raw = download_SP500_data()
        mapping = {
            ticker: info["sector"]
            for ticker, info in raw.items()
            if isinstance(info, dict) and "sector" in info
        }
        logger.info(f"S&P 500 mapping: {len(mapping)} tickers")
        return mapping

    # ── Plotting ──────────────────────────────────────────────────────────

    def _plot_logistic_curve(
        self,
        indicator: str,
        quarterly_df: pd.DataFrame,
        model: ThresholdModeller,
        filename: str,
    ) -> None:
        """
        Scatter plot of quarterly (X_t, Y_t) with fitted logistic S-curve
        and a vertical dashed red line at X_critical.
        """
        x_col = f"X_{indicator}"
        y_col = f"Y_{indicator}"
        label = self._LABELS.get(indicator, indicator)

        df = quarterly_df.dropna(subset=[x_col, y_col]).copy()
        X_obs = df[x_col].values
        Y_obs = df[y_col].values

        fig, ax = plt.subplots(figsize=(10, 6))

        # Scatter: jitter y slightly so overlapping 0s and 1s are visible
        jitter = np.random.default_rng(42).uniform(-0.02, 0.02, size=len(Y_obs))
        ax.scatter(
            X_obs * 100,
            Y_obs + jitter,
            color="steelblue",
            alpha=0.55,
            edgecolors="navy",
            linewidths=0.5,
            s=50,
            zorder=3,
            label="Observed quarters",
        )

        # Fitted logistic curve
        x_grid = np.linspace(0, 1, 500)
        y_pred = model.predict_proba(x_grid)
        ax.plot(
            x_grid * 100,
            y_pred,
            color="darkorange",
            linewidth=2.5,
            label="Fitted logistic curve",
            zorder=4,
        )

        # Horizontal reference at P = 0.5
        ax.axhline(
            0.5,
            color="gray",
            linestyle=":",
            linewidth=0.8,
            alpha=0.7,
        )

        # Vertical dashed red line at X_critical
        if not np.isnan(model.x_critical):
            x_crit_pct = model.x_critical * 100
            ax.axvline(
                x_crit_pct,
                color="red",
                linestyle="--",
                linewidth=2,
                zorder=5,
                label=f"$X_{{critical}}$ = {x_crit_pct:.1f}%",
            )
            # Annotate
            ax.annotate(
                f"{x_crit_pct:.1f}%\n(50% prob.)",
                xy=(x_crit_pct, 0.5),
                xytext=(x_crit_pct + 4, 0.65),
                fontsize=10,
                fontweight="bold",
                color="red",
                arrowprops=dict(arrowstyle="->", color="red", lw=1.5),
                zorder=6,
            )

        ax.set_xlabel("Weighted Decline Share $X_t$ (%)", fontsize=12)
        ax.set_ylabel("P(Aggregate Decline)", fontsize=12)
        ax.set_title(
            f"Logistic Threshold Model — {label}\n"
            f"$\\beta_0$={model.beta_0:.3f},  $\\beta_1$={model.beta_1:.3f},  "
            f"McFadden $R^2$={model.pseudo_r2:.3f}",
            fontsize=13,
        )
        ax.set_xlim(-2, 102)
        ax.set_ylim(-0.08, 1.08)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f"))
        ax.legend(loc="upper left", fontsize=10)
        sns.despine(ax=ax)

        fig.tight_layout()
        outpath = os.path.join(self.output_dir, filename)
        fig.savefig(outpath, dpi=200, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Saved: {outpath}")

    # ── CSV export ────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        rows = []
        for indicator, model in self._models.items():
            label = self._LABELS.get(indicator, indicator)
            rows.append({
                "Indicator": label,
                "beta_0 (intercept)": round(model.beta_0, 6),
                "beta_1 (coefficient)": round(model.beta_1, 6),
                "X_critical (%)": round(model.x_critical * 100, 2),
                "McFadden_Pseudo_R2": round(model.pseudo_r2, 4),
                "n_quarters": len(model._y),
            })

        csv_df = pd.DataFrame(rows)
        outpath = os.path.join(self.output_dir, "logistic_threshold_results.csv")
        csv_df.to_csv(outpath, index=False)
        logger.info(f"Saved: {outpath}")
        logger.info(f"\n{csv_df.to_string(index=False)}")

    # ── Main pipeline ─────────────────────────────────────────────────────

    def run(self) -> None:
        """Execute the full pipeline: load → aggregate → fit → plot → export."""
        logger.info("=" * 72)
        logger.info("THRESHOLD MODELLING — QUESTION C: WEIGHTED SHARE & DECLINE THRESHOLDS")
        logger.info("=" * 72)

        # 1. S&P 500 mapping
        sp500 = self._load_sp500_sectors()

        # 2. Company-level data
        self._builder = CompanyQuarterlyBuilder(sp500_sectors=sp500)
        self._builder.load_filings()
        self._builder.compute_qoq_changes()

        # 3. Aggregate market & weighted decline share
        self._aggregator = AggregateMarketBuilder(self._builder.company_df)
        quarterly = self._aggregator.build()

        # 4. Fit logistic regression for each indicator
        figure_map = {
            "Net_Income": "fig1_logistic_curve_ni.png",
            "ROE": "fig2_logistic_curve_roe.png",
        }

        for indicator, fig_name in figure_map.items():
            x_col = f"X_{indicator}"
            y_col = f"Y_{indicator}"
            label = self._LABELS.get(indicator, indicator)

            logger.info(f"\n{'─' * 60}")
            logger.info(f"Fitting logistic model for: {label}")

            valid = quarterly.dropna(subset=[x_col, y_col])
            X = valid[x_col].values
            y = valid[y_col].values

            logger.info(
                f"  Observations: {len(y)} quarters  |  "
                f"Decline rate: {y.mean():.1%} of quarters"
            )

            model = ThresholdModeller()
            model.fit(X, y)
            self._models[indicator] = model

            self._plot_logistic_curve(indicator, quarterly, model, fig_name)

        # 5. Export CSV
        self._export_csv()

        logger.info("\n" + "=" * 72)
        logger.info("THRESHOLD MODELLING COMPLETE")
        logger.info("=" * 72)


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Weighted-Share Decline Threshold Modelling (Question C)",
    )
    parser.add_argument(
        "--output-dir",
        default="threshold_output",
        help="Directory for output figures and tables (default: threshold_output/)",
    )
    args = parser.parse_args()

    report = ThresholdReport(output_dir=args.output_dir)
    report.run()


if __name__ == "__main__":
    main()
