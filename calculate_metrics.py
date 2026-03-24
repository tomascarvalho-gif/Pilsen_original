
import pandas as pd
import numpy as np
import os
import glob

# Paths
excel_path = 'Tunad/Videos_db_Tunad/Audios Tunad ATUALIZADO.xlsx'
neural_dir = 'Tunad/Videos_db_Tunad/videos'
focus_dir = 'Tunad/Videos_db_Tunad/videos/attentiveai'

output_path = 'Tunad/Videos_db_Tunad/Audios_Tunad_With_Fluency.csv'

def calculate_indices():
    print(f"Loading Excel from {excel_path}...")
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        print(f"Error: Excel file not found at {excel_path}")
        return

    print(f"Loaded {len(df)} rows.")

    # Initialize new columns
    df['Fluency_Index'] = np.nan
    df['Peak_Score'] = np.nan
    
    success_count = 0
    missing_neural = 0
    missing_focus = 0

    for index, row in df.iterrows():
        video_url = str(row['VideoURL'])
        
        # Extract Hash from URL
        # Format: https://s3.amazonaws.com/tunad-base/mp4/<HASH>.mp4
        if 'mp4/' in video_url:
            filename = video_url.split('mp4/')[-1]
            if filename.endswith('.mp4'):
                file_hash = filename[:-4] # Remove .mp4
            else:
                # Handle cases like .../HASH.mp4?query=... if any (unlikely based on prev inspection)
                file_hash = filename
        else:
            # Fallback or skip
            continue
            
        neural_file = os.path.join(neural_dir, f"{file_hash}.mp4.npy")
        focus_file = os.path.join(focus_dir, f"{file_hash}.mp4.foco.npy")
        
        if not os.path.exists(neural_file):
            missing_neural += 1
            continue
            
        if not os.path.exists(focus_file):
            missing_focus += 1
            # Can still calc Peak Score if we wanted, but let's stick to full data for now
            # Actually, let's calculate Peak Score even if Focus is missing? 
            # No, let's be strict for Fluency.
            pass

        try:
            # Load Data
            neural_data = np.load(neural_file, allow_pickle=True)
            
            # Check if focus exists to calc fluency
            if os.path.exists(focus_file):
                focus_data = np.load(focus_file, allow_pickle=True)
                
                # Ensure shapes match or trim to min length
                min_len = min(len(neural_data), len(focus_data))
                if min_len > 0:
                    n_trim = neural_data[:min_len]
                    f_trim = focus_data[:min_len]
                    
                    # Avoid division by zero
                    f_trim = np.where(f_trim == 0, 0.001, f_trim)
                    
                    # Fluency = Neural / Focus
                    fluency_series = n_trim / f_trim
                    fluency_index = np.mean(fluency_series)
                    
                    df.at[index, 'Fluency_Index'] = fluency_index
                    df.at[index, 'Average_Focus'] = np.mean(f_trim)
                else:
                    print(f"Empty data for {file_hash}")

            # Peak Score (Neural Max) and Average Neural
            if len(neural_data) > 0:
                peak_score = np.max(neural_data)
                avg_neural = np.mean(neural_data)
                df.at[index, 'Peak_Score'] = peak_score
                df.at[index, 'Average_Neural'] = avg_neural
                success_count += 1

        except Exception as e:
            print(f"Error processing {file_hash}: {e}")

    print("-" * 30)
    print(f"Processing Complete.")
    print(f"Calculated for {success_count} videos.")
    print(f"Missing Neural Files: {missing_neural}")
    print(f"Missing Focus Files: {missing_focus}")
    
    print(f"Saving to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done.")

if __name__ == "__main__":
    calculate_indices()
