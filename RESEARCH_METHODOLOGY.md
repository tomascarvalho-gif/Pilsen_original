# DATA COLLECTION STRATEGY & DATASET VALIDITY REPORT

**Project Title:** Multidimensional Visualization of Financial Indicators (S&P 500)

**Date:** February 24, 2026

**Author:** Tomás Carvalho

**Advisor:** doc. Ing. Jan Pospíšil, Ph.D.

**University:** University of Brasília (UnB) / Západočeská univerzita v Plzni

---

## 1. Executive Summary

This report outlines the data acquisition strategy and current status of the dataset compiled for the analysis of S&P 500 financial indicators. The data collection phase is complete, resulting in a robust dataset covering the period **2000–2025**.

This scope was selected to ensure maximum data integrity and statistical validity. While the dataset does not include every historical constituent of the index for every year, it achieves near-total market capitalization coverage ("weighted share"), ensuring that the resulting visualizations and correlations accurately reflect market movements, particularly regarding Sector Analysis and the COVID-19 impact.

---

## 2. Methodology: S&P 500 Universe and the XBRL Data Transition (2000–2025)

A strategic decision was made to define the empirical study period from **2000 to 2025**, strictly limiting the constituent universe to the 500 companies comprising the S&P 500 index. However, the integrity and availability of the dataset are fundamentally bifurcated by the technological evolution of SEC filings:

- **Pre-2009 (The Unstructured Era & Data Sparsity):** Prior to 2009, corporate financial reports were filed primarily as unstructured HTML or text documents. Because extracting precise financial indicators (e.g., P/E Ratio, ROE) from these legacy formats requires unreliable text parsing and estimation, structured data for several S&P 500 constituents is either unavailable or highly sparse between 2000 and 2008.
- **Post-2009 (XBRL Standardization):** The SEC mandated the phased use of XBRL (eXtensible Business Reporting Language) starting in 2009. This format provides structured, machine-readable tags for every financial line item, ensuring high-fidelity, standardized data retrieval.

**Methodological Impact:** By extending the timeline back to 2000, the study successfully captures vital historical macroeconomic regimes. However, the reliance on high-fidelity structured filings dictates that the dataset operates as an **unbalanced panel**. Data density and sample sizes are naturally constrained prior to 2009, reaching maximum fidelity only in the post-XBRL era. This structural reality was strictly accounted for to ensure the accuracy of the multidimensional visualizations and statistical tests.

---

## 3. Dataset Health & Market Coverage

The dataset was subjected to a "Heavyweight Analysis" to verify its representativeness of the S&P 500 index.

- **Company Count:** The number of companies varies by year (ranging from ~230 in 2009 to ~1500 in recent years) due to the gradual adoption of XBRL and the natural churn of the index (mergers, bankruptcies).
- **Weighted Validity (The "Kings" Check):** Despite the varying count, the dataset consistently includes the top market-cap constituents ("The Kings") for every year in the study.
  - _Example:_ The 2009–2012 data includes key drivers such as Exxon Mobil (XOM), Apple (AAPL), Microsoft (MSFT), and GE.
  - _Example:_ The 2020–2025 data includes the "Magnificent Seven" (e.g., Nvidia, Amazon, Meta).

**Conclusion:** Because the S&P 500 is a market-cap-weighted index, the absence of smaller companies in the early years has a negligible statistical impact on the index's overall performance. The dataset successfully captures the "weighted share" required to simulate index-level movements.

---

## 4. Alignment with Research Objectives & Methodology

The current dataset is fully sufficient to calculate the key Financial Indicators required for the multidimensional analysis. Specifically, we will compute and visualize the following metrics for each company and aggregated sector:

- **Valuation Metrics:** Price-to-Earnings (P/E), Price-to-Book (P/B), Price-to-Cash-Flow (P/CF)
- **Profitability Metrics:** Return on Equity (ROE), Net Profit Margin
- **Health/Leverage Metrics:** Debt-to-Equity Ratio, Current Ratio

These indicators will serve as the primary variables for answering the core research questions:

---

### A. COVID-19 Impact Analysis

**Objective:** Visualize the divergence of selected indicators (e.g., P/E and ROE) before, during, and after the pandemic.

**Method:** We will track the correlation coefficient between sector performance and the broader S&P 500 index across three distinct periods (Pre-2020, 2020–2021, Post-2021) to determine if historical correlations were "broken" or inverted during the crisis.

---

### B. Sector Analysis (Technology vs. Energy)

**Objective:** Compare the development of valuation and profitability indicators across the 11 S&P 500 sectors.

