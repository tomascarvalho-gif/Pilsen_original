"""
fix_master_pipeline.py
======================
Reconstruction of df_master.csv with mathematically correct 1×20 cognitive
embedding vectors, replacing the corrupted img_emb_*/vid_emb_* columns that
contained only temporal means for both images and videos.

Correct transformation (mirrors flatten_embedding() in merge_embeddings_pipeline.py):
  · Image creatives (static, 1D)  → cognitive_mean = embedding values
                                     cognitive_var  = 0.0  (zero-padded)
  · Video creatives (temporal, T×10) → cognitive_mean = mean(axis=0) across frames
                                        cognitive_var  = var(axis=0)  across frames

Sources:
  · Embeddings_Images_Q1_2026.csv           — 6,243 static image vectors (1×10)
  · Embeddings_Videos_Temporal_Q1_2026.csv  — 140,842 frame rows for 2,076 videos

Output:
  · df_master_v2.csv  (safe export; df_master.csv is NOT overwritten until verified)

Sanity checks printed to terminal:
  1. Total rows must remain 6,244
  2. Zero-inflation in cognitive_var_* must be ≈ 66.7%  (4,167 image-only rows)
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE       = Path(__file__).parent
MASTER_IN  = BASE / "df_master.csv"
MASTER_OUT = BASE / "df_master_v2.csv"
IMG_EMB    = BASE / "Embeddings_Images_Q1_2026.csv"
VID_TEMP   = BASE / "Embeddings_Videos_Temporal_Q1_2026.csv"

# ── Corporate column naming ────────────────────────────────────────────────────
N_DIMS     = 10
SRC_COLS   = [f"emb_{i}" for i in range(N_DIMS)]
MEAN_COLS  = [f"cognitive_mean_{i}" for i in range(N_DIMS)]
VAR_COLS   = [f"cognitive_var_{i}"  for i in range(N_DIMS)]
COG_COLS   = MEAN_COLS + VAR_COLS

# ── Stale columns to purge ─────────────────────────────────────────────────────
STALE_PREFIXES = ("img_emb_", "vid_emb_")


# ══════════════════════════════════════════════════════════════════════════════
# Step 1 — Load master and drop corrupted embedding columns
# ══════════════════════════════════════════════════════════════════════════════
print("═" * 70)
print("  fix_master_pipeline.py — Cognitive Embedding Reconstruction")
print("═" * 70)

print("\n[Step 1] Loading df_master.csv and purging stale columns...")
df_master = pd.read_csv(MASTER_IN)
print(f"         Shape on load    : {df_master.shape}")

stale_cols = [c for c in df_master.columns
              if any(c.startswith(p) for p in STALE_PREFIXES)]
df_master  = df_master.drop(columns=stale_cols)
print(f"         Columns dropped  : {stale_cols}")
print(f"         Shape after purge: {df_master.shape}")


# ══════════════════════════════════════════════════════════════════════════════
# Step 2 — Build cognitive vectors for IMAGE creatives
#          mean = static embedding values | var = 0.0 (zero-padding)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Step 2] Building image cognitive vectors (mean=values, var=0)...")
img_raw = pd.read_csv(IMG_EMB, usecols=["creative_id"] + SRC_COLS)
print(f"         Image embeddings loaded: {len(img_raw):,} rows")

# Deduplicate on creative_id (keep first occurrence)
img_raw = img_raw.drop_duplicates(subset="creative_id", keep="first")
print(f"         After dedup           : {len(img_raw):,} unique creative_ids")

img_cog = img_raw.rename(
    columns={src: mean for src, mean in zip(SRC_COLS, MEAN_COLS)}
).copy()

# Zero-pad all variance columns for image creatives
for var_col in VAR_COLS:
    img_cog[var_col] = 0.0

img_cog = img_cog[["creative_id"] + COG_COLS]
print(f"         cognitive_var zero% (images): "
      f"{(img_cog[VAR_COLS] == 0).all(axis=1).mean() * 100:.1f}%  ✓")


# ══════════════════════════════════════════════════════════════════════════════
# Step 3 — Build cognitive vectors for VIDEO creatives
#          mean = mean(emb_i, axis=0) | var = var(emb_i, axis=0) across frames
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Step 3] Building video cognitive vectors from temporal frames...")
vid_temp = pd.read_csv(VID_TEMP, usecols=["creative_id"] + SRC_COLS)
n_frames   = len(vid_temp)
n_vid_ids  = vid_temp["creative_id"].nunique()
print(f"         Temporal rows loaded  : {n_frames:,}")
print(f"         Unique video creatives: {n_vid_ids:,}")

# Aggregate: mean and variance across all frames per creative_id
vid_mean = (vid_temp
            .groupby("creative_id")[SRC_COLS]
            .mean()
            .reset_index()
            .rename(columns={src: mean for src, mean in zip(SRC_COLS, MEAN_COLS)}))

vid_var  = (vid_temp
            .groupby("creative_id")[SRC_COLS]
            .var(ddof=0)      # population variance (consistent with np.var default)
            .reset_index()
            .rename(columns={src: var for src, var in zip(SRC_COLS, VAR_COLS)}))

vid_cog = vid_mean.merge(vid_var, on="creative_id")
print(f"         Aggregated vectors    : {len(vid_cog):,} video creative_ids")

avg_nonzero_var = (vid_cog[VAR_COLS] > 0).mean().mean() * 100
print(f"         Non-zero var dims (avg across dims): {avg_nonzero_var:.1f}%  ✓")


# ══════════════════════════════════════════════════════════════════════════════
# Step 4 — Coalesce: start with image base, overwrite video creative rows
#          Video embedding is semantically superior (contains temporal dynamics)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Step 4] Coalescing image + video cognitive vectors...")

all_cog = img_cog.copy().set_index("creative_id")

# Update video rows with temporally-derived values
vid_cog_indexed = vid_cog.set_index("creative_id")
video_ids = vid_cog_indexed.index.intersection(all_cog.index)
all_cog.loc[video_ids, COG_COLS] = vid_cog_indexed.loc[video_ids, COG_COLS]

all_cog = all_cog.reset_index()

n_image_only = (~all_cog["creative_id"].isin(vid_cog_indexed.index)).sum()
n_video      = all_cog["creative_id"].isin(vid_cog_indexed.index).sum()
print(f"         Image-only creative vectors : {n_image_only:,}")
print(f"         Video creative vectors      : {n_video:,}")


# ══════════════════════════════════════════════════════════════════════════════
# Step 5 — Left join cognitive vectors into df_master
# ══════════════════════════════════════════════════════════════════════════════
print("\n[Step 5] Merging cognitive vectors into df_master...")
df_v2 = df_master.merge(all_cog[["creative_id"] + COG_COLS],
                         on="creative_id",
                         how="left")
print(f"         Shape after merge: {df_v2.shape}")


# ══════════════════════════════════════════════════════════════════════════════
# Step 6 — Sanity checks (audit output)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 70)
print("  SANITY CHECK REPORT")
print("═" * 70)

# Check 1: Row count
n_rows = len(df_v2)
row_ok = "✅ PASS" if n_rows == 6244 else f"❌ FAIL (expected 6244, got {n_rows})"
print(f"\n  [1] Total rows              : {n_rows:,}   {row_ok}")

# Check 2: Zero-inflation in variance columns
zero_pct = (df_v2[VAR_COLS] == 0).all(axis=1).mean() * 100
zero_ok  = "✅ PASS" if 60 < zero_pct < 72 else f"❌ FAIL (expected ≈66.7%)"
print(f"  [2] Rows with ALL var=0     : {zero_pct:.1f}%   {zero_ok}")
print(f"       → Image-only rows (var=0) : {int(df_v2[VAR_COLS].eq(0).all(axis=1).sum()):,}")
print(f"       → Video rows (var>0)      : {int((df_v2[VAR_COLS] > 0).any(axis=1).sum()):,}")

# Check 3: No NaN leakage in cognitive columns
nan_count = df_v2[COG_COLS].isna().sum().sum()
nan_ok    = "✅ PASS" if nan_count == 0 else f"⚠️  {nan_count} NaN values found"
print(f"  [3] NaN values in cog cols  : {nan_count}   {nan_ok}")

# Check 4: Column names are correct
expected_cols = set(COG_COLS)
present_cols  = set(df_v2.columns)
missing = expected_cols - present_cols
stale_present = [c for c in df_v2.columns if any(c.startswith(p) for p in STALE_PREFIXES)]
col_ok  = "✅ PASS" if not missing and not stale_present else f"❌ FAIL"
print(f"  [4] Corporate column naming : {col_ok}")
if missing:
    print(f"       Missing  : {sorted(missing)}")
if stale_present:
    print(f"       Stale still present: {stale_present}")

# Check 5: Per-column zero% summary for variance cols
print(f"\n  [5] Zero-inflation per cognitive_var column:")
print(f"       {'Column':<22} {'Zero %':>8}  {'Non-zero rows':>14}")
print(f"       {'─'*48}")
for col in VAR_COLS:
    z = (df_v2[col] == 0).mean() * 100
    nz = int((df_v2[col] != 0).sum())
    print(f"       {col:<22} {z:>7.1f}%  {nz:>14,}")

print("\n" + "═" * 70)


# ══════════════════════════════════════════════════════════════════════════════
# Step 7 — Export
# ══════════════════════════════════════════════════════════════════════════════
df_v2.to_csv(MASTER_OUT, index=False)
print(f"\n  ✅  Saved: {MASTER_OUT.name}")
print(f"       Shape  : {df_v2.shape}")
print(f"       Columns: {list(df_v2.columns)}")
print("\n  ℹ️   df_master.csv has NOT been overwritten.")
print("      Verify df_master_v2.csv, then rename manually to promote it.")
print("═" * 70 + "\n")
