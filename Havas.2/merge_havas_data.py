
import pandas as pd
import json
import os
import numpy as np

# Define file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assumes the script is in Havas.2 folder
CSV_PATH = os.path.join(BASE_DIR, "Dados Creatives + Performance Tim Q1 2026.csv")
VIDEO_INDICES_DIR = os.path.join(BASE_DIR, "video_public_storage_url", "indices")
IMAGE_INDICES_DIR = os.path.join(BASE_DIR, "public_storage_url-4", "indices")
OUTPUT_PATH = os.path.join(BASE_DIR, "Dados_Creatives_Enriched_Q1_2026.csv")

def parse_cost(cost_str):
    """Parses cost string like 'R$ 1.598.450,29' to float."""
    if pd.isna(cost_str) or not isinstance(cost_str, str):
        return 0.0
    
    clean_str = cost_str.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

def get_mean_metric(value):
    """Helper to safely extract mean from list or return scalar."""
    if isinstance(value, list):
        if not value:
            return np.nan
        return np.mean(value)
    elif isinstance(value, (int, float)):
        return float(value)
    return np.nan

def get_neuro_metrics_advanced(row):
    """
    Extracts neuro metrics from JSON files.
    Calculates Mean, 5-Sec Average, and Peak for Videos.
    Extracts scalar/mean for Images.
    """
    
    # Priority 1: Video JSON
    video_url = row.get('video_public_storage_url')
    if pd.notna(video_url) and isinstance(video_url, str) and video_url:
        filename = os.path.basename(video_url)
        # Check for .json extension logic matches previous script
        json_filename = filename + ".json"
        json_path = os.path.join(VIDEO_INDICES_DIR, json_filename)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                metrics = {}
                for key in ['engajamentoneural', 'cognitivedemand', 'focus']:
                    # Default NaNs
                    metrics[key] = np.nan
                    metrics[f'{key}_5sec'] = np.nan
                    metrics[f'{key}_peak'] = np.nan

                    if key in data:
                        val = data[key]
                        if isinstance(val, list) and len(val) > 0:
                            # Full Mean
                            metrics[key] = np.mean(val)
                            
                            # 5 Seconds (Assuming 0.5s interval -> first 10 samples)
                            limit_5s = min(len(val), 10)
                            metrics[f'{key}_5sec'] = np.mean(val[:limit_5s])
                            
                            # Peak (Max)
                            metrics[f'{key}_peak'] = np.max(val)
                        elif isinstance(val, (int, float)):
                            # Scalar fallback
                            metrics[key] = float(val)
                            metrics[f'{key}_5sec'] = float(val)
                            metrics[f'{key}_peak'] = float(val)
                            
                # Handle embeddings for video
                metrics['embedding_mean'] = np.nan
                if 'embeddings' in data:
                    embeddings_list = data['embeddings']
                    if isinstance(embeddings_list, list) and len(embeddings_list) > 0:
                        # flatten the list of lists
                        flat_embeddings = [item for sublist in embeddings_list for item in sublist]
                        metrics['embedding_mean'] = np.mean(flat_embeddings)
                
                return pd.Series(metrics)

            except Exception as e:
                # print(f"Error reading {json_path}: {e}")
                pass

    # Priority 2: Image JSON
    image_url = row.get('public_storage_url')
    if pd.notna(image_url) and isinstance(image_url, str) and image_url:
        filename = os.path.basename(image_url)
        json_filename = filename + ".json"
        
        # Check both potential image dirs if unsure, but strict mapping was established
        json_path = os.path.join(IMAGE_INDICES_DIR, json_filename)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                metrics = {}
                for key in ['engajamentoneural', 'cognitivedemand', 'focus']:
                    val = get_mean_metric(data.get(key))
                    metrics[key] = val
                    # For images, 5sec and Peak are just the static value
                    metrics[f'{key}_5sec'] = val
                    metrics[f'{key}_peak'] = val
                
                # Handle embeddings for images
                metrics['embedding_mean'] = np.nan
                if 'embeddings' in data:
                    embeddings_list = data['embeddings']
                    if isinstance(embeddings_list, list) and len(embeddings_list) > 0:
                        metrics['embedding_mean'] = np.mean(embeddings_list)

                return pd.Series(metrics)

            except Exception as e:
                pass
                
    return pd.Series({
        'engajamentoneural': np.nan, 'cognitivedemand': np.nan, 'focus': np.nan,
        'engajamentoneural_5sec': np.nan, 'cognitivedemand_5sec': np.nan, 'focus_5sec': np.nan,
        'engajamentoneural_peak': np.nan, 'cognitivedemand_peak': np.nan, 'focus_peak': np.nan,
        'embedding_mean': np.nan
    })

def main():
    print(f"Loading data from {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    
    # 1. Parse Cost
    print("Parsing 'cost' column...")
    df['parsed_cost'] = df['cost'].apply(parse_cost)
    
    # 2. Calculate Performance Metrics
    print("Calculating CTR, CPC, CPM...")
    df['CTR'] = (df['clicks'] / df['impressions']) * 100
    df['CPC'] = df['parsed_cost'] / df['clicks']
    df['CPM'] = (df['parsed_cost'] / df['impressions']) * 1000
    
    # 3. Extract Neuro Metrics (Advanced)
    print("Extracting neuro metrics (Advanced: Mean, 5sec, Peak)...")
    
    # Create empty columns first to ensure order? No, apply returns Series.
    neuro_cols = ['engajamentoneural', 'cognitivedemand', 'focus',
                  'engajamentoneural_5sec', 'cognitivedemand_5sec', 'focus_5sec',
                  'engajamentoneural_peak', 'cognitivedemand_peak', 'focus_peak',
                  'embedding_mean']
    
    neuro_df = df.apply(get_neuro_metrics_advanced, axis=1)
    
    # Concat guarantees alignment on index
    df = pd.concat([df, neuro_df], axis=1)
    
    # 4. Calculate Fluency Index and Peak Score
    print("Calculating Fluency Index & Derived Metrics...")
    df['fluency_index'] = df['engajamentoneural'] / df['focus']
    # If Peak Score is defined as engagement peak
    df['peak_score'] = df['engajamentoneural_peak']

    # 5. Save Output
    print(f"Saving enriched data to {OUTPUT_PATH}...")
    df.to_csv(OUTPUT_PATH, index=False)
    print("Done!")

if __name__ == "__main__":
    main()