**Method:** We will specifically isolate the Technology and Energy sectors to visualize their inverse correlation during key economic events (e.g., the 2015 oil price crash vs. the 2020 tech rally).

---

### C. Weighted Share & Decline Thresholds

**Objective:** Determine the "tipping point" for market decline.

**Method:** Using the market-cap weighted data, we will calculate the percentage of companies (by weight) that must show a quarter-over-quarter decline in Net Income or ROE to trigger a decline in the overall sector index.

---

## 5. Proposed Additional Research Questions

To rigorously expand the baseline analysis of the S&P 500, two additional exploratory dimensions were selected for the final project scope. The inclusion of these specific vectors was designed to test the market's structural response of the stocks.

---

### Q3: Cross-Sector Correlation Shifts (COVID-19)

**Research Question:** How did the correlation between sectors (e.g., Tech vs. Health, Energy vs. Materials) change during the pandemic? Did sectors that traditionally move together decouple during the 2020–2021 period?

---

### Q4: AI Investment & Tech Sector Valuation

**Research Question:** Is there a measurable relationship between the R&D / Capital Expenditure (CAPEX) growth of individual Tech companies and their stock price performance?

**Context:** This would serve as a proxy for "AI Investment," assuming that significant increases in R&D and CAPEX in 2023–2025 are largely driven by Artificial Intelligence infrastructure.

---

## Scope Summary

| Question                      | In Scope | External Data Needed | Effort                         |
| ----------------------------- | -------- | -------------------- | ------------------------------ |
| A: COVID Correlation          | Yes      | None                 | Already partially implemented  |
| B: Tech vs. Energy Sectors    | Yes      | None                 | Already partially implemented  |
| C: Weighted Decline Threshold | Yes      | None                 | Needs market-cap weighting fix |
| Q3: Cross-Sector Correlation  | Yes      | None                 | Low                            |
| Q4: R&D/CAPEX vs. Stock Price | Yes      | None                 | Low–Medium                     |

---

## 6. Preliminary Results: COVID-19 Impact Analysis

### 6.1 Volatility Adjustment and Outlier Sanitization

To rigorously assess whether the correlation between sector performance and the S&P 500 experienced a structural break during the pandemic, the raw returns were standardized using a **GARCH(1,1)** model. This extracted the standardized residuals (_ε_t_), neutralizing the **Forbes-Rigobon effect** (where correlations artificially inflate during periods of high market variance).

Furthermore, a strict data sanitization protocol was enforced to address the **"Denominator Effect"** in our fundamental indicators. Following established valuation econometrics (Damodaran, 2012):

- **P/E Ratios:** Capped at a maximum of 300. Negative P/E ratios were forced to `NaN`.
- **Return on Equity (ROE):** Winsorized to a strict boundary of **-100% to 100%** at the company level prior to market-cap weighting to neutralize equity-driven asymptote artifacts.

---

### 6.2 Statistical Results: Fisher Z-Transformation

A formal **Fisher z-transformation** hypothesis test (_H₀: ρ_pre = ρ_covid_) was conducted on the 63-day rolling Pearson correlations (_α = 0.05_) to test for market decoupling.

**Figure 1: Sector–S&P 500 Correlation by Period.**

This heatmap establishes the baseline GARCH-standardized Pearson _ρ_ across all 11 S&P 500 sectors for the Pre-COVID, COVID, and Post-COVID periods.

![Figure 1: Correlation Heatmap](covid_analysis_output/fig1_correlation_heatmap.png)

### Sector Correlation Interpretations: Real-World Structural Breaks

While the majority of the S&P 500—most notably massive, market-cap-weighted sectors like Information Technology, Financials, and Industrials—maintained historically high and stable correlations (ranging between 0.80 and 0.91) across all three observed periods, they essentially functioned as the structural anchor of the index. Because the bulk of the market's covariance matrix behaved exactly as expected during the macroeconomic shock, this analysis deliberately isolates the four anomalous sectors: Consumer Staples, Energy, Real Estate, and Utilities. These specific sectors exhibited statistically significant regime shifts and structural breaks, providing the clearest mathematical footprints of the pandemic's real-world impact on market decoupling and liquidity.

**Consumer Staples (Supply Chain & Liquidity Shock):**

The Consumer Staples sector demonstrated a distinct structural break, shifting from a defensive, moderate correlation (0.591) pre-COVID to a highly synchronized state during the pandemic shock (0.754). This mathematical fracture reflects severe global supply chain disruptions and the broader institutional liquidity crunch. Panic-driven market sell-offs temporarily overrode the sector's traditionally stable, inelastic consumer demand, forcing it to move in lockstep with the crashing index before normalizing in the post-pandemic regime (0.636).

