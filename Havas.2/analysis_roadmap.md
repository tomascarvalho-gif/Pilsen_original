# TIM Data Analysis Roadmap

This document outlines the planned tests to analyze the relationship between neuro-metrics (Neural Engagement, Cognitive Demand, Focus) and business performance (CTR/Clicks) in the TIM database.

## Phase 1: Data Preparation & Feature Engineering
1.  **Calculate New Neuro-Metrics (Videos Only):**
    *   Extract the **First 5 seconds mean** (first 10 samples) for all 3 neuro-metrics from the raw JSON files in `video_public_storage_url/indices/`.
    *   Extract the **Last 5 seconds mean** (last 10 samples) for all 3 neuro-metrics from the raw JSON files.
    *   Append these new metrics to the main dataset.
2.  **Define Cost Intervals (Buckets):**
    *   Analyze the distribution of the `parsed_cost` column.
    *   Create categorical buckets (e.g., Low Cost, Medium Cost, High Cost) using quartiles or fixed thresholds.
3.  **Ensure Trimester Data is Clean:**
    *   Verify the existence and format of the trimester column (e.g., Q1, Q2, etc.) or derive it from the `date_start` column.

## Phase 2: Execution of Tests

For every test defined below, the analysis will output:
*   Pearson/Spearman Correlations (vs CTR and Clicks).
*   Scatter plots with regression lines for significant correlations.
*   Quartile Analysis (Top 25% vs Bottom 25% performers).

### Test Suite A: Images Only
*   **Base Dataset:** Rows where `video_public_storage_url` is empty (`Dados_Creatives_Enriched_Q1_2026_Images_Only.csv`).
*   **Neuro-Metrics Used:** Global mean only (since images are static).
*   **Segmentation:**
    1.  Global (All Images).
    2.  By Trimester (e.g., Q1, Q2).
    3.  By Cost Interval (e.g., Low, Med, High).
    4.  Crosstab: By Trimester AND Cost Interval simultaneously.

### Test Suite B: Videos (Global Metrics)
*   **Base Dataset:** Rows where `video_public_storage_url` is populated (`Dados_Creatives_Enriched_Q1_2026_Videos_Only.csv`).
*   **Neuro-Metrics Used:** Global mean of the entire video duration.
*   **Segmentation:**
    1.  Global (All Videos).
    2.  By Trimester.
    3.  By Cost Interval.
    4.  Crosstab: By Trimester AND Cost Interval simultaneously.

### Test Suite C: Videos (First 5s vs Last 5s)
*   **Base Dataset:** Same as Test Suite B.
*   **Neuro-Metrics Used:** `metric_first_5s` and `metric_last_5s`.
*   **Hypothesis to Test:** Does the "Hook" (first 5s) or the "CTA/Closing" (last 5s) show a stronger correlation to CTR?
*   **Segmentation:**
    1.  Global (All Videos).
    2.  By Trimester.
    3.  By Cost Interval.
    4.  Crosstab: By Trimester AND Cost Interval simultaneously.

## Next Step for AI Assistant
When instructed to begin, proceed to **Phase 1** by writing a Python script to perform the data extraction and feature engineering.

## Phase 3: Final Report (COMPLETED)
The final comprehensive report has been generated at `Havas.2/TIM_Neuro_Final_Report.md`.
