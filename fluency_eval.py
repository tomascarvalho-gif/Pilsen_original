
import pandas as pd
import numpy as np
import json
import os
import glob
from scipy.stats import pearsonr, spearmanr
import matplotlib.pyplot as plt
import seaborn as sns

# Configs
GAIA_DIR = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/GAIA/ds_meta_criativos"
TUNAD_DIR = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Tunad/Videos_30_e_1200"
OUTPUT_DIR = "/Users/tomasdefreitascarvalho/.gemini/antigravity/brain/40f72a65-5efc-416f-89ef-18ca4422368b"

def analyze_gaia():
    print("\n--- Gaia (Image) Analysis ---")
    
    # 1. Load AI Results
    json_path = os.path.join(GAIA_DIR, "resultados_ia.json")
    if not os.path.exists(json_path):
        print("Gaia JSON not found.")
        return

    with open(json_path, 'r') as f:
        ai_data = json.load(f)
    
    # Convert to DataFrame
    ai_records = []
    for img, metrics in ai_data.items():
        if "erro" not in metrics:
            ai_records.append({
                "Imagem": img,
                "Engagement": metrics.get("brainai_index"),
                "Focus": metrics.get("focus_index"),
                "CognitiveDemand": metrics.get("cognitive_demand_index")
            })
    
    df_ai = pd.DataFrame(ai_records)
    
    # 2. Load Performance Data (Feathers)
    feather_dir = os.path.join(GAIA_DIR, "feathers_compactos")
    feather_files = glob.glob(os.path.join(feather_dir, "*.feather"))
    
    df_perf_list = []
    for f in feather_files:
        try:
            df = pd.read_feather(f)
            # Normalize image column name if needed
            if 'imagem' in df.columns:
                df['Imagem'] = df['imagem'].apply(lambda x: x.split('/')[-1] if isinstance(x, str) else x)
                df_perf_list.append(df[['Imagem', 'clicks', 'impressions', 'cost']])
            elif 'imagem_anuncio' in df.columns:
                df['Imagem'] = df['imagem_anuncio'].apply(lambda x: x.split('/')[-1] if isinstance(x, str) else x)
                df_perf_list.append(df[['Imagem', 'clicks', 'impressions', 'cost']])
        except Exception as e:
            print(f"Error reading feather {f}: {e}")

    if not df_perf_list:
        print("No performance data found.")
        return

    df_perf = pd.concat(df_perf_list)
    # Aggregate duplicate images
    df_perf = df_perf.groupby('Imagem').sum().reset_index()
    
    # 3. Merge
    df_merged = pd.merge(df_ai, df_perf, on='Imagem', how='inner')
    
    # 4. Calculate Fluency and CTR
    df_merged['Fluency'] = df_merged['Engagement'] / df_merged['Focus']
    df_merged['CTR'] = df_merged['clicks'] / df_merged['impressions']
    
    # Filter valid data
    df_final = df_merged.dropna(subset=['Fluency', 'CTR'])
    df_final = df_final[df_final['impressions'] > 1000] # Min impressions filter
    
    print(f"Gaia: Analyzed {len(df_final)} images.")
    
    # 5. Correlations
    metrics = ['Engagement', 'Focus', 'CognitiveDemand', 'Fluency']
    targets = ['CTR']
    
    results = {}
    for m in metrics:
        if m in df_final.columns:
            corr, p = pearsonr(df_final[m], df_final['CTR'])
            results[m] = corr
            print(f"{m} vs CTR: r={corr:.4f} (p={p:.4f})")
    
    # Save plot for Fluency vs CTR
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df_final, x='Fluency', y='CTR', alpha=0.5)
    plt.title(f'Gaia: Fluency Index vs CTR (r={results.get("Fluency", 0):.2f})')
    plt.savefig(os.path.join(OUTPUT_DIR, "gaia_fluency_ctr.png"))
    plt.close()

def analyze_tunad():
    print("\n--- Tunad (Video) Analysis ---")
    
    # 1. Load Excel Data
    excel_path = os.path.join(TUNAD_DIR, "dados.xlsx")
    if not os.path.exists(excel_path):
        print("Tunad Excel not found.")
        return
        
    df_data = pd.read_excel(excel_path)
    
    # Create Hash Check column
    # Link format: https://s3.amazonaws.com/tunad-base/mp4/HASH.mp4
    def extract_hash(link):
        if isinstance(link, str) and 'mp4' in link:
            return link.split('/')[-1]
        return None
        
    df_data['video_filename'] = df_data['Link'].apply(extract_hash)
    df_data = df_data.dropna(subset=['video_filename'])
    
    # 2. Load Neural Metrics from .npy
    npy_dir = os.path.join(TUNAD_DIR, "videos1200")
    
    neural_data = []
    
    # Iterate over dataframe rows to find matching npy files
    for idx, row in df_data.iterrows():
        vid_name = row['video_filename']
        npy_path = os.path.join(npy_dir, vid_name + ".npy")
        
        if os.path.exists(npy_path):
            try:
                # Load only if exists. Assume 1D array of metric X.
                data = np.load(npy_path, allow_pickle=True)
                if data.ndim == 1:
                    mean_val = np.mean(data)
                    neural_data.append({
                        'video_filename': vid_name,
                        'Neural_Metric_Mean': mean_val
                    })
            except Exception as e:
                pass
                
    df_neural = pd.DataFrame(neural_data)
    
    if df_neural.empty:
        print("No neural data matched.")
        return

    # 3. Merge
    df_merged = pd.merge(df_data, df_neural, on='video_filename', how='inner')
    
    # 4. Correlations
    # We correlate the available 'Neural_Metric_Mean' with 'Uplift Médio' and 'Call To Action'
    targets = ['Uplift Médio', 'Call To Action']
    metric = 'Neural_Metric_Mean'
    
    print(f"Tunad: Analyzed {len(df_merged)} videos.")
    
    for t in targets:
        # Drop nan
        tmp = df_merged.dropna(subset=[metric, t])
        if len(tmp) > 10:
            corr, p = pearsonr(tmp[metric], tmp[t])
            print(f"{metric} vs {t}: r={corr:.4f} (p={p:.4f})")
            
            # Plot
            plt.figure(figsize=(8, 6))
            sns.scatterplot(data=tmp, x=metric, y=t, alpha=0.5)
            plt.title(f'Tunad: {metric} vs {t} (r={corr:.2f})')
            plt.savefig(os.path.join(OUTPUT_DIR, f"tunad_{metric}_vs_{t.replace(' ', '_')}.png"))
            plt.close()

if __name__ == "__main__":
    analyze_gaia()
    analyze_tunad()