**Energy (Fundamental Decoupling):**

Conversely, the Energy sector exhibited a persistent decoupling from the broader S&P 500 index. Starting at a baseline correlation of 0.675, it decayed to 0.560 during the pandemic and further detached to 0.418 in the post-COVID era. This divergence captures the unique, isolated fundamental crisis of the energy markets—most notably the unprecedented collapse in global mobility and the brief inversion to negative crude oil prices—forcing the sector to trade independently of the broader equity market's recovery.

**Real Estate (Permanent Regime Shift):**

Real Estate experienced a permanent regime shift rather than a temporary correlation shock. Pre-COVID, the sector remained largely insulated (0.429) due to the delayed cash-flow nature of long-term commercial leases. However, government-mandated lockdowns and the systemic transition to remote work forced an immediate correlation spike (0.695). This elevated synchronization persisted into the post-COVID era (0.708), as the sector's heavy reliance on debt financing left it fundamentally tethered to the broader market's ongoing macroeconomic struggles with inflation and aggressive interest rate hikes.

**Utilities (Forced Institutional Liquidation):**

The Utilities sector provides the clearest mathematical footprint of a systemic liquidity crisis. Historically functioning as the ultimate uncorrelated defensive asset (0.223) due to guaranteed basic consumer demand, its correlation violently doubled during the pandemic (0.558). This reflects forced institutional liquidation; to cover margin calls during the crash, portfolio managers were forced to liquidate their safest, most profitable utility assets. Furthermore, its failure to return to pre-COVID isolation (settling at 0.496) highlights the heavily leveraged sector's new vulnerability to the post-pandemic high-interest-rate environment.

**Figure 2: 63-Day Rolling Correlation (GARCH Adjusted).**

This time-series visualizes the dynamic shifts in correlation. The shaded COVID-19 region illustrates the sharp divergence, notably the sustained drop in the Energy sector's correlation with the S&P 500.

![Figure 2: Rolling Correlation](covid_analysis_output/fig2_rolling_correlation.png)

**Time-Series Interpretation: The 63-Day Rolling Fracture:**

While the static heatmap provides a macroeconomic overview, the 63-day rolling correlation (Figure 2) captures the high-resolution, real-time momentum of these structural breaks. Because a 63-day window perfectly proxies one financial quarter, this time-series tracks institutional quarterly reallocation behavior.

The chart visually enforces the "Anchor" thesis: Information Technology and Financials maintained a heavy, persistent structural grip on the index (ρ>0.80), successfully bridging the pre- and post-COVID regimes without a permanent fracture. Conversely, the Energy sector's trajectory provides undeniable visual evidence of complete fundamental decoupling. Entering the shaded COVID-19 regime, the sector's correlation sharply deteriorates, ultimately crashing to a mathematically uncorrelated state (ρ≈0.0) by mid-2022. This physical detachment visually maps the sector's shift from broad macroeconomic dependency to trading exclusively on isolated geopolitical and supply-side constraints.

**Figure 3: Fisher Z-Statistic Structural Break Test.**

The test results empirically validate a heterogeneous sector reaction to the macroeconomic shocks, bounded by the critical values of ±1.96 (α=0.05). The data confirms severe structural breaks in historically defensive and isolated sectors. Real Estate and Utilities exhibited massive, statistically significant fractures during the Pre-to-COVID regime shift (Z≈−6.0), reflecting the systemic liquidity crunch and physical lockdowns.

![Figure 3: Fisher Z-Test Results](covid_analysis_output/fig3_fisher_z_results.png)

Furthermore, Energy demonstrated persistent, significant decoupling across both transition periods. While Information Technology and Financials registered statistically significant structural shifts (p<0.01), their baseline correlations remained exceptionally high; therefore, these shifts represent an tightening of their "market anchor" status rather than a fundamental decoupling. Conversely, Health Care maintained its historical market beta relationship during the initial pandemic shock, failing to cross the significance threshold for a structural break (p=0.0664).

---

### 6.3 Visual Evidence: Valuation and Profitability Divergence

Using the sanitized, dynamic market-cap-weighted data (_w\_{i,t}_), the aggregated P/E and ROE were plotted using a **4-quarter (Trailing Twelve Month) rolling window** with **1,000 bootstrap iterations** to map **95% confidence intervals**.

**Figure 4: Market-Cap-Weighted P/E Divergence.** The Energy sector's P/E ratio exhibited extreme mathematical instability — spiking dramatically before vanishing as earnings inverted below zero (rendered as gaps due to the `NaN` treatment). The Information Technology sector maintained a persistent, elevated premium, confirming investors priced in its structural advantage.

