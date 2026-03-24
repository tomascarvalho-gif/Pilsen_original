# TIM Dataset: Neuro-Metric Roadmap and Final Report

This report consolidates the tests defined in the `analysis_roadmap.md` and details the statistically significant findings derived from merging the `Havas/Tim` dataset with the individual neuro-metric values (Engajamento Neural, Cognitive Demand, Focus).



---

## Image Classification (Taxonomy) Overview

To enrich the creative analysis, an AI-powered image classifier was built to categorize static images into core funnel stages (Awareness, Consideration, Conversion). This was achieved by passing the image assets through the Gemini API to analyze their visual content, text, and structure.

**Taxonomy Classification Rubric:**

| Category | Prompt / Definition |
| :--- | :--- |
| **1. Awareness** | Brand focus, lifestyle, emotional, logo-centric. No specific offers. |
| **2. Consideration** | Features, benefits, comparisons, or plans (e.g. "Internet 500 Mega"). Educational. |
| **3. Conversion** | Hard sell. Prices (R$), discounts (%), or direct call-to-actions ("Assine Já", "Compre", "Contrate Agora", "Confira", "Saiba Mais", "Aproveite", "Aproveite Agora", "Consulte aqui"). |

**Next Steps & Taxonomy Definition**  
We plan to use these new taxonomy classes to achieve better accuracy in our correlation tests and to incorporate them as categorical features in our clustering models. We will meet with Billy to perfectly define the taxonomy framework to set and structure the final prompts for the AI classifier.

---

## Neuro-Metric Analysis Results

This section details the statistically significant correlations found between neuro-metric data (Neural Engagement, Cognitive Demand, Focus) and performance metrics (CTR) within the TIM dataset. 

### 1. Video Analysis

The analysis of video assets revealed that performance is highly dependent on both the campaign's cost tier and the specific moments within the video timeline.

**A. Cost Segmentation is Crucial**

The most critical finding across all video analysis is that neuro-metrics only hold predictive power for **Medium and High Cost campaigns (Spend > R$ 210)**. Low-Cost video campaigns showed zero correlation with neuro-metrics, likely because their performance is governed by algorithmic exploration rather than creative resonance. For instance, in High-Cost campaigns, Neural Engagement correlates positively with CTR (r = 0.1228, p = 0.0066) and Focus (Visual Complexity) correlates negatively (r = -0.1656, p = 0.0002).

**B. The "Closing" Effect (Final 5 Seconds)**

When analyzing the video timeline, the final 5 seconds showed far stronger correlations with CTR than the first 5 seconds. 
*   **Neural Engagement:** Higher Neural Engagement at the end of the video leads to higher CTR (r = 0.0634, p = 0.0039). 
*   **Focus (Visual Complexity):** A sharp drop in visual focus/intensity at the exact moment of the Call-to-Action (CTA) leads to higher CTR (r = -0.1099, p < 0.0001). 

**C. The Formula for High-Performing Videos**

For High-Cost campaigns, the optimal strategy is a "Closing Hook": 
*   Decrease visual complexity (Focus) at the end.
*   Simultaneously generate an increase in neural stimulation (Neural Engagement) through audio or core messaging during the final 5 seconds.

**D. Trimester Variations (The Hook)**

While the end of the video is generally more important, the requirement for the *start* of the video changes depending on the time of year:
*   **2024 Q3:** Required high Cognitive Demand from the very first frame to succeed (r = 0.6670, p = 0.0034).
*   **2025 Q1:** Heavily punished videos that started intensely. It rewarded a "slow burn" approach with lower initial Neural Engagement (r = -0.2356, p < 0.0001).

### 2. Image Analysis

Unlike videos, static image performance and their relation to neuro-metrics changed drastically depending on the Trimester analyzed.

**A. Global Averages Are Ineffective**

In the aggregate, without segmenting by time of year, images showed practically zero (insignificant) correlation with CTR across all metrics: Neural Engagement (r = 0.0255, p = 0.1001), Cognitive Demand (r = -0.0021, p = 0.8917), and Focus (r = 0.0154, p = 0.3197). Cost segmentation also did not reveal any hidden patterns for images.

**B. High Seasonality**

Segmenting by Trimester was the only method that showed clear signals for static images, indicating that the ideal creative strategy shifts throughout the year.
*   **2024 Q2:** Positive correlation with Neural Engagement (r = 0.2794, p < 0.0001).
*   **2025 Q1:** Strong negative correlation with both Neural Engagement (r = -0.3183, p < 0.0001) and Cognitive Demand (r = -0.2995, p < 0.0001). Simpler, calmer images performed better.
*   **2025 Q3:** Positive correlation with Neural Engagement (r = 0.2017, p = 0.0002). More engaging, complex images performed better.

---

## General Conclusion

The data conclusively shows that neuro-metric optimization is highly effective for TIM campaigns, provided the analysis accounts for budget tiers and seasonality. 

For videos, optimization efforts should focus entirely on High and Medium cost tiers, specifically engineering the final 5 seconds to have low visual complexity but high auditory/messaging engagement. For static images, a one-size-fits-all approach fails; the creative style must pivot between 'simple/calm' and 'complex/engaging' depending on the specific Trimester. Integrating these findings with the new Taxonomy Classifications will provide a robust, data-driven framework for all future creative production.


