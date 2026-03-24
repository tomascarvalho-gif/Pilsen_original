"""
eda_step8b_clean_clusters.py
============================
Clean K-Means re-run after removing the cognitivedemand outlier (7.1M artifact).
  · Hard-drop rows where cognitivedemand > 1000
  · StandardScaler on neural features
  · K-Means K=2 (the 3rd cluster was a single outlier)
  · Cross-tabulation: Cluster × Funnel → median CTR, median CPM,
    mean engajamentoneural, mean pca_var_2
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# ── Paths & constants ──────────────────────────────────────────────────────────
BASE        = Path(__file__).parent
DATA        = BASE / "Havas.2" / "df_master.csv"
COG_MEAN    = [f"cognitive_mean_{i}" for i in range(10)]
COG_VAR     = [f"cognitive_var_{i}"  for i in range(10)]
NEURO       = ["engajamentoneural", "cognitivedemand", "focus"]
RANDOM_SEED = 42
OUTLIER_THR = 1000


def run() -> None:
    print("═" * 72)
    print("  EDA Step 8b — Clean K-Means Clustering (K=2, outlier removed)")
    print("═" * 72)

    # ── 1. Load & isolate video rows ───────────────────────────────────────────
    df = pd.read_csv(DATA)
    df = df[df["dominant_funnel_stage"] != "Unknown"].copy()
    video_mask     = (df[COG_VAR] > 0).any(axis=1)
    df["is_video"] = video_mask.astype(int)
    df_vid = df[df["is_video"] == 1].copy()
    print(f"\n  Video rows loaded : {len(df_vid):,}")

    # ── 2. Hard-drop cognitivedemand outlier ───────────────────────────────────
    before = len(df_vid)
    df_vid = df_vid[df_vid["cognitivedemand"] <= OUTLIER_THR].copy()
    dropped = before - len(df_vid)
    print(f"  Dropped rows (cognitivedemand > {OUTLIER_THR:,}) : {dropped}")
    print(f"  Video rows after cleaning : {len(df_vid):,}")

    # ── 3. Regenerate PCA components ───────────────────────────────────────────
    # Mean block (fit on all rows for consistency, but only apply to video)
    df_all = df[df["cognitivedemand"] <= OUTLIER_THR].copy()
    X_m_sc = StandardScaler().fit_transform(df_all[COG_MEAN])
    pca_m  = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_m    = pca_m.fit_transform(X_m_sc)
    for i in range(X_m.shape[1]):
        df_all[f"pca_mean_{i+1}"] = X_m[:, i]

    # Var block (video rows only)
    vm = (df_all[COG_VAR] > 0).any(axis=1)
    X_v_sc = StandardScaler().fit_transform(df_all.loc[vm, COG_VAR])
    pca_v  = PCA(n_components=0.90, random_state=RANDOM_SEED)
    X_v    = pca_v.fit_transform(X_v_sc)
    for i in range(X_v.shape[1]):
        df_all[f"pca_var_{i+1}"] = 0.0
        df_all.loc[vm, f"pca_var_{i+1}"] = X_v[:, i]

    n_mean = X_m.shape[1]
    n_var  = X_v.shape[1]

    # Slice back to video only
    df_vid = df_all[df_all["is_video"] == 1].copy()

    pca_mean_cols = [f"pca_mean_{i+1}" for i in range(n_mean)]
    pca_var_cols  = [f"pca_var_{i+1}"  for i in range(n_var)]
    cluster_feats = pca_mean_cols + pca_var_cols + NEURO

    # ── 4. StandardScaler + K-Means (K=2) ─────────────────────────────────────
    X = df_vid[cluster_feats].dropna()
    idx = X.index

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=2, random_state=RANDOM_SEED, n_init=20)
    labels = kmeans.fit_predict(X_scaled)
    df_vid.loc[idx, "cluster"] = labels.astype(int)

    print(f"\n  K-Means fitted (K=2) on {len(idx):,} video rows")
    print(f"  Features: {cluster_feats}")

    # ── 5. Cross-tabulation ────────────────────────────────────────────────────
    W = 86

    # 5a. Cluster × Funnel Stage
    xtab = (df_vid.loc[idx]
            .groupby(["cluster", "dominant_funnel_stage"])
            .agg(
                n               = ("CTR", "size"),
                median_CTR      = ("CTR", "median"),
                median_CPM      = ("CPM", "median"),
                mean_engage     = ("engajamentoneural", "mean"),
                mean_pca_var_2  = ("pca_var_2", "mean"),
            )
            .reset_index())

    # 5b. Cluster totals
    totals = (df_vid.loc[idx]
              .groupby("cluster")
              .agg(
                  total_n         = ("CTR", "size"),
                  median_CTR      = ("CTR", "median"),
                  median_CPM      = ("CPM", "median"),
                  mean_engage     = ("engajamentoneural", "mean"),
                  mean_pca_var_2  = ("pca_var_2", "mean"),
              )
              .reset_index())

    print("\n" + "═" * W)
    print("  CLEAN K-MEANS CROSS-TABULATION (K=2, cognitivedemand outlier removed)")
    print("═" * W)

    print(f"\n  {'Cluster':>8}  {'Funnel':<16} {'N':>5}  "
          f"{'Med CTR':>10}  {'Med CPM':>10}  "
          f"{'Avg Engage':>11}  {'Avg pca_var_2':>14}")
    print("  " + "─" * (W - 2))

    for cluster_id in sorted(xtab["cluster"].unique()):
        rows = xtab[xtab["cluster"] == cluster_id]
        tot  = totals[totals["cluster"] == cluster_id].iloc[0]

        for _, r in rows.iterrows():
            print(f"  {r['cluster']:>8}  {r['dominant_funnel_stage']:<16} "
                  f"{r['n']:>5}  "
                  f"{r['median_CTR']:>10.5f}  {r['median_CPM']:>10.2f}  "
                  f"{r['mean_engage']:>11.2f}  {r['mean_pca_var_2']:>14.5f}")

        print(f"  {'':>8}  {'── TOTAL':<16} "
              f"{tot['total_n']:>5}  "
              f"{tot['median_CTR']:>10.5f}  {tot['median_CPM']:>10.2f}  "
              f"{tot['mean_engage']:>11.2f}  {tot['mean_pca_var_2']:>14.5f}")
        print()

    # ── 5c. Delta summary ─────────────────────────────────────────────────────
    if len(totals) == 2:
        c0 = totals[totals["cluster"] == 0].iloc[0]
        c1 = totals[totals["cluster"] == 1].iloc[0]

        # Label the higher-CTR cluster as "High" and the other as "Low"
        if c1["median_CTR"] > c0["median_CTR"]:
            hi, lo = c1, c0
            hi_id, lo_id = 1, 0
        else:
            hi, lo = c0, c1
            hi_id, lo_id = 0, 1

        ctr_ratio  = hi["median_CTR"] / lo["median_CTR"] if lo["median_CTR"] > 0 else float("inf")
        cpm_delta  = hi["median_CPM"] - lo["median_CPM"]
        eng_delta  = hi["mean_engage"] - lo["mean_engage"]
        var2_delta = hi["mean_pca_var_2"] - lo["mean_pca_var_2"]

        print("  " + "─" * (W - 2))
        print(f"  Cluster {hi_id} = HIGH CTR archetype  |  "
              f"Cluster {lo_id} = LOW CTR archetype")
        print(f"  " + "─" * (W - 2))
        print(f"    CTR lift             : {ctr_ratio:.2f}× "
              f"({hi['median_CTR']:.5f} vs {lo['median_CTR']:.5f})")
        print(f"    CPM premium          : {cpm_delta:+.2f} R$ "
              f"({hi['median_CPM']:.2f} vs {lo['median_CPM']:.2f})")
        print(f"    Engagement delta     : {eng_delta:+.2f} "
              f"({hi['mean_engage']:.2f} vs {lo['mean_engage']:.2f})")
        print(f"    pca_var_2 delta      : {var2_delta:+.5f} "
              f"({hi['mean_pca_var_2']:.5f} vs {lo['mean_pca_var_2']:.5f})")

    print("\n" + "═" * W + "\n")


if __name__ == "__main__":
    run()