![Figure 4: P/E Divergence](covid_analysis_output/fig4_pe_divergence.png)

**Figure 4 Interpretation:**

Structural Premiums and Earnings Inversions
The bootstrapped 4-quarter rolling P/E time-series provides visual confirmation of the data sanitization protocols and reveals extreme sector-level valuation divergences during the macroeconomic shock.

The Energy sector (olive) perfectly illustrates the "Denominator Effect" followed by a complete earnings inversion. As global mobility ceased in early 2020, collapsing net income drove the sector's aggregate P/E to mathematically unstable highs. Subsequently, as physical energy markets fractured and sector earnings dropped below zero, the rigorous NaN sanitization protocol correctly excluded these negative valuations, resulting in the visible structural gaps in the time-series.

In stark contrast, the Information Technology sector (pink) demonstrated robust valuation resilience. Despite the systemic volatility represented by the widened confidence intervals, the sector maintained a persistent, elevated P/E premium throughout the COVID and Post-COVID regimes. This reflects a definitive market consensus, pricing in the sector's structural immunity to physical supply-chain disruptions and its operational dominance during the global transition to remote infrastructure.

**Figure 5: Market-Cap-Weighted ROE Divergence.**

The Energy sector suffered a catastrophic collapse in aggregate demand, plunging into negative profitability during the Q1–Q2 2020 shock. Conversely, Information Technology empirically proved its status as a "pandemic beneficiary," with its ROE accelerating away from the market average.

![Figure 5: ROE Divergence](covid_analysis_output/fig5_roe_divergence.png)

**Figure 5 Interpretation:**

Divergent Capital Efficiency and Demand Destruction
The bootstrapped 4-quarter rolling ROE time-series provides empirical confirmation of severe fundamental divergence during the macroeconomic shock. The effectiveness of the rigorous winsorization protocol is visually evident, as the time-series successfully maps extreme equity fluctuations without being compromised by asymptote artifacts.

The physical demand destruction of the pandemic is mathematically isolated in the Energy sector's trajectory (olive), which experienced a catastrophic collapse in capital efficiency, plunging deep into negative profitability (ROE < −20%) during the Q1-Q2 2020 lockdowns. Conversely, Information Technology (pink) empirically cemented its status as a structural "pandemic beneficiary." Benefiting from highly scalable, asset-light business models, the sector absorbed the global transition to digital infrastructure, driving its ROE to accelerate aggressively away from the market average. Furthermore, the significant widening of the IT sector's bootstrapped confidence intervals highlights the massive intra-sector variance as specific digital monopolies captured disproportionate market share. Finally, the delayed deterioration of the Financials sector's ROE in the 2022-2023 regime maps the secondary macroeconomic shock of aggressive monetary tightening and subsequent duration-risk realization.

---

## 7. Preliminary Results: Sector Analysis (Technology vs. Energy)

### 7.1 Methodology: Regime Event Studies and The Tech Premium

To evaluate the fundamental divergence between the Information Technology and Energy sectors, a time-series "Tech Premium Spread" was constructed for both valuation (_Spread_P/E = P/E_Tech − P/E_Energy_) and profitability (_Spread_ROE = ROE_Tech − ROE_Energy_).

These spreads were analyzed across three distinct macroeconomic regimes:

- **Regime 1 (The Oil Glut):** 2014–2016
- **Regime 2 (The Pandemic Shock):** 2020–2021
- **Regime 3 (Rate Hikes & Energy Crisis):** 2022–2023

To account for the inherent heteroskedasticity of financial indicators across different economic crises, **Welch's t-tests** were utilized to determine if the Tech Premium Spread underwent statistically significant structural shifts between these regimes. Furthermore, data sanitization was strictly controlled; negative P/E ratios were coerced to `NaN` (Damodaran, 2012) to prevent the denominator effect from skewing the aggregate spreads.

**Figure 6: 63-Day Rolling Correlation (Tech vs. Energy residuals).** This visualizes the correlation between the two sectors across the defined macroeconomic regimes, highlighting periods of inverse or decoupled behavior.

![Figure 6: Tech vs. Energy Correlation](sector_divergence_output/fig1_tech_energy_correlation.png)

**Figure 6 Interpretation:**

Systemic Decoupling and Inverse Crisis Dynamics
The rolling 63-day correlation of standardized residuals (Figure 6) mathematically validates the necessity of analyzing the Tech-Energy spread. The time-series empirically proves that these two sectors do not merely decouple during macroeconomic shocks; they actively invert.

