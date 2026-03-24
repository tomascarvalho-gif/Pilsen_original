"""
Gera uma planilha CSV geral com as colunas solicitadas:
  creative_name, creative_id, public_storage_url, video_public_storage_url,
  from_date, last_date, impressions, clicks, parsed_cost, cost,
  CTR, CPM, CPC,
  engajamentoneural, cognitivedemand, focus
"""

import pandas as pd

BASE_FILE     = "Performance_Metrics_with_Taxonomy_Attributed_Q1_2026.csv"
ENRICHED_FILE = "Dados_Creatives_Enriched_Q1_2026.csv"
OUTPUT_FILE   = "Planilha_Geral_Consolidada_Q1_2026.csv"

# 1. Carrega arquivos
print(f"Carregando {BASE_FILE}...")
df_base = pd.read_csv(BASE_FILE, low_memory=False)

print(f"Carregando {ENRICHED_FILE}...")
df_enriched = pd.read_csv(ENRICHED_FILE, low_memory=False)

# 2. Traz as métricas de neurociência (média geral, sem 5sec/peak)
NEURO_COLS = ["creative_id", "engajamentoneural", "cognitivedemand", "focus"]
neuro_cols_exist = [c for c in NEURO_COLS if c in df_enriched.columns]
df_neuro = df_enriched[neuro_cols_exist].drop_duplicates(subset="creative_id")

# 3. Merge
df = df_base.merge(df_neuro, on="creative_id", how="left")

# 4. Seleciona exatamente as colunas pedidas
COLS_FINAL = [
    "creative_name",
    "creative_id",
    "public_storage_url",
    "video_public_storage_url",
    "from_date",
    "last_date",
    "impressions",
    "clicks",
    "parsed_cost",
    "cost",
    "CTR",
    "CPM",
    "CPC",
    "engajamentoneural",
    "cognitivedemand",
    "focus",
]

cols = [c for c in COLS_FINAL if c in df.columns]
df_out = df[cols]

# 5. Salva
df_out.to_csv(OUTPUT_FILE, index=False)
print(f"\n✅ Planilha salva: {OUTPUT_FILE}")
print(f"   Linhas  : {len(df_out)}")
print(f"   Colunas : {list(df_out.columns)}")
