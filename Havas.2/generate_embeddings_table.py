"""
Gera duas tabelas CSV com os embeddings neurais:
  - Embeddings_Images_Q1_2026.csv  (6.243 linhas)
  - Embeddings_Videos_Q1_2026.csv  (2.076 linhas)

Colunas:
  creative_id | filename | engajamentoneural | cognitivedemand | focus
  | emb_0 | emb_1 | ... | emb_9
"""

import json
import os
import numpy as np
import pandas as pd
from pathlib import Path

IMAGES_DIR = Path("public_storage_url-3/indices")
VIDEOS_DIR = Path("video_public_storage_url/indices")
OUTPUT_IMG  = "Embeddings_Images_Q1_2026.csv"
OUTPUT_VID  = "Embeddings_Videos_Q1_2026.csv"

EMB_COLS = [f"emb_{i}" for i in range(10)]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def extract_creative_id(filename: str) -> str:
    """O creative_id é a segunda parte do nome do arquivo separada por '_'."""
    parts = filename.split("_")
    return parts[1] if len(parts) >= 2 else filename


def safe_mean(val):
    """Retorna a média de uma lista ou o próprio valor se for escalar."""
    if isinstance(val, (list, tuple)):
        return float(np.mean(val))
    return float(val) if val is not None else float("nan")


# ──────────────────────────────────────────────────────────────────────────────
# 1. IMAGENS
# ──────────────────────────────────────────────────────────────────────────────
print("Processando imagens...")
img_records = []
img_files = sorted(IMAGES_DIR.glob("*.json"))

for path in img_files:
    try:
        with open(path) as f:
            d = json.load(f)

        emb = d.get("embeddings", [])
        if not emb or len(emb) != 10:
            continue  # ignora JSONs sem embedding válido

        fname = path.name
        record = {
            "creative_id":       extract_creative_id(fname),
            "filename":          fname,
            "engajamentoneural": d.get("engajamentoneural", float("nan")),
            "cognitivedemand":   d.get("cognitivedemand",   float("nan")),
            "focus":             d.get("focus",             float("nan")),
        }
        for i, v in enumerate(emb):
            record[f"emb_{i}"] = v

        img_records.append(record)

    except Exception as e:
        print(f"  ⚠️  Erro em {path.name}: {e}")

df_img = pd.DataFrame(img_records)
cols_img = ["creative_id", "filename", "engajamentoneural", "cognitivedemand", "focus"] + EMB_COLS
df_img = df_img[[c for c in cols_img if c in df_img.columns]]
df_img.to_csv(OUTPUT_IMG, index=False)
print(f"  ✅ {OUTPUT_IMG} — {len(df_img)} linhas, {len(df_img.columns)} colunas")


# ──────────────────────────────────────────────────────────────────────────────
# 2. VÍDEOS  (mean-pooling ao longo do tempo)
# ──────────────────────────────────────────────────────────────────────────────
print("Processando vídeos...")
vid_records = []
vid_files = sorted(VIDEOS_DIR.glob("*.json"))

for path in vid_files:
    try:
        with open(path) as f:
            d = json.load(f)

        emb = d.get("embeddings", [])
        if not emb:
            continue

        # emb pode ser lista de vetores (N × 10) ou lista de escalares (10,)
        emb_array = np.array(emb, dtype=float)
        if emb_array.ndim == 2:
            # N frames × 10 dims → média temporal
            emb_mean = emb_array.mean(axis=0)
        elif emb_array.ndim == 1 and len(emb_array) == 10:
            emb_mean = emb_array
        else:
            continue  # estrutura inesperada

        fname = path.name
        record = {
            "creative_id":       extract_creative_id(fname),
            "filename":          fname,
            # métricas também são séries temporais → média
            "engajamentoneural": safe_mean(d.get("engajamentoneural")),
            "cognitivedemand":   safe_mean(d.get("cognitivedemand")),
            "focus":             safe_mean(d.get("focus")),
        }
        for i, v in enumerate(emb_mean):
            record[f"emb_{i}"] = v

        vid_records.append(record)

    except Exception as e:
        print(f"  ⚠️  Erro em {path.name}: {e}")

df_vid = pd.DataFrame(vid_records)
cols_vid = ["creative_id", "filename", "engajamentoneural", "cognitivedemand", "focus"] + EMB_COLS
df_vid = df_vid[[c for c in cols_vid if c in df_vid.columns]]
df_vid.to_csv(OUTPUT_VID, index=False)
print(f"  ✅ {OUTPUT_VID} — {len(df_vid)} linhas, {len(df_vid.columns)} colunas")

print("\nColunas (ambos os arquivos):")
print("  ", list(df_img.columns))