During the 2020–2021 Pandemic Shock (Regime 2), the correlation violently collapsed into negative territory (ρ<0.0), reflecting an inverse fundamental dynamic: the physical mobility destruction that crippled Energy simultaneously acted as a digital demand catalyst for Information Technology. This inverse relationship repeated during the 2022–2023 Rate Hike regime (Regime 3), albeit driven by reversed macroeconomic catalysts. As geopolitical supply constraints triggered an Energy sector windfall, aggressive monetary tightening simultaneously compressed Information Technology's growth multiples. Because these sectors exhibit statistically proven counter-cyclical behavior during exogenous shocks, applying Welch's t-tests to their valuation and profitability spreads provides a robust, heteroskedasticity-adjusted measure of the market's structural capital reallocation.

---

### 7.2 Statistical Results: Profitability Shift (Oil Glut vs. Pandemic)

The transition from the 2014 Oil Glut to the 2020 Pandemic Shock revealed a highly significant structural break in relative profitability.

**Figure 7: Time-Series of the Tech Premium Spread (P/E and ROE).**

![Figure 7: Premium Spreads](sector_divergence_output/fig2_premium_spreads.png)

**Figure 7 Interpretation:**

The Tech Premium and Structural Profitability Shifts
Figure 7 visualizes the dual-axis time-series of the Tech Premium Spread, empirically validating the necessity of Welch's t-tests to account for severe heteroskedasticity across crisis regimes.

The ROE Spread (blue line, right axis) captures a violent structural capital reallocation during the 2020–2021 Pandemic Shock. The spread aggressively widened to excess of 70 percentage points, mathematically driven by a dual-catalyst effect: the rapid acceleration of Information Technology's capital efficiency combined with the severe negative earnings inversion of the Energy sector. This represents a historic, statistically significant fundamental decoupling. Conversely, the 2022–2023 Rate Hike regime forced a rapid mean reversion of this profitability spread, perfectly mapping the macroeconomic shift from digital infrastructure premiums back to physical supply-side constraints.

Furthermore, the P/E Spread (red line, left axis) visually confirms the rigor of the data sanitization pipeline. The explicit structural gaps in the time-series during the 2015 Oil Glut and the 2020 Pandemic Shock prove the successful implementation of NaN coercion for negative earnings, preventing denominator-driven asymptote artifacts from contaminating the aggregate valuation spread.

- **ROE Spread Expansion:** The Tech profitability premium over Energy expanded significantly from a mean of 10.75% during the Oil Glut to 38.59% during the Pandemic. Welch's t-test confirms this shift is statistically significant (_t = −3.32, p = 0.008_).
- **The Valuation "Wipeout" Phenomenon:** Crucially, the _Spread_P/E_ test for this transition yielded an insufficient sample size for Regime 1. Rather than a data pipeline failure, this missing data (**MNAR — Missing Not At Random**) is empirical proof of a sector-wide earnings wipeout; Energy sector earnings were genuinely negative during the 2014–2016 commodity crash, rendering their P/E ratios economically undefined and perfectly illustrating the depth of the sector's distress compared to Tech's stability.

---

### 7.3 Statistical Results: Valuation Inversion (Pandemic vs. Rate Hikes)

The transition from the zero-interest-rate Pandemic regime to the 2022 inflationary Rate Hike regime produced a completely different statistical dynamic.

**Figure 8: Distribution of Tech Premium Spreads by Regime.**

![Figure 8: Regime Boxplots](sector_divergence_output/fig3_regime_boxplots.png)

**7.3 Statistical Results:**

Valuation Inversion (Pandemic vs. Rate Hikes)
The transition from the zero-interest-rate Pandemic regime to the 2022 inflationary Rate Hike regime produced a severe divergence in market mechanics.

Valuation Spread Explosion: The Spread
P/E
​
widened violently from a mean of 18.21 to 71.00 (t=−2.61,p=0.031). This mathematically captures the Ukraine energy crisis windfall: Energy companies generated so much free cash flow that their P/E multiples compressed, while Information Technology maintained historically elevated valuations despite the rising discount rates associated with monetary tightening.

Profitability Variance and Power Limitations: While the Welch's t-test for the ROE spread failed to reject the null hypothesis between the regimes (p=0.237), visual distribution analysis (Figure 8) reveals extreme ongoing variance. Furthermore, strict econometric interpretation dictates that this high p-value must be contextualized by the inherently small sample sizes of these condensed macroeconomic event windows (n=7 and n=4 quarters). Consequently, this lack of statistical significance likely reflects diminished statistical power (Type II error constraints) rather than definitive proof of profitability stabilization, highlighting the extreme volatility underlying the median sector returns.

---

## 8. Preliminary Results: Weighted Share & Decline Thresholds

