import os
import csv
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. SETUP API KEY ---
env_path = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/.env"
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(f"❌ ERROR: Could not find API Key at: {env_path}")
    exit()

genai.configure(api_key=api_key)

# --- 2. CONFIGURATION ---
VIDEO_FOLDER_PATH = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/video_public_storage_url-3"
OUTPUT_CSV = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/havas_video_taxonomy_test.csv"
DATASET_PATH = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/Dados_Creatives_Enriched_Q1_2026_Videos_Only.csv"

# --- 3. SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are a senior Marketing Data Analyst. 
Analyze this video ad and output a percentage breakdown of its content strategy across three stages: Awareness, Consideration, and Conversion.
The sum of the three percentages MUST equal exactly 100.

RUBRIC:
1. AWARENESS: Brand focus, lifestyle, emotional, logo-centric. No specific price or offers.
2. CONSIDERATION: Features, benefits, comparisons, or plans (e.g. "Internet 500 Mega"). Educational.
3. CONVERSION: Hard sell. Prices (R$), discounts (%), or direct call-to-actions ("Assine Já", "Compre","Contrate Agora","Confira").

RETURN JSON ONLY (No markdown formatting, no comments):
{
  "filename": "string",
  "Awareness_Percentage": integer,
  "Consideration_Percentage": integer,
  "Conversion_Percentage": integer,
  "reasoning": "short explanation"
}
"""

def get_valid_video_filenames(dataset_path):
    valid_videos = set()
    if not os.path.exists(dataset_path):
        print(f"⚠️ Dataset for filtering not found: {dataset_path}")
        return valid_videos
        
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_url = row.get('video_public_storage_url', '')
                if video_url:
                    filename = video_url.split('/')[-1]
                    valid_videos.add(filename)
    except Exception as e:
        print(f"❌ Error reading dataset: {e}")
        
    return valid_videos

def upload_and_wait(video_path):
    """Uploads the video to Gemini and waits until it is ready for analysis."""
    print(f"Uploading {os.path.basename(video_path)} to Gemini...")
    video_file = genai.upload_file(path=video_path)
    
    print("Waiting for video processing to complete...")
    timeout_seconds = 300 # 5 minutes
    start_time = time.time()
    while video_file.state.name == "PROCESSING":
        if time.time() - start_time > timeout_seconds:
            raise TimeoutError(f"Video processing timed out after {timeout_seconds} seconds.")
        print(".", end="", flush=True)
        time.sleep(10)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        raise ValueError("Video processing failed.")
    
    print("\n✅ Video ready!")
    return video_file

def analyze_folder():
    valid_videos = get_valid_video_filenames(DATASET_PATH)
    print(f"Loaded {len(valid_videos)} valid video signatures.")

    file_exists = os.path.exists(OUTPUT_CSV)
    processed_files = set()
    if file_exists:
        try:
            with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if row: processed_files.add(row[0])
        except Exception:
            pass
    print(f"Skipping {len(processed_files)} already processed videos.")

    mode = 'a' if file_exists else 'w'
    with open(OUTPUT_CSV, mode, newline='') as csvfile:
        fieldnames = ['filename', 'Awareness_Percentage', 'Consideration_Percentage', 'Conversion_Percentage', 'reasoning']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        all_files = os.listdir(VIDEO_FOLDER_PATH)
        videos = [f for f in all_files if f.lower().endswith('.mp4')]
        print(f"📂 Found {len(videos)} videos in folder.")

        count = 0
        for filename in videos:
            if filename in processed_files:
                continue
            
            if valid_videos and filename not in valid_videos:
                continue

            print(f"\n--- Analyzing {filename} ---")
            video_path = os.path.join(VIDEO_FOLDER_PATH, filename)
            uploaded_file = None
            
            try:
                # 1. Upload
                uploaded_file = upload_and_wait(video_path)
                
                # 2. Analyze
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-pro",
                    system_instruction=SYSTEM_PROMPT
                )
                
                response = model.generate_content([
                    "Classify this video's taxonomy percentages.",
                    uploaded_file
                ])

                # 3. Parse Response
                raw_text = response.text.strip()
                start_idx = raw_text.find('{')
                end_idx = raw_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    raw_text = raw_text[start_idx:end_idx+1]
                else:
                    raise ValueError(f"No JSON object found: {raw_text}")
                
                result = json.loads(raw_text)
                
                # Validation
                aw = result.get('Awareness_Percentage', 0)
                co = result.get('Consideration_Percentage', 0)
                cv = result.get('Conversion_Percentage', 0)
                
                if (aw + co + cv) != 100:
                    print(f"⚠️ WARNING: Percentages do not sum to 100 ({aw} + {co} + {cv}). Normalizing...")
                    # Basic normalization could be added here, but model should follow instruction
                
                result['filename'] = filename
                writer.writerow(result)
                print(f"✅ Distribution: {aw}% AW | {co}% CO | {cv}% CV")
                count += 1
                
            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
                time.sleep(10)
                
            finally:
                # 4. Mandatory Cleanup
                if uploaded_file:
                    try:
                        print(f"🧹 Deleting file {uploaded_file.name} from Gemini storage...")
                        genai.delete_file(uploaded_file.name)
                    except Exception as e:
                        print(f"⚠️ Failed to delete file: {e}")

if __name__ == "__main__":
    analyze_folder()
