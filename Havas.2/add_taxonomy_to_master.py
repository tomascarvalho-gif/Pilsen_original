"""
Add Taxonomy Classification to df_master
=========================================
Merges the campaign objective classification (Awareness / Consideration /
Conversion) into df_master.csv from two sources:

  Images → havas_taxonomy_test.csv
            Column added: `category`  (single label)

  Videos → havas_video_taxonomy_test.csv
            Columns added: `Awareness_Percentage`
                           `Consideration_Percentage`
                           `Conversion_Percentage`

Join key: the filename is extracted from the URL columns in df_master
  Images: public_storage_url       → last segment after final "/"
  Videos: video_public_storage_url → last segment after final "/"

Output: overwrites df_master.csv in-place (a backup is saved first).
"""

from pathlib import Path
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE       = Path(__file__).parent
MASTER     = BASE / "df_master.csv"
IMG_TAX    = BASE / "havas_taxonomy_test.csv"
VID_TAX    = BASE / "havas_video_taxonomy_test.csv"
BACKUP     = BASE / "df_master_backup.csv"

# ── Load ───────────────────────────────────────────────────────────────────────

print(f"[INFO] Loading df_master  →  {MASTER.name}")
df = pd.read_csv(MASTER)
print(f"       Shape: {df.shape}")

# ── Drop existing taxonomy columns (makes script safe to re-run) ───────────────
STALE_COLS = [
    "taxonomy_category",
    "Awareness_Percentage", "Consideration_Percentage", "Conversion_Percentage",
    "dominant_funnel_stage",
]
dropped = [c for c in STALE_COLS if c in df.columns]
if dropped:
    df = df.drop(columns=dropped)
    print(f"[INFO] Dropped existing columns to avoid merge conflicts: {dropped}")

# ── Image taxonomy ─────────────────────────────────────────────────────────────

print(f"\n[INFO] Loading image taxonomy  →  {IMG_TAX.name}")
img = pd.read_csv(IMG_TAX, usecols=["filename", "category"])
print(f"       Shape: {img.shape}  |  Categories: {img['category'].unique().tolist()}")

# Extract filename from the image URL (last path segment)
df["_img_filename"] = (
    df["public_storage_url"]
    .fillna("")
    .str.split("/")
    .str[-1]
)

df = df.merge(
    img.rename(columns={"category": "taxonomy_category"}),
    left_on="_img_filename",
    right_on="filename",
    how="left"
).drop(columns=["filename", "_img_filename"])

matched_img = df["taxonomy_category"].notna().sum()
print(f"       Matched {matched_img} / {len(df)} rows  ({matched_img/len(df)*100:.1f}%)")

# ── Video taxonomy ─────────────────────────────────────────────────────────────

print(f"\n[INFO] Loading video taxonomy  →  {VID_TAX.name}")

# The video CSV has no header row — assign column names manually
vid = pd.read_csv(
    VID_TAX,
    header=None,
    names=["filename", "Awareness_Percentage",
           "Consideration_Percentage", "Conversion_Percentage", "reasoning"]
)
# Keep only the columns we need
vid = vid[["filename", "Awareness_Percentage",
           "Consideration_Percentage", "Conversion_Percentage"]]

print(f"       Shape: {vid.shape}")

# Extract filename from the video URL (last path segment)
df["_vid_filename"] = (
    df["video_public_storage_url"]
    .fillna("")
    .str.split("/")
    .str[-1]
)

df = df.merge(
    vid,
    left_on="_vid_filename",
    right_on="filename",
    how="left"
).drop(columns=["filename", "_vid_filename"])

matched_vid = df["Awareness_Percentage"].notna().sum()
print(f"       Matched {matched_vid} / {len(df)} rows  ({matched_vid/len(df)*100:.1f}%)")

# ── Save ───────────────────────────────────────────────────────────────────────

# Backup first, then overwrite
df_original = pd.read_csv(MASTER)
df_original.to_csv(BACKUP, index=False)
print(f"\n[INFO] Backup saved  →  {BACKUP.name}")

df.to_csv(MASTER, index=False)
print(f"[INFO] df_master updated  →  {MASTER.name}")
print(f"       Final shape: {df.shape}")

# ── Summary ────────────────────────────────────────────────────────────────────

print("\n" + "═" * 55)
print("  TAXONOMY MERGE SUMMARY")
print("═" * 55)
print(f"  Total rows              : {len(df)}")
print(f"  Rows with category      : {df['taxonomy_category'].notna().sum()}")
print(f"  Rows with video %       : {df['Awareness_Percentage'].notna().sum()}")
print(f"\n  category value counts:")
print(df["taxonomy_category"].value_counts(dropna=False).to_string(header=False))
print("═" * 55)