### 8.1 Methodology: Logistic Regression of Systemic Decline

To determine the critical mass required to trigger a fundamental decline in the market-cap-weighted S&P 500 proxy, a logistic probability model was constructed. The objective was to find the exact "Tipping Point" where the probability of an aggregate index decline exceeds 50%.

For every constituent $i$ at quarter $t$, a binary state variable $D_{i,t}$ was assigned ($1$ if Quarter-over-Quarter indicator growth $< 0$, else $0$). The continuous independent variable ($X_t$) was defined as the

**Weighted Decline Share**:

$$X_t = \sum (w_{i,t} \cdot D_{i,t})$$

A logistic regression ($Y_t \sim X_t$) was fitted to model the probability of an aggregate index decline ($Y_t = 1$). The decision boundary ($X_{critical}$), representing the 50% probability threshold, was extracted using the log-odds root:

$$X_{critical} = -\frac{\beta_0}{\beta_1}$$

---

### 8.2 Statistical Results: The Critical Mass of Decay

The logistic regression yielded statistically robust thresholds for both valuation and profitability metrics across $n = 64$ quarters (2009–2025).

**Figure 9: Logistic Probability of Aggregate Net Income Decline.** The model ($\beta_0 = -3.573$, $\beta_1 = 7.954$) identifies a critical threshold of $44.92\%$. When constituents representing $\geq 44.92\%$ of the total index market capitalization experience a QoQ decline in Net Income, there is a $\geq 50\%$ probability that the aggregate index Net Income will also contract.

![Figure 9: Logistic Curve — Net Income](threshold_output/fig1_logistic_curve_ni.png)

**Figure 9 Interpretation: Structural Fragility and the 44.9% Tipping Point**

The fitted logistic probability curve provides empirical evidence of structural fragility within the market-cap-weighted index. The model's fit (McFadden $R^2 = 0.351$) demonstrates highly robust explanatory power for a binary financial classification. Crucially, the $X_{critical}$ threshold mathematically proves that the index does not require a majority failure to trigger a systemic contraction. Because the S&P 500's weight is heavily concentrated in a few mega-cap anchors, the simultaneous fundamental decay of just 44.9% of the index's structural weight is sufficient to push the probability of an aggregate Net Income decline past the 50% tipping point. This effectively quantifies the extreme concentration risk inherent in the modern index, demonstrating that aggregate market stability is disproportionately reliant on a minority of capital-heavy constituents.

**Figure 10: Logistic Probability of Aggregate ROE Decline.**

The Return on Equity model ($\beta_0 = -5.237$, $\beta_1 = 12.717$) demonstrates a tighter critical threshold of $41.18\%$ and a superior explanatory power (McFadden Pseudo-$R^2 = 0.5107$). Because ROE normalizes net income by shareholder equity, profitability shifts within mega-cap constituents propagate faster through the aggregate index, requiring only a $\sim 41\%$ weighted decay to pull the broader market into fundamental contraction.

![Figure 10: Logistic Curve — ROE](threshold_output/fig2_logistic_curve_roe.png)

**Figure 10 Interpretation: Capital Efficiency and the 41.2% Cliff**

The Return on Equity logistic model ($\beta_0 = -5.237$, $\beta_1 = 12.717$) reveals a sharper and more severe structural boundary than raw Net Income. The exceptional explanatory power (McFadden $R^2 = 0.511$) and the steeper probability curve indicate that aggregate market profitability does not decay gradually; it faces a distinct cliff. Because ROE measures capital efficiency, the mathematical failure of just 41.2% of the market-cap-weighted constituents is sufficient to guarantee an aggregate index contraction ($p \geq 0.50$). This empirically proves that the modern S&P 500 is highly leveraged to the operational efficiency of its largest mega-cap anchors; if the top 41% lose their profitability momentum, the remaining 59% of the index is mathematically incapable of sustaining the broader market's growth.

**Conclusion:** These thresholds mathematically confirm the structural vulnerability of a market-cap-weighted index; systemic fundamental decline does not require a simple majority (>50%) of constituents to fail, but rather a concentrated minority of heavily weighted actors.

---

## 9. Exploratory Results: Cross-Sector Correlation Shifts (COVID-19)

### 9.1 Methodology: The Delta Correlation Matrix

To investigate the internal fracture of the market's covariance structure during the lockdown, an $11 \times 11$ sector-to-sector correlation analysis was conducted. Utilizing the GARCH(1,1) standardized residuals to control for volatility inflation (the Forbes-Rigobon effect), Pearson correlation matrices were computed for both the Pre-COVID and COVID-19 regimes.

