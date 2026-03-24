"""
Gera Embeddings_Videos_Temporal_Q1_2026.csv em formato LONGO:
  Uma linha por (criativo × frame), preservando a matriz completa.

Colunas:
  creative_id | filename | frame_index | time
  | engajamentoneural | cognitivedemand | focus
  | emb_0 | emb_1 | ... | emb_9
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path

VIDEOS_DIR = Path("video_public_storage_url/indices")
OUTPUT     = "Embeddings_Videos_Temporal_Q1_2026.csv"
EMB_COLS   = [f"emb_{i}" for i in range(10)]


def extract_creative_id(filename: str) -> str:
    parts = filename.split("_")
    return parts[1] if len(parts) >= 2 else filename


print("Processando vídeos em formato longo...")
records = []
vid_files = sorted(VIDEOS_DIR.glob("*.json"))
total = len(vid_files)

for idx, path in enumerate(vid_files):
    if idx % 200 == 0:
        print(f"  {idx}/{total}...", flush=True)
    try:
        with open(path) as f:
            d = json.load(f)

        emb    = d.get("embeddings", [])
        tempos = d.get("tempos", [])
        neural = d.get("engajamentoneural", [])
        cogn   = d.get("cognitivedemand",   [])
        focus  = d.get("focus",             [])

        if not emb:
            continue

        emb_array = np.array(emb, dtype=float)  # shape: (N, 10)
        if emb_array.ndim != 2 or emb_array.shape[1] != 10:
            continue

        n_frames = emb_array.shape[0]
        fname = path.name
        cid   = extract_creative_id(fname)

        for i in range(n_frames):
            row = {
                "creative_id":       cid,
                "filename":          fname,
                "frame_index":       i,
                "time":              tempos[i] if i < len(tempos) else float("nan"),
                "engajamentoneural": neural[i] if i < len(neural) else float("nan"),
                "cognitivedemand":   cogn[i]   if i < len(cogn)   else float("nan"),
                "focus":             focus[i]   if i < len(focus)   else float("nan"),
            }
            for j, v in enumerate(emb_array[i]):
                row[f"emb_{j}"] = v
            records.append(row)

    except Exception as e:
        print(f"  ⚠️  Erro em {path.name}: {e}")

df = pd.DataFrame(records)
col_order = (
    ["creative_id", "filename", "frame_index", "time",
     "engajamentoneural", "cognitivedemand", "focus"] + EMB_COLS
)
df = df[[c for c in col_order if c in df.columns]]
df.to_csv(OUTPUT, index=False)

print(f"\n✅ Salvo: {OUTPUT}")
print(f"   Linhas  : {len(df):,}  ({len(vid_files)} vídeos × ~{len(df)//len(vid_files)} frames)")
print(f"   Colunas : {len(df.columns)}")
print(f"   NaN emb : {df[EMB_COLS].isna().sum().sum()}")
