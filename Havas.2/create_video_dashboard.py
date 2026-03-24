import csv
import os

# === CONFIGURATION ===
CSV_FILE = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/havas_video_taxonomy_test.csv"
VIDEO_FOLDER = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/video_public_storage_url-3"
OUTPUT_HTML = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Video_Taxonomy_Report.html"

# === HTML TEMPLATE ===
HTML_HEADER = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Video Taxonomy Classification Report</title>
    <style>
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f9; color: #333; padding: 20px; }
        h1 { text-align: center; color: #444; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card { background: white; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden; transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .video-container { width: 100%; height: 250px; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; }
        .video-container video { width: 100%; height: 100%; object-fit: contain; }
        .content { padding: 15px; }
        
        .progress-bar-container { width: 100%; height: 20px; background-color: #eee; border-radius: 10px; margin-bottom: 15px; display: flex; overflow: hidden; }
        .bar-aw { background-color: #007bff; height: 100%; text-align: center; color: white; font-size: 10px; line-height: 20px; font-weight: bold; }
        .bar-co { background-color: #ffc107; height: 100%; color: #333; text-align: center; font-size: 10px; line-height: 20px; font-weight: bold; }
        .bar-cv { background-color: #28a745; height: 100%; text-align: center; color: white; font-size: 10px; line-height: 20px; font-weight: bold; }
        
        .filename { font-size: 12px; color: #888; margin-bottom: 5px; word-break: break-all; }
        .reasoning { font-size: 14px; line-height: 1.4; color: #555; }
        .legend {text-align: center; margin-bottom: 20px; font-size: 14px;}
        .leg-aw {color: #007bff; font-weight: bold;}
        .leg-co {color: #ffc107; font-weight: bold;}
        .leg-cv {color: #28a745; font-weight: bold;}
        .filters { text-align: center; margin-bottom: 30px; background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); display: inline-table; width: auto; margin-left: auto; margin-right: auto; }
        .filter-group { display: inline-block; margin: 0 15px; }
        .filter-group label { font-weight: bold; margin-right: 5px; font-size: 14px; color: #444; }
        select { padding: 5px 10px; border-radius: 5px; border: 1px solid #ccc; font-size: 14px; }
        .dashboard-header {text-align: center;}
        #counter { font-weight: bold; color: #666; margin-top: 10px; font-size: 14px; }
    </style>
    <script>
        function filterVideos() {
            var awFilter = parseInt(document.getElementById('filter-aw').value);
            var coFilter = parseInt(document.getElementById('filter-co').value);
            var cvFilter = parseInt(document.getElementById('filter-cv').value);
            
            var cards = document.getElementsByClassName('card');
            var visibleCount = 0;
            
            for (var i = 0; i < cards.length; i++) {
                var card = cards[i];
                var aw = parseInt(card.getAttribute('data-aw')) || 0;
                var co = parseInt(card.getAttribute('data-co')) || 0;
                var cv = parseInt(card.getAttribute('data-cv')) || 0;
                
                if (aw >= awFilter && co >= coFilter && cv >= cvFilter) {
                    card.style.display = 'block';
                    visibleCount++;
                } else {
                    card.style.display = 'none';
                }
            }
            document.getElementById('counter').innerText = visibleCount + " videos showing";
        }
    </script>
</head>
<body>
    <h1>AI Video Taxonomy Classification Results</h1>
    <div class="legend">
        <span class="leg-aw">■ Awareness</span> &nbsp;&nbsp; 
        <span class="leg-co">■ Consideration</span> &nbsp;&nbsp; 
        <span class="leg-cv">■ Conversion</span>
    </div>

    <div class="dashboard-header">
        <div class="filters">
            <div class="filter-group">
                <label class="leg-aw">Awareness >=</label>
                <select id="filter-aw" onchange="filterVideos()">
                    <option value="0">0%</option>
                    <option value="25">25%</option>
                    <option value="50">50%</option>
                    <option value="75">75%</option>
                    <option value="90">90%</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="leg-co">Consideration >=</label>
                <select id="filter-co" onchange="filterVideos()">
                    <option value="0">0%</option>
                    <option value="25">25%</option>
                    <option value="50">50%</option>
                    <option value="75">75%</option>
                    <option value="90">90%</option>
                </select>
            </div>
            <div class="filter-group">
                <label class="leg-cv">Conversion >=</label>
                <select id="filter-cv" onchange="filterVideos()">
                    <option value="0">0%</option>
                    <option value="25">25%</option>
                    <option value="50">50%</option>
                    <option value="75">75%</option>
                    <option value="90">90%</option>
                </select>
            </div>
            <div id="counter">--- videos showing</div>
        </div>
    </div>
    
    <div class="gallery">
"""

HTML_FOOTER = """
    </div>
</body>
</html>
"""

def generate_report():
    print("Generating Video Report...")
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as html_file:
        html_file.write(HTML_HEADER)
        
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                
                count = 0
                for row in reader:
                    if not row or row[0] == 'filename':
                        continue
                    
                    filename = row[0]
                    aw = row[1] if len(row) > 1 else '0'
                    co = row[2] if len(row) > 2 else '0'
                    cv = row[3] if len(row) > 3 else '0'
                    reasoning = row[4] if len(row) > 4 else ''
                    
                    try:
                        aw_val = int(aw)
                        co_val = int(co)
                        cv_val = int(cv)
                    except ValueError:
                        aw_val, co_val, cv_val = 0, 0, 0
                    
                    # Direct link to the local file for the browser
                    # We just use relative path from where HTML is saved, or absolute file:// 
                    abs_path = os.path.join(VIDEO_FOLDER, filename)
                    # Because browser security might block absolute paths, it's safer to use an absolute path for local viewing
                    video_uri = f"file://{abs_path}"
                    
                    html_content = f"""
                    <div class="card" data-aw="{aw_val}" data-co="{co_val}" data-cv="{cv_val}">
                        <div class="video-container">
                            <video controls preload="metadata">
                                <source src="{video_uri}#t=0.5" type="video/mp4">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                        <div class="content">
                            <div class="filename">{filename}</div>
                            
                            <!-- Visual Percentage Bar -->
                            <div class="progress-bar-container">
                    """
                    
                    if aw_val > 0:
                        html_content += f'<div class="bar-aw" style="width: {aw_val}%;">{aw_val}%</div>'
                    if co_val > 0:
                        html_content += f'<div class="bar-co" style="width: {co_val}%;">{co_val}%</div>'
                    if cv_val > 0:
                        html_content += f'<div class="bar-cv" style="width: {cv_val}%;">{cv_val}%</div>'
                        
                    html_content += f"""
                            </div>
                            
                            <p class="reasoning"><strong>Analysis:</strong> {reasoning}</p>
                        </div>
                    </div>
                    """
                    html_file.write(html_content)
                    count += 1
            
            # Initialize the counter correctly after load
            html_file.write(HTML_FOOTER.replace('</body>', f'<script>document.getElementById("counter").innerText = "{count} videos showing";</script></body>'))
            print(f"\\n✅ Success! Video Report generated with {count} videos at: {OUTPUT_HTML}")
            
        except FileNotFoundError:
            print(f"❌ Error: Could not find CSV file: {CSV_FILE}")
            print("The video classification process might still be starting, or CSV hasn't been written to yet.")

if __name__ == "__main__":
    generate_report()