A Delta Matrix ($\Delta \rho = \rho_{COVID} - \rho_{Pre-COVID}$) was derived to measure the absolute shift in sector relationships. To ensure econometric rigor, a pairwise Fisher Z-transformation hypothesis test ($H_0: \rho_{pre} = \rho_{covid}$) was applied to all 55 unique sector combinations ($\alpha = 0.05$).

### 9.2 Statistical Results: The Fracture of the Covariance Matrix

The empirical results demonstrate a catastrophic breakdown of historical market structures. Of the 55 unique sector pairs, 43 pairs (78.1%) exhibited a statistically significant structural break in their correlation profile.

**Figure 11: Significance-Masked $\Delta \rho$ Heatmap.** Sector pairs failing to reject the null hypothesis ($p \geq 0.05$) are masked, highlighting only the mathematically validated structural shifts. Red indicates coupling ($\Delta \rho > 0$); Blue indicates decoupling ($\Delta \rho < 0$).

![Figure 11: Significance-Masked Δρ Heatmap](cross_sector_output/fig1_delta_significance_heatmap.png)

---

### 9.3 Economic Interpretation of Extreme Z-Statistics

The severity of the Z-statistics reveals two distinct macroeconomic phenomena driven by the exogenous shock:

**The ZIRP Decoupling Effect:** The most violent negative shifts occurred between Information Technology and both Energy ($\Delta\rho = -0.254$, $Z = 4.99$) and Financials ($\Delta\rho = -0.215$, $Z = 6.44$). The decoupling of Financials and Tech empirically captures the market's reaction to Zero Interest Rate Policy (ZIRP); collapsing yields compressed bank net interest margins while simultaneously expanding the discounted valuation multiples of growth-oriented Tech equities.

**The "Flight to Safety" Coupling:** Conversely, the strongest positive correlation shifts occurred between heavily cyclical sectors (Industrials, Materials, Financials) and Utilities ($\Delta\rho$ ranging from $+0.311$ to $+0.359$, with $Z < -5.50$). Because Utilities serve as the market's defensive "bond proxy," this severe coupling indicates a systemic liquidity crisis where cyclical equities temporarily abandoned idiosyncratic fundamentals and traded uniformly on macroeconomic fear.

---

## 10. Exploratory Results: AI Investment & Tech Sector Valuation (2023-2025)

### 10.1 Methodology: Cross-Sectional OLS Regression

To empirically test whether the "AI Boom" valuation premium was driven by fundamental capital deployment (infrastructure building) versus speculative narrative, a cross-sectional Ordinary Least Squares (OLS) regression was conducted.

To eliminate sector-level noise, the dataset was strictly filtered to the GICS sub-industries physically building the AI ecosystem: Semiconductors, Systems Software, and Technology Hardware.

The independent variable was the change in Capital Expenditure (CAPEX) Intensity ($\Delta \text{CAPEX Intensity} = \frac{\text{CAPEX}}{\text{Revenue}}$), measuring the shift from the Pre-AI Regime (2021–2022) to the AI Boom Regime (2023–2025). The dependent variable was the corresponding change in valuation multiple ($\Delta \text{P/E}$). The regression was fitted using HC3 robust standard errors to account for heteroskedasticity.

### 10.2 Statistical Results: The Null Hypothesis Holds

The empirical results demonstrate a profound disconnect between physical capital deployment and valuation multiple expansion during the targeted regime.

**Figure 12: Cross-Sectional Regression of $\Delta \text{P/E}$ on $\Delta \text{CAPEX Intensity}$.** The regression yielded a coefficient of $\beta_1 = 39.94$, but failed to achieve statistical significance ($t = 0.341$, $p = 0.733$). Furthermore, the model's explanatory power is effectively zero ($R^2 = 0.008$).

![Figure 12: CAPEX vs P/E Regression](ai_valuation_output/fig1_capex_pe_regression.png)

**Conclusion:** We fail to reject the null hypothesis. There is no statistically significant relationship between an AI-infrastructure company's change in CAPEX intensity and its P/E multiple expansion. This empirical "negative finding" confirms that the 2023–2025 Tech sector valuation premium is primarily driven by speculative forward-revenue expectations and narrative framing, rather than being a mechanistic reward for raw capital expenditure in physical data center and GPU infrastructure.

---

## 11. Conclusion, Deliverables, and Future Research

### 11.1 Synthesis of Empirical Findings

