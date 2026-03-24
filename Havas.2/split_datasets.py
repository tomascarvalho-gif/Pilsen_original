import pandas as pd

def split_datasets():
    print("Loading original dataset...")
    # Using the enriched one which is likely the one they want for analysis, or the original one.
    # Let's split both just to be safe, or just provide a script that they can run on whatever they need.
    original_file = "Dados Creatives + Performance Tim Q1 2026.csv"
    enriched_file = "Dados_Creatives_Enriched_Q1_2026.csv"
    
    for file in [original_file, enriched_file]:
        try:
            df = pd.read_csv(file)
            print(f"\nProcessing {file}...")
            
            # Videos have a non-empty 'video_public_storage_url'
            videos_df = df[df['video_public_storage_url'].notna() & (df['video_public_storage_url'] != "")]
            # Images have an empty 'video_public_storage_url'
            images_df = df[df['video_public_storage_url'].isna() | (df['video_public_storage_url'] == "")]
            
            # Create filenames based on the input name
            base_name = file.replace(".csv", "")
            img_file = f"{base_name}_Images_Only.csv"
            vid_file = f"{base_name}_Videos_Only.csv"
            
            # Save
            images_df.to_csv(img_file, index=False)
            videos_df.to_csv(vid_file, index=False)
            
            print(f" -> Saved {len(images_df)} images to {img_file}")
            print(f" -> Saved {len(videos_df)} videos to {vid_file}")
        except FileNotFoundError:
            print(f"File {file} not found. Skipping.")

if __name__ == '__main__':
    split_datasets()
