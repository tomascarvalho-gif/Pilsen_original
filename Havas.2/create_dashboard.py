import csv
import os
import base64

# === CONFIGURATION ===
# Path to your CSV file (Make sure this matches your output file)
CSV_FILE = "havas_taxonomy_test.csv"

# Path to your images (Must match what you used before)
IMAGE_FOLDER = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/public_storage_url-3"

# Output file name
OUTPUT_HTML = "../Taxonomy_Report.html"

# === HTML TEMPLATE ===
HTML_HEADER = """
<!DOCTYPE html>
<html>
<head>
    <title>Taxonomy Classification Report</title>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }
        h1 { text-align: center; color: #444; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .image-container { width: 100%; height: 250px; background: #eee; display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .image-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .content { padding: 15px; }
        .badge { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; color: white; margin-bottom: 10px; }
        
        /* COLOR CODING */
        .badge.Conversion { background-color: #28a745; } /* Green */
        .badge.Awareness { background-color: #007bff; }  /* Blue */
        .badge.Consideration { background-color: #ffc107; color: #333; } /* Yellow */
        
        .filename { font-size: 12px; color: #888; margin-bottom: 5px; }
        .reasoning { font-size: 14px; line-height: 1.4; color: #555; }
    </style>
</head>
<body>
    <h1>AI Taxonomy Classification Results</h1>
    
    <div style="text-align: center; margin-bottom: 20px;">
        <label for="class-filter" style="font-weight: bold; margin-right: 10px;">Filter by Class:</label>
        <select id="class-filter" onchange="filterCards()" style="padding: 8px; border-radius: 5px; border: 1px solid #ccc; font-size: 16px;">
            <option value="All">All</option>
            <option value="Awareness">Awareness</option>
            <option value="Consideration">Consideration</option>
            <option value="Conversion">Conversion</option>
            <option value="Unclassified">Unclassified</option>
        </select>
    </div>

    <script>
        function filterCards() {
            var filterValue = document.getElementById('class-filter').value;
            var cards = document.querySelectorAll('.card');
            
            cards.forEach(function(card) {
                var badge = card.querySelector('.badge');
                if (badge) {
                    var cardClass = badge.textContent.trim();
                    if (filterValue === 'All' || cardClass === filterValue) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                }
            });
        }
    </script>
    <div class="gallery">
"""

HTML_FOOTER = """
    </div>
</body>
</html>
"""

def image_to_base64(path):
    """Encodes image to base64 so it embeds directly inside the HTML"""
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def generate_report():
    print("Generating report...")
    
    # We open the output HTML file
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as html_file:
        html_file.write(HTML_HEADER)
        
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                count = 0
                for row in reader:
                    filename = row['filename']
                    category = row['category']
                    reasoning = row['reasoning']
                    
                    # Construct full image path
                    img_path = os.path.join(IMAGE_FOLDER, filename)
                    
                    # Convert to base64 for embedding
                    img_data = image_to_base64(img_path)
                    
                    if img_data:
                        html_content = f"""
                        <div class="card">
                            <div class="image-container">
                                <img src="data:image/jpeg;base64,{img_data}" alt="{filename}">
                            </div>
                            <div class="content">
                                <div class="filename">{filename}</div>
                                <span class="badge {category}">{category}</span>
                                <p class="reasoning">{reasoning}</p>
                            </div>
                        </div>
                        """
                        html_file.write(html_content)
                        count += 1
                        print(f"Added {filename} to report.")
            
            html_file.write(HTML_FOOTER)
            print(f"\n✅ Success! Report generated: {OUTPUT_HTML}")
            print("You can now open this file in Chrome or Safari.")
            
        except FileNotFoundError:
            print(f"❌ Error: Could not find CSV file: {CSV_FILE}")
            print("Make sure the CSV is in the same folder where you are running this script.")

if __name__ == "__main__":
    generate_report()