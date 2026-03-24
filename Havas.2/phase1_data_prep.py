import pandas as pd
import json
import os
import numpy as np

# Configuration
BASE_DIR = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2"
INPUT_FILE = os.path.join(BASE_DIR, "Dados_Creatives_Enriched_Q1_2026.csv")
OUTPUT_FILE = os.path.join(BASE_DIR, "Dados_Creatives_Enriched_Q1_2026_Phase1.csv")
VIDEO_INDICES_DIR = os.path.join(BASE_DIR, "video_public_storage_url", "indices")

def get_last_5sec_metrics(row):
    """
    Extracts the last 5 seconds mean from the video JSON files.
    """
    metrics = {
        'engajamentoneural_last_5sec': np.nan, 
        'cognitivedemand_last_5sec': np.nan, 
        'focus_last_5sec': np.nan
    }
    
    video_url = row.get('video_public_storage_url')
    if pd.notna(video_url) and isinstance(video_url, str) and video_url:
        filename = os.path.basename(video_url)
        json_filename = filename + ".json"
        json_path = os.path.join(VIDEO_INDICES_DIR, json_filename)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                for key in ['engajamentoneural', 'cognitivedemand', 'focus']:
                    if key in data:
                        val = data[key]
                        if isinstance(val, list) and len(val) > 0:
                            # Last 5 Seconds (Assuming 0.5s interval -> last 10 samples)
                            # If video is shorter than 5s, take all
                            limit_5s = min(len(val), 10)
                            metrics[f'{key}_last_5sec'] = np.mean(val[-limit_5s:])
            except Exception as e:
                pass
                
    return pd.Series(metrics)

def assign_cost_bucket(cost):
    if pd.isna(cost):
        return 'Unknown'
    # Defining buckets based on quartiles check: 25% ~ 210, 50% ~ 1600, 75% ~ 8180
    if cost <= 210:
        return 'Low'
    elif cost <= 8180:
        return 'Medium'
    else:
        return 'High'

def get_trimester(date_str):
    if pd.isna(date_str) or not isinstance(date_str, str):
        return 'Unknown'
    
    try:
        # Assuming format is DD/MM/YYYY based on the sample
        parts = date_str.split('/')
        if len(parts) == 3:
            month = int(parts[1])
            year = parts[2]
            
            if 1 <= month <= 3:
                q = "Q1"
            elif 4 <= month <= 6:
                q = "Q2"
            elif 7 <= month <= 9:
                q = "Q3"
            else:
                q = "Q4"
                
            return f"{year}_{q}"
    except (ValueError, IndexError):
        pass
    
    return 'Unknown'

def main():
    print(f"Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)
    
    # 1. Add Last 5s Metrics for Videos
    print("Calculating 'Last 5s' metrics for videos...")
    last_5s_df = df.apply(get_last_5sec_metrics, axis=1)
    df = pd.concat([df, last_5s_df], axis=1)
    
    # 2. Add Cost Intervals
    print("Assigning cost intervals...")
    if 'parsed_cost' in df.columns:
        df['cost_interval'] = df['parsed_cost'].apply(assign_cost_bucket)
    else:
        print("Warning: 'parsed_cost' column not found.")
        
    # 3. Add Trimester
    print("Assigning trimester...")
    if 'from_date' in df.columns:
        df['trimester'] = df['from_date'].apply(get_trimester)
    else:
        print("Warning: 'from_date' column not found.")
        
    # 4. Save Main Dataset
    print(f"Saving augmented data to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    
    # 5. Split Dataset
    print("Splitting dataset into Images Only and Videos Only...")
    videos_df = df[df['video_public_storage_url'].notna() & (df['video_public_storage_url'] != "")]
    images_df = df[df['video_public_storage_url'].isna() | (df['video_public_storage_url'] == "")]
    
    base_name = OUTPUT_FILE.replace(".csv", "")
    img_file = f"{base_name}_Images_Only.csv"
    vid_file = f"{base_name}_Videos_Only.csv"
    
    images_df.to_csv(img_file, index=False)
    videos_df.to_csv(vid_file, index=False)
    
    print(f" -> Saved {len(images_df)} images to {img_file}")
    print(f" -> Saved {len(videos_df)} videos to {vid_file}")
    print("Phase 1 Complete!")

if __name__ == "__main__":
    main()
