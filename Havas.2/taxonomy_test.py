import os
import csv      # <--- Added missing import
import json
import base64
import mimetypes
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. SETUP API KEY ---
# Pointing to your specific .env file in the Havas.2 folder
env_path = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/.env"
load_dotenv(dotenv_path=env_path)

# Verify Key
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print(f"❌ ERROR: Could not find API Key at: {env_path}")
    print("Check if the file exists and has GOOGLE_API_KEY=...")
    exit()
else:
    print("✅ API Key loaded successfully!")

genai.configure(api_key=api_key)

# --- 2. CONFIGURATION ---
IMAGE_FOLDER_PATH = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/public_storage_url-3"
OUTPUT_CSV = "havas_taxonomy_test.csv"
DATASET_PATH = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/Dados_Creatives_Enriched_Q1_2026_Images_Only.csv"

# --- 3. THE ANALYST (System Prompt) ---
SYSTEM_PROMPT = """
You are a senior Marketing Data Analyst. Classify this digital ad into one of three stages.

RUBRIC:
1. AWARENESS: Brand focus, lifestyle, emotional, logo-centric. No specific offers.
2. CONSIDERATION: Features, benefits, comparisons, or plans (e.g. "Internet 500 Mega"). Educational.
3. CONVERSION: Hard sell. Prices (R$), discounts (%), or direct call-to-actions ("Assine Já", "Compre","Contrate Agora","Confira", "Saiba Mais", "Aproveite", "Aproveite Agora","Colsulte aqui").

RETURN JSON ONLY:
{
  "filename": "string",
  "category": "Awareness" | "Consideration" | "Conversion",
  "reasoning": "short explanation"
}
"""

def get_valid_image_filenames(dataset_path):
    """Reads the CSV and creates a set of filenames belonging to actual images (no video screenshots)."""
    valid_images = set()
    if not os.path.exists(dataset_path):
        print(f"⚠️ Dataset for filtering not found: {dataset_path}")
        return valid_images
        
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                pub_url = row.get('public_storage_url', '')
                if pub_url:
                    filename = pub_url.split('/')[-1]
                    valid_images.add(filename)
                    # Also keep the base name without extension
                    base_name, _ = os.path.splitext(filename)
                    valid_images.add(base_name)
    except Exception as e:
        print(f"❌ Error reading dataset: {e}")
        
    return valid_images

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_folder():
    print("Checking for valid images in the dataset to filter out video screenshots...")
    valid_images = get_valid_image_filenames(DATASET_PATH)
    print(f"Loaded {len(valid_images)} total valid image signatures from dataset.")

    # Prepare CSV file with 'link' column
    file_exists = os.path.exists(OUTPUT_CSV)
    processed_files = set()
    if file_exists:
        try:
            with open(OUTPUT_CSV, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # skip header
                for row in reader:
                    if row: processed_files.add(row[0])
        except Exception:
            pass
    print(f"Skipping {len(processed_files)} already processed images.")

    mode = 'a' if file_exists else 'w'
    with open(OUTPUT_CSV, mode, newline='') as csvfile:
        fieldnames = ['filename', 'category', 'reasoning', 'link']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        # Get images
        if not os.path.exists(IMAGE_FOLDER_PATH):
            print(f"❌ Error: Folder not found at {IMAGE_FOLDER_PATH}")
            return

        all_files = os.listdir(IMAGE_FOLDER_PATH)
        images = [f for f in all_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        
        print(f"📂 Found {len(images)} images in folder.")
        
        if len(images) == 0:
            print("⚠️ No images found! Do your files have extensions like .jpg?")
            return

        # LOOP THROUGH IMAGES
        count = 0
        for filename in images:
            if filename in processed_files:
                continue
            
            # Check if it's a true image based on the dataset
            base_name, _ = os.path.splitext(filename)
            if valid_images and (filename not in valid_images and base_name not in valid_images):
                continue

            
            print(f"Analyzing {filename}...", end=" ")
            image_path = os.path.join(IMAGE_FOLDER_PATH, filename)
            
            # Create Clickable Link for Excel
            abs_path = os.path.abspath(image_path)
            excel_link = f'=HYPERLINK("file://{abs_path}", "Open Image")'
            
            try:
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type:
                    mime_type = "image/jpeg"
                    
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    system_instruction=SYSTEM_PROMPT
                )
                
                response = model.generate_content(
                    [
                        "Classify this.",
                        {"mime_type": mime_type, "data": image_data}
                    ],
                    safety_settings=[
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                    ]
                )

                # Clean up the response text just in case Gemini adds markdown formatting
                raw_text = response.text.strip()
                start_idx = raw_text.find('{')
                end_idx = raw_text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    raw_text = raw_text[start_idx:end_idx+1]
                else:
                    raise ValueError(f"No JSON object found in response: {raw_text}")
                
                print(f"DEBUG raw_text: {raw_text}")
                result = json.loads(raw_text.strip())
                result['filename'] = filename
                result['link'] = excel_link # Add link to result
                
                writer.writerow(result)
                print(f"✅ {result['category']}")
                count += 1
                
                # Sleep to prevent hitting Gemini API rate limit (15 requests per minute)
                time.sleep(4.5)

            except Exception as e:
                print(f"❌ Error processing {filename}: {e}")
                # We sleep slightly, but no need to sleep 60 seconds if it's just a safety filter
                if "429" in str(e) or "Quota" in str(e):
                    print("Sleeping 60 seconds to reset quota...")
                    time.sleep(60)
                else:
                    print("Skipping to next file...")
                    time.sleep(4.5)

if __name__ == "__main__":
    analyze_folder()