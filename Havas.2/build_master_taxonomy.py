"""
build_master_taxonomy.py
========================
Definitive, safe taxonomy merge for df_master.csv.

Fixes all issues from previous runs:
  - Removes stale / duplicate taxonomy columns before merging
  - Deduplicates taxonomy files on filename before joining (prevents row fan-out)
  - Validates row count is preserved at every step
  - Builds video_label (idxmax) and dominant_funnel_stage (coalesce)

Sources
-------
  Images : havas_taxonomy_test.csv                  (4174 rows, root folder, has header)
  Videos : Havas.2/havas_video_taxonomy_test.csv    (2072 rows, NO header)

Join keys (extracted from URL columns in df_master)
  Images : public_storage_url       → last segment after final "/"
  Videos : video_public_storage_url → last segment after final "/"

Output
------
  Overwrites Havas.2/df_master.csv
  Saves clean backup to Havas.2/df_master_clean_backup.csv
"""

from pathlib import Path
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE     = Path(__file__).parent
MASTER   = BASE / "df_master.csv"
BACKUP   = BASE / "df_master_backup.csv"          # existing backup (40 cols)
CLEAN_BK = BASE / "df_master_clean_backup.csv"    # new clean backup we create
IMG_TAX  = BASE.parent / "havas_taxonomy_test.csv"  # ROOT folder — 4174 rows (full)
VID_TAX  = BASE / "havas_video_taxonomy_test.csv"   # Havas.2 — 2072 rows (NO header)

VIDEO_COLS  = ["Awareness_Percentage", "Consideration_Percentage", "Conversion_Percentage"]
STALE_COLS  = ["taxonomy_category", "dominant_funnel_stage", "video_label"] + VIDEO_COLS

# ── Helper ─────────────────────────────────────────────────────────────────────

def assert_shape(df: pd.DataFrame, expected_rows: int, label: str) -> None:
    """Raise if row count drifted from expected."""
    if len(df) != expected_rows:
        raise RuntimeError(
            f"[FAIL] {label}: expected {expected_rows} rows, got {len(df)}. "
            "Check for duplicate join keys."
        )
    print(f"  ✓ {label}: {len(df)} rows  (shape {df.shape})")

# ── 1. Load & restore to clean baseline ───────────────────────────────────────

# Prefer backup (cleaner starting point), fall back to current master
src = BACKUP if BACKUP.exists() else MASTER
print(f"[INFO] Loading base  →  {src.name}")
df = pd.read_csv(src)
print(f"       Shape on load : {df.shape}")

# Drop any stale taxonomy columns so we start from a clean slate
present_stale = [c for c in STALE_COLS if c in df.columns]
if present_stale:
    df = df.drop(columns=present_stale)
    print(f"[INFO] Dropped stale columns: {present_stale}")

BASELINE_ROWS = len(df)
print(f"[INFO] Clean baseline: {df.shape}  ({BASELINE_ROWS} rows)\n")

# ── 2. Build join keys from URL columns ───────────────────────────────────────

df["_img_key"] = df["public_storage_url"].fillna("").str.split("/").str[-1]
df["_vid_key"] = df["video_public_storage_url"].fillna("").str.split("/").str[-1]

# ── 3. Load & deduplicate image taxonomy ──────────────────────────────────────

print(f"[INFO] Loading image taxonomy  →  {IMG_TAX.name}")
img = (
    pd.read_csv(IMG_TAX, usecols=["filename", "category"])
    .drop_duplicates(subset="filename", keep="first")   # safety dedup
    .rename(columns={"category": "taxonomy_category"})
)
# Normalize caps variants: 'CONVERSION' → 'Conversion', 'AWARENESS' → 'Awareness'
img["taxonomy_category"] = img["taxonomy_category"].str.capitalize()
print(f"       {len(img)} unique filenames  |  "
      f"categories: {img['taxonomy_category'].value_counts().to_dict()}")

# ── 4. Merge image taxonomy ───────────────────────────────────────────────────

df = df.merge(img, left_on="_img_key", right_on="filename", how="left")
df = df.drop(columns=["filename"])            # drop the right-side key column
assert_shape(df, BASELINE_ROWS, "after image merge")

