"""
Step 2 — Unify Funnel Stage into a Single Master Column
=========================================================
Reads the already-merged df_master.csv (which has taxonomy_category and
video percentage columns from add_taxonomy_to_master.py) and adds:

  dominant_funnel_stage:
    → image rows  : directly from taxonomy_category
    → video rows  : argmax across Awareness / Consideration / Conversion %
    → neither     : 'Unknown'

Output: overwrites df_master.csv in-place (backup saved first).
"""

from pathlib import Path
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE    = Path(__file__).parent
MASTER  = BASE / "df_master.csv"
BACKUP  = BASE / "df_master_prefunnel_backup.csv"

VIDEO_COLS = ["Awareness_Percentage", "Consideration_Percentage", "Conversion_Percentage"]

# ── Load ───────────────────────────────────────────────────────────────────────

print(f"[INFO] Loading df_master  →  {MASTER.name}")
df = pd.read_csv(MASTER)
print(f"       Shape: {df.shape}")

# ── Step 1 — Video argmax ──────────────────────────────────────────────────────
# idxmax() returns the column name with the highest value per row.
# We then strip '_Percentage' to get clean label text.

has_video = df[VIDEO_COLS].notna().any(axis=1)

video_argmax = (
    df.loc[has_video, VIDEO_COLS]
    .idxmax(axis=1)                          # e.g. 'Conversion_Percentage'
    .str.replace("_Percentage", "", regex=False)  # → 'Conversion'
)

# ── Step 2 — Coalesce into dominant_funnel_stage ───────────────────────────────

df["dominant_funnel_stage"] = (
    df["taxonomy_category"]                  # images: direct label
    .where(df["taxonomy_category"].notna(),  # if NaN → try video argmax
        other=video_argmax.reindex(df.index) # align index before filling
    )
    .fillna("Unknown")                       # still NaN → Unknown
)

# ── Summary ────────────────────────────────────────────────────────────────────

counts = df["dominant_funnel_stage"].value_counts(dropna=False)

print("\n" + "═" * 50)
print("  DOMINANT FUNNEL STAGE — Value Counts")
print("═" * 50)
print(counts.to_string())
print("─" * 50)
print(f"  Total rows  : {len(df)}")
print(f"  Unknown     : {(df['dominant_funnel_stage'] == 'Unknown').sum()}")
print(f"  Classified  : {(df['dominant_funnel_stage'] != 'Unknown').sum()}")
print("═" * 50)

# ── Save ───────────────────────────────────────────────────────────────────────

df.to_csv(BACKUP, index=False)
print(f"\n[INFO] Backup saved  →  {BACKUP.name}")

df.to_csv(MASTER, index=False)
print(f"[INFO] df_master updated  →  {MASTER.name}")
print(f"       Final shape: {df.shape}")
print(f"       New column : dominant_funnel_stage")