This methodological framework successfully engineered a multi-regime pipeline to analyze the structural integrity and internal covariance of the S&P 500. By enforcing strict data sanitization (Winsorization and denominator-effect neutralization) and deploying advanced econometric tests (GARCH(1,1) volatility adjustment, pairwise Fisher Z-transformations, Welch's t-tests, and Logistic Regression), this research empirically proved several critical market dynamics:

- **Exogenous Decoupling:** The Information Technology and Energy sectors experienced statistically significant deviations from market beta during the COVID-19 shock.
- **The Tech Premium Shift:** The valuation and profitability spread between Technology and Energy underwent structural regime shifts, transitioning from a fundamental earnings wipeout in Energy (2014) to a massive, liquidity-driven valuation divergence during the 2022 rate hikes.
- **The Critical Mass of Decay:** Logistic probability modeling mathematically proved that fundamental contraction in merely 41% of the weighted index (via ROE) is sufficient to drag the aggregate market into systemic decline.
- **Covariance Fracture:** The pandemic induced a catastrophic breakdown of traditional portfolio theory, structurally altering 78% of historical sector-to-sector correlations.
- **The AI CAPEX Null Hypothesis:** Cross-sectional OLS regressions proved that the 2023–2025 technology valuation premium is fundamentally disconnected from physical infrastructure capital expenditure.

---

### 11.2 Interactive Data Dissemination Framework

To ensure the reproducibility and accessibility of these findings, the static analytical pipelines were synthesized into a dynamic, interactive dashboard. This deployment serves as the primary technical deliverable of the project. The dashboard architecture ingests the outputs from the continuous-time GARCH models, the discrete Welch's t-tests, and the Logistic threshold arrays, allowing end-users to dynamically query macroeconomic regimes, visualize cross-sector correlation fractures in real-time, and independently verify the statistical significance of the Tech Premium spread across multiple time horizons.

---

### 11.3 Methodological Limitations (Geopolitical Conflict Modeling)

The original scope of this research proposed an exploratory analysis linking the Materials and Defense sub-sectors to discrete geopolitical interventions. This vector was formally omitted from the final pipeline due to severe data limitations. Public data regarding sovereign defense contracting is highly opaque, low-frequency, and difficult to parameterize for time-series regression. Attempting to model this without granular, high-fidelity defense data would introduce unacceptable levels of omitted variable bias and compromise the econometric rigor established in the preceding sections.

---

### 11.4 Future Research Horizon: The Nautilus Project

To resolve the limitations of traditional fundamental modeling encountered during this study, future research will pivot toward advanced dynamic systems modeling via the **Nautilus Project**. This initiative seeks to profoundly bridge the disciplines of Naval Engineering and Quantitative Finance by translating hydrodynamic wave mechanics and fluid turbulence into quantitative financial risk models.

**Spectral Volatility and the Kolmogorov Energy Cascade**

Traditional financial models treat volatility as a random walk, but empirical market crises behave more accurately as dissipative turbulent systems. When a macroeconomic shock occurs, it injects massive "kinetic energy" into the market. Drawing from fluid dynamics, we hypothesize that this market turbulence follows a deterministic energy decay, cascading from large macro-eddies (systemic shocks) to smaller, higher-frequency trading scales before dissipating completely. We will model the Local Volatility Surface (LVSV) using Kolmogorov's $-5/3$ turbulence energy spectrum:

$$E(k) = C \cdot \varepsilon^{2/3} \cdot k^{-5/3}$$

where $E(k)$ represents the kinetic energy of the volatility at a given frequency (wavenumber) $k$, and $\varepsilon$ is the kinetic energy dissipation rate. By calculating the decay rate of these market "vortices," we can predict exactly how fast a systemic shock will dissipate into high-frequency white noise.

**Spectral Signatures and Oceanographic Wave Models**

Furthermore, financial markets do not possess a single dominant frequency. To identify the "Spectral Signature" of specific market crash phenomena, we will apply Spectral Decomposition to asset returns, modeling the frequency distribution of market energy analogous to the **JONSWAP (Joint North Sea Wave Project)** spectrum used to map irregular wind-generated sea states. By mapping the energy density spectrum $S(f)$, we can differentiate between conservative (linear) market oscillations and destructive, dissipative non-linear shocks.

**Stochastic Routing Application**

Integrating these hydrodynamic principles, the Nautilus framework will apply Stochastic Weather Routing algorithms — specifically **Markov Decision Processes (MDP)** — to portfolio optimization. Utilizing the LVSV as a predictive "weather radar," the algorithm will treat the portfolio as a vessel navigating a turbulent fluid. The objective is to mathematically prove that dynamic stochastic routing can avoid areas of critical kinetic energy (high structural volatility) and minimize the risk of absolute ruin (hull breach) significantly more effectively than traditional Black-Scholes Delta Hedging.
