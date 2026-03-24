"""
Merge da Planilha_Geral_Consolidada_Q1_2026.csv
com Embeddings_Images_Q1_2026.csv e Embeddings_Videos_Q1_2026.csv

Resultado: Planilha_Geral_com_Embeddings_Q1_2026.csv
  - Todos os 6243 criativos
  - Embeddings de imagem (emb_0..9) — 6243 linhas
  - Embeddings de vídeo (vid_emb_0..9) — preenchidos apenas where exists (2076)
"""

import pandas as pd

planilha = pd.read_csv("Planilha_Geral_Consolidada_Q1_2026.csv")
img      = pd.read_csv("Embeddings_Images_Q1_2026.csv")
vid      = pd.read_csv("Embeddings_Videos_Q1_2026.csv")

EMB_COLS = [f"emb_{i}" for i in range(10)]

# ── Imagens: renomeia colunas para evitar conflito com colunas existentes ──
img_merge = img[["creative_id"] + EMB_COLS].rename(
    columns={c: f"img_{c}" for c in EMB_COLS}
)

# ── Vídeos: renomeia colunas com prefixo vid_ ──
vid_merge = vid[["creative_id"] + EMB_COLS].rename(
    columns={c: f"vid_{c}" for c in EMB_COLS}
)

# ── Merge ──
df = planilha.merge(img_merge, on="creative_id", how="left")
df = df.merge(vid_merge, on="creative_id", how="left")

OUTPUT = "Planilha_Geral_com_Embeddings_Q1_2026.csv"
df.to_csv(OUTPUT, index=False)

img_emb_cols = [f"img_emb_{i}" for i in range(10)]
vid_emb_cols = [f"vid_emb_{i}" for i in range(10)]

print(f"✅ Salvo: {OUTPUT}")
print(f"   Linhas : {len(df)}")
print(f"   Colunas: {len(df.columns)}")
print(f"\n   NaN img embeddings: {df[img_emb_cols].isna().sum().sum()}")
print(f"   NaN vid embeddings: {df[vid_emb_cols].isna().sum().sum()}")
print(f"   (esperado; apenas {2076} criativos têm vídeo)\n")
print("Colunas finais:")
for c in df.columns:
    print(f"  {c}")
