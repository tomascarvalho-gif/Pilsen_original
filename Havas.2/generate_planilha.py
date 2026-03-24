import pandas as pd

df = pd.read_csv('Performance_Metrics_with_Taxonomy_Attributed_Q1_2026.csv')

# Let's inspect columns
cols_to_keep = [
    'creative_name', 'creative_id', 'from_date', 'last_date',
    'impressions', 'clicks', 'cost', 'parsed_cost',
    'Awareness_Score', 'Consideration_Score', 'Conversion_Score',
    'Awareness_impressions', 'Awareness_clicks', 'Awareness_cost',
    'Consideration_impressions', 'Consideration_clicks', 'Consideration_cost',
    'Conversion_impressions', 'Conversion_clicks', 'Conversion_cost',
    'CTR', 'CPM', 'CPC'
]

# Keep only columns that exist
cols = [c for c in cols_to_keep if c in df.columns]

df_res = df[cols]

output_name = 'Planilha_Geral_Metricas_Q1_2026.csv'
df_res.to_csv(output_name, index=False)
print(f"File saved to {output_name}")