img_matched = df["taxonomy_category"].notna().sum()
print(f"       Matched: {img_matched} rows  ({img_matched/BASELINE_ROWS*100:.1f}%)\n")

# ── 5. Load & deduplicate video taxonomy ──────────────────────────────────────

print(f"[INFO] Loading video taxonomy  →  {VID_TAX.name}")
vid = pd.read_csv(
    VID_TAX,
    header=None,
    names=["filename"] + VIDEO_COLS + ["reasoning"]
)
dupes = vid["filename"].duplicated().sum()
if dupes:
    print(f"  [WARN] {dupes} duplicate filename(s) in video taxonomy — keeping first")
    vid = vid.drop_duplicates(subset="filename", keep="first")

vid = vid[["filename"] + VIDEO_COLS]   # drop reasoning
print(f"       {len(vid)} unique video filenames")

# ── 6. Merge video taxonomy ───────────────────────────────────────────────────

df = df.merge(vid, left_on="_vid_key", right_on="filename", how="left")
df = df.drop(columns=["filename"])
assert_shape(df, BASELINE_ROWS, "after video merge")

vid_matched = df[VIDEO_COLS[0]].notna().sum()
print(f"       Matched: {vid_matched} rows  ({vid_matched/BASELINE_ROWS*100:.1f}%)\n")

# ── 7. Drop temp key columns ──────────────────────────────────────────────────

df = df.drop(columns=["_img_key", "_vid_key"])

# ── 8. video_label — idxmax across video % columns ───────────────────────────

has_video = df[VIDEO_COLS].notna().any(axis=1)
df["video_label"] = pd.Series(dtype="object")   # explicit object dtype avoids FutureWarning
df.loc[has_video, "video_label"] = (
    df.loc[has_video, VIDEO_COLS]
    .idxmax(axis=1)
    .str.replace("_Percentage", "", regex=False)
)

# ── 9. dominant_funnel_stage — coalesce ───────────────────────────────────────
# Priority: image label  >  video argmax  >  "Unknown"

df["dominant_funnel_stage"] = (
    df["taxonomy_category"]
    .where(df["taxonomy_category"].notna(), other=df["video_label"])
    .fillna("Unknown")
)

# ── 10. Validation report ─────────────────────────────────────────────────────

total        = len(df)
n_image      = df["taxonomy_category"].notna().sum()
n_video      = df["video_label"].notna().sum()
n_both       = (df["taxonomy_category"].notna() & df["video_label"].notna()).sum()
n_classified = (df["dominant_funnel_stage"] != "Unknown").sum()
n_unknown    = (df["dominant_funnel_stage"] == "Unknown").sum()

print("═" * 58)
print("  FINAL VALIDATION REPORT")
print("═" * 58)
print(f"  Total rows                      : {total:>6,}")
print(f"  Rows with image label           : {n_image:>6,}  ({n_image/total*100:.1f}%)")
print(f"  Rows with video label (argmax)  : {n_video:>6,}  ({n_video/total*100:.1f}%)")
print(f"  Rows with BOTH (image priority) : {n_both:>6,}")
print(f"  ─────────────────────────────────────────────────")
print(f"  Classified (dominant_funnel_stage != Unknown): {n_classified:>5,}  ({n_classified/total*100:.1f}%)")
print(f"  Still NaN / Unknown             : {n_unknown:>6,}  ({n_unknown/total*100:.1f}%)")
print(f"  ─────────────────────────────────────────────────")
print(f"  dominant_funnel_stage breakdown:")
for stage, count in df["dominant_funnel_stage"].value_counts(dropna=False).items():
    print(f"    {str(stage):<20} {count:>5,}  ({count/total*100:.1f}%)")
print("═" * 58)

# ── 11. Save ──────────────────────────────────────────────────────────────────

df.to_csv(CLEAN_BK, index=False)
print(f"\n[INFO] Clean backup saved  →  {CLEAN_BK.name}")

df.to_csv(MASTER, index=False)
print(f"[INFO] df_master updated   →  {MASTER.name}")
print(f"       Final shape         :  {df.shape}")
print(f"       New columns         :  taxonomy_category, video_label,")
print(f"                              {', '.join(VIDEO_COLS)},")
print(f"                              dominant_funnel_stage")
