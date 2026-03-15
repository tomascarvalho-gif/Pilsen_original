import os
import json
import glob

# Path to your JSON dataset
DATA_DIR = "xbrl_data_json"

print("🔍 SCANNING FOR ROE ANOMALIES (>500%) IN 2020-2021...\n")

# Find all JSON files in the dataset
json_files = glob.glob(os.path.join(DATA_DIR, "**", "*.json"), recursive=True)

for file_path in json_files:
    # We only care about the pandemic window where the spike occurred
    if "2020" in file_path or "2021" in file_path:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
                # Check if the required keys exist in your base data
                if "Net income" in data and "Total shareholders' equity" in data:
                    net_income = float(data["Net income"])
                    equity = float(data["Total shareholders' equity"])
                    
                    # Prevent division by zero
                    if equity != 0:
                        roe = (net_income / equity) * 100
                        
                        # Flag the anomaly if ROE is massively inflated
                        if roe > 500 or roe < -500:
                            ticker = os.path.basename(os.path.dirname(file_path))
                            filename = os.path.basename(file_path)
                            print(f"🚨 ANOMALY DETECTED: {ticker} ({filename})")
                            print(f"   Net Income: ${net_income:,.2f}")
                            print(f"   Equity:     ${equity:,.2f}")
                            print(f"   Calculated ROE: {roe:.2f}%\n")
        except Exception as e:
            pass

print("✅ SCAN COMPLETE.")