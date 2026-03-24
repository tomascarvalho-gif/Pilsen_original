"""
merge_embeddings_pipeline.py
────────────────────────────
Task 1: Flatten 1D (image) or 2D (video) embeddings from individual JSON files
         into a DataFrame with columns:
           url | emb_1_mean..emb_10_mean | emb_1_var..emb_10_var

Task 2: LEFT JOIN with TIM CSV on a unified merge_url column
         (video_public_storage_url preferred, fallback to public_storage_url)
"""

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

# ─── Config ───────────────────────────────────────────────────────────────────
TIM_CSV     = "Dados Creatives + Performance Tim Q1 2026.csv"
IMAGES_DIR  = Path("public_storage_url-3/indices")
VIDEOS_DIR  = Path("video_public_storage_url/indices")
N_DIMS      = 10
NAN_VECTOR  = np.full(N_DIMS * 2, np.nan)

MEAN_COLS = [f"emb_{i}_mean" for i in range(1, N_DIMS + 1)]
VAR_COLS  = [f"emb_{i}_var"  for i in range(1, N_DIMS + 1)]
EMB_COLS  = MEAN_COLS + VAR_COLS


# ─── Task 1 — Dimensionality Flattening ───────────────────────────────────────

def flatten_embedding(raw) -> np.ndarray:
    """
    Flatten a raw embeddings value (from JSON) into a 1×20 vector:
      [emb_1_mean, …, emb_10_mean, emb_1_var, …, emb_10_var]

    - 1D array of shape (10,)  → images: mean = values, var = zeros
    - 2D array of shape (T,10) → videos: mean and var across time axis=0
    - Missing/corrupted data   → 20 × np.nan
    """
    try:
        arr = np.array(raw, dtype=float)

        if arr.ndim == 1 and arr.shape[0] == N_DIMS:
            # Static image: mean IS the values, variance = 0
            return np.concatenate([arr, np.zeros(N_DIMS)])

        elif arr.ndim == 2 and arr.shape[1] == N_DIMS:
            # Video: compute mean and variance across time axis
            mean = arr.mean(axis=0)
            var  = arr.var(axis=0)
            return np.concatenate([mean, var])

        else:
            return NAN_VECTOR.copy()

    except Exception:
        return NAN_VECTOR.copy()


def url_from_filename(filename: str, base_url_pattern: str) -> str:
    """Reconstruct the GCS URL from the JSON filename (removes trailing .json)."""
    stem = filename.removesuffix(".json")
    return base_url_pattern + stem


def load_embeddings_df(indices_dir: Path, base_url: str) -> pd.DataFrame:
    """
    Read all JSON files in an indices directory and return a DataFrame:
      url | emb_1_mean..emb_10_mean | emb_1_var..emb_10_var
    """
    records = []
    for path in sorted(indices_dir.glob("*.json")):
        try:
            with open(path) as f:
                d = json.load(f)
            raw_emb = d.get("embeddings", None)
            vector  = flatten_embedding(raw_emb) if raw_emb is not None else NAN_VECTOR.copy()
        except Exception:
            vector = NAN_VECTOR.copy()

        url = url_from_filename(path.name, base_url)
        row = {"url": url}
        for col, val in zip(EMB_COLS, vector):
            row[col] = val
        records.append(row)

    return pd.DataFrame(records)


# Derive base URL from actual data so it stays flexible
def infer_base_url(tim_df: pd.DataFrame, col: str) -> str:
    """Extract the URL prefix (everything up to the filename) from the first valid value."""
    sample = tim_df[col].dropna().iloc[0]
    # Split at last '/' to get the directory prefix
    return sample.rsplit("/", 1)[0] + "/"


print("Loading TIM CSV...")
tim_df = pd.read_csv(TIM_CSV, low_memory=False)
print(f"  TIM shape: {tim_df.shape}")

# Infer base URLs from real data
BASE_URL_IMG = infer_base_url(tim_df, "public_storage_url")
BASE_URL_VID = infer_base_url(tim_df[tim_df["video_public_storage_url"].notna()], "video_public_storage_url")

print(f"\nBase URL (images): {BASE_URL_IMG}")
print(f"Base URL (videos): {BASE_URL_VID}")

print("\nBuilding embeddings DataFrame from JSON files...")
df_img = load_embeddings_df(IMAGES_DIR, BASE_URL_IMG)
print(f"  Image embeddings: {df_img.shape}")

df_vid = load_embeddings_df(VIDEOS_DIR, BASE_URL_VID)
print(f"  Video embeddings: {df_vid.shape}")

# Combine into single embeddings lookup
df_emb = pd.concat([df_img, df_vid], ignore_index=True)
print(f"  Combined embeddings: {df_emb.shape}")


# ─── Task 2 — Relational Merge ────────────────────────────────────────────────

print("\nBuilding merge_url (video preferred, fallback to image)...")
tim_df["merge_url"] = tim_df["video_public_storage_url"].fillna(tim_df["public_storage_url"])

print("Executing LEFT JOIN on merge_url ↔ url...")
merged_df = tim_df.merge(
    df_emb.rename(columns={"url": "merge_url"}),
    on="merge_url",
    how="left"
)

# Drop the temporary column
merged_df = merged_df.drop(columns=["merge_url"])

# ─── Output Report ────────────────────────────────────────────────────────────
n_total   = len(merged_df)
n_matched = merged_df["emb_1_mean"].notna().sum()
pct       = (n_matched / n_total) * 100

print("\n" + "═" * 55)
print(f"  Final merged DataFrame shape : {merged_df.shape}")
print(f"  TIM records with embedding   : {n_matched:,} / {n_total:,}  ({pct:.2f}%)")
print("═" * 55)

# Save result
OUTPUT = "TIM_with_Embeddings_Q1_2026.csv"
merged_df.to_csv(OUTPUT, index=False)
print(f"\n✅  Saved: {OUTPUT}")
