import csv
import os
import random
import json

IMAGE_CSV = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/havas_taxonomy_test.csv"
VIDEO_CSV = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/havas_video_taxonomy_test.csv"
IMAGE_FOLDER = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/public_storage_url-3"
VIDEO_FOLDER = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Havas.2/video_public_storage_url-3"
OUTPUT_HTML = "/Users/tomasdefreitascarvalho/Desktop/Work Space/Rubens/synapsee/Unified_Taxonomy_Dashboard.html"

HTML_HEADER = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Unified Taxonomy Dashboard - TIM</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; display: flex; margin: 0; background-color: #f4f6f8; color: #333; height: 100vh; overflow: hidden; }
        
        /* Sidebar Styles */
        .sidebar { width: 300px; background: #ffffff; border-right: 1px solid #eaeaea; padding: 25px 20px; overflow-y: auto; box-shadow: 2px 0 10px rgba(0,0,0,0.03); flex-shrink: 0; }
        .sidebar h2 { font-size: 20px; color: #111; margin-top: 0; margin-bottom: 25px; font-weight: 700; letter-spacing: -0.5px; }
        
        .menu-block { margin-bottom: 30px; }
        .menu-title { font-weight: 600; font-size: 13px; margin-bottom: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.8px; }
        
        .menu-list { list-style: none; padding: 0; margin: 0; }
        .menu-list > li { margin-bottom: 5px; }
        
        /* Main Category e.g., TIM */
        .menu-item { display: flex; align-items: center; cursor: pointer; font-size: 15px; color: #333; padding: 8px 12px; border-radius: 6px; font-weight: 500; transition: background 0.2s; }
        .menu-item:hover { background-color: #f0f4f8; color: #0056b3; }
        .menu-item.active { background-color: #e6f0ff; color: #0056b3; font-weight: 600; }
        
        /* Sub-items e.g., Video / Imagem */
        .submenu-list { list-style: none; padding-left: 25px; margin-top: 5px; margin-bottom: 10px; }
        .submenu-item { cursor: pointer; font-size: 14px; color: #666; padding: 6px 10px; border-radius: 6px; transition: all 0.2s; display: flex; align-items: center; margin-bottom: 2px;}
        .submenu-item:hover { background-color: #f8f9fa; color: #000; }
        .submenu-item.active { background-color: #f0f4f8; color: #0056b3; font-weight: 600; }
        
        .icon-text { font-size: 14px; font-weight: 600; margin-right: 8px; width: 20px; text-align: center; color: #888;}
        .menu-item:hover .icon-text, .menu-item.active .icon-text { color: #0056b3; }
        
        /* Main Content Styles */
        .main-content { flex: 1; padding: 40px; overflow-y: auto; display: flex; flex-direction: column; }
        .header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px; border-bottom: 2px solid #eaeaea; padding-bottom: 15px; }
        .header h1 { margin: 0; font-size: 28px; color: #111; font-weight: 700; letter-spacing: -0.5px; }
        #counter { font-size: 15px; color: #666; font-weight: 500; background: #eee; padding: 5px 12px; border-radius: 20px; }
        
        /* Gallery Grid */
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 25px; padding-bottom: 20px;}
        
        /* Card Styles */
        .card { background: white; border-radius: 14px; border: 1px solid #eee; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; display: flex; flex-direction: column; position: relative;}
        .card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.08); border-color: transparent;}
        
        .media-container { width: 100%; height: 280px; background: #000; display: flex; align-items: center; justify-content: center; overflow: hidden; position: relative; }
        .media-container img, .media-container video { width: 100%; height: 100%; object-fit: contain; }
        
        .tag-type { position: absolute; top: 12px; left: 12px; color: white; padding: 4px 10px; border-radius: 6px; font-size: 10px; font-weight: 800; z-index: 10; letter-spacing: 0.5px;}
        .tag-video { background: rgba(231, 76, 60, 0.85); backdrop-filter: blur(4px);}
        .tag-image { background: rgba(52, 152, 219, 0.85); backdrop-filter: blur(4px);}
        
        .content { padding: 20px; flex: 1; display: flex; flex-direction: column; }
        .filename { font-size: 12px; color: #888; margin-bottom: 12px; word-break: break-all; font-family: monospace;}
        .reasoning { font-size: 14px; line-height: 1.6; color: #444; flex: 1; margin: 0; }
        
        /* Visual Taxonomy Bars/Badges */
        .progress-bar-container { width: 100%; height: 16px; background-color: #eee; border-radius: 8px; margin-bottom: 15px; display: flex; overflow: hidden; }
        .bar-aw { background-color: #007bff; height: 100%; text-align: center; color: white; font-size: 9px; line-height: 16px; font-weight: bold; }
        .bar-co { background-color: #ffc107; height: 100%; color: #333; text-align: center; font-size: 9px; line-height: 16px; font-weight: bold; }
        .bar-cv { background-color: #28a745; height: 100%; text-align: center; color: white; font-size: 9px; line-height: 16px; font-weight: bold; }
        
        .badge { display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-bottom: 15px; text-align: center; width: fit-content;}
        .badge.aw { background-color: #e7f1ff; color: #007bff; border: 1px solid #b3d7ff; }
        .badge.co { background-color: #fff8e1; color: #e6a200; border: 1px solid #ffeeba; }
        .badge.cv { background-color: #e8f5e9; color: #28a745; border: 1px solid #c3e6cb; }

        /* Load More Button */
        #load-more {
            display: none;
            margin: 20px auto 40px auto;
            padding: 12px 30px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        #load-more:hover { background-color: #0056b3; }
    </style>
</head>
<body>

    <!-- SIDEBAR -->
    <div class="sidebar">
        <h2>Synapsee Analytics</h2>
        
        <!-- SECTION 1 -->
        <div class="menu-block">
            <div class="menu-title">Banco de Dados</div>
            <ul class="menu-list">
                <li>
                    <div class="menu-item active" id="btn-tim-all" onclick="filterGallery('all', 'TIM (Todos)', this)">
                        <span class="icon-text">DA</span> TIM
                    </div>
                    <ul class="submenu-list">
                        <li class="submenu-item" onclick="filterGallery('video', 'TIM: Vídeos', this)">
                            <span class="icon-text">-</span> Vídeo
                        </li>
                        <li class="submenu-item" onclick="filterGallery('image', 'TIM: Imagens', this)">
                            <span class="icon-text">-</span> Imagem
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
        
        <!-- SECTION 2 -->
        <div class="menu-block">
            <div class="menu-title">Organização</div>
            <ul class="menu-list">
                <li>
                    <div class="menu-item" onclick="alert('Funcionalidade de inserção de novas pastas em breve.')">
                        <span class="icon-text">+</span> Criar nova pasta
                    </div>
                    <ul class="submenu-list">
                        <li class="submenu-item" onclick="alert('Área Privada em breve.')">
                            <span class="icon-text">-</span> Privada
                        </li>
                        <li class="submenu-item" onclick="alert('Área Pública em breve.')">
                            <span class="icon-text">-</span> Pública
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
    </div>
    
    <!-- MAIN CONTENT -->
    <div class="main-content">
        <div class="header">
            <h1 id="page-title">TIM (Todos)</h1>
            <div id="counter">Carregando itens...</div>
        </div>
        
        <div class="gallery" id="gallery"></div>
        
        <button id="load-more" onclick="loadMore()">Carregar Mais</button>
    </div>

    <script>
        // DATA PLACEHOLDER
        const mediaData = __MEDIA_DATA_PLACEHOLDER__;
        
        let currentFilter = 'all';
        let currentPage = 1;
        const PAGE_SIZE = 50;
        let filteredData = [];

        function filterGallery(type, title, clickedElement) {
            // Update UI
            document.querySelectorAll('.menu-item, .submenu-item').forEach(el => el.classList.remove('active'));
            if(clickedElement) clickedElement.classList.add('active');
            document.getElementById('page-title').innerText = title;

            // Filter logic
            currentFilter = type;
            filteredData = mediaData.filter(item => type === 'all' || item.type === type);
            document.getElementById('counter').innerText = filteredData.length + " mídias encontradas";
            
            // Reset and render
            currentPage = 1;
            document.getElementById('gallery').innerHTML = '';
            renderPage();
            
            // Scroll to top
            document.querySelector('.main-content').scrollTop = 0;
        }
        
        function renderPage() {
            const start = (currentPage - 1) * PAGE_SIZE;
            const end = start + PAGE_SIZE;
            const pageItems = filteredData.slice(start, end);
            
            const gallery = document.getElementById('gallery');
            pageItems.forEach(item => {
                const card = document.createElement('div');
                card.className = 'card';
                
                if (item.type === 'video') {
                    let bars = '';
                    if (item.aw > 0) bars += `<div class="bar-aw" style="width: ${item.aw}%;">${item.aw}% AW</div>`;
                    if (item.co > 0) bars += `<div class="bar-co" style="width: ${item.co}%;">${item.co}% CO</div>`;
                    if (item.cv > 0) bars += `<div class="bar-cv" style="width: ${item.cv}%;">${item.cv}% CV</div>`;
                    
                    card.innerHTML = `
                        <div class="tag-type tag-video">VÍDEO</div>
                        <div class="media-container">
                            <video controls preload="metadata">
                                <source src="${item.uri}#t=0.5" type="video/mp4">
                            </video>
                        </div>
                        <div class="content">
                            <div class="filename" title="${item.filename}">${item.filename}</div>
                            <div class="progress-bar-container">${bars}</div>
                            <p class="reasoning"><strong>Análise:</strong> ${item.reasoning}</p>
                        </div>
                    `;
                } else {
                    card.innerHTML = `
                        <div class="tag-type tag-image">IMAGEM</div>
                        <div class="media-container">
                            <img src="${item.uri}" alt="${item.filename}" loading="lazy">
                        </div>
                        <div class="content">
                            <div class="filename" title="${item.filename}">${item.filename}</div>
                            <div class="badge ${item.cat}">${item.category}</div>
                            <p class="reasoning"><strong>Análise:</strong> ${item.reasoning}</p>
                        </div>
                    `;
                }
                gallery.appendChild(card);
            });
            
            if (end < filteredData.length) {
                document.getElementById('load-more').style.display = 'block';
            } else {
                document.getElementById('load-more').style.display = 'none';
            }
        }
        
        function loadMore() {
            currentPage++;
            renderPage();
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            filterGallery('all', 'TIM (Todos)', document.getElementById('btn-tim-all'));
        });
    </script>
</body>
</html>
"""

def extract_basename(filename):
    return os.path.splitext(filename)[0]

def build_dashboard():
    print("Building Professional Unified Dashboard...")
    
    video_basenames = set()
    js_items = []
    
    # --- 1. READ VIDEOS (Populate filter set and js_items) ---
    print("Reading Video Data...")
    try:
        with open(VIDEO_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            
            for row in reader:
                if not row or len(row) < 5: continue
                filename = row[0]
                
                # Check for skipped videos
                if 'TIMEOUT' in row[4]: continue
                
                try:
                    aw, co, cv = int(row[1]), int(row[2]), int(row[3])
                except Exception:
                    aw, co, cv = 0, 0, 0
                reasoning = row[4]
                
                # Register base name to filter images later
                video_basenames.add(extract_basename(filename))
                
                abs_path = os.path.join(VIDEO_FOLDER, filename)
                uri = f"file://{abs_path}"
                
                js_items.append({
                    "type": "video",
                    "filename": filename,
                    "uri": uri,
                    "aw": aw,
                    "co": co,
                    "cv": cv,
                    "reasoning": reasoning
                })
    except Exception as e:
        print(f"Error reading videos: {e}")

    # --- 2. READ IMAGES (Filter out video thumbnails) ---
    print("Reading Image Data...")
    filtered_out_count = 0
    try:
        with open(IMAGE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            
            for row in reader:
                if not row or len(row) < 3: continue
                filename = row[0]
                
                # --- FILTER LOGIC ---
                # Exclude image if it's just a thumbnail frame from an existing video
                if extract_basename(filename) in video_basenames:
                    filtered_out_count += 1
                    continue
                
                category = row[1]
                reasoning = row[2]
                
                cat_lower = 'aw'
                if 'consideration' in category.lower(): cat_lower = 'co'
                elif 'conversion' in category.lower(): cat_lower = 'cv'
                
                abs_path = os.path.join(IMAGE_FOLDER, filename)
                uri = f"file://{abs_path}"
                
                js_items.append({
                    "type": "image",
                    "filename": filename,
                    "uri": uri,
                    "category": category,
                    "cat": cat_lower,
                    "reasoning": reasoning
                })
    except Exception as e:
        print(f"Error reading images: {e}")

    print(f"Filtered out {filtered_out_count} image thumbnails belonging to videos.")

    # --- 3. SHUFFLE AND EXPORT ---
    print("Generating Javascript JSON Database...")
    random.seed(42)
    random.shuffle(js_items)
    
    # Inject JSON array into HTML
    json_data_str = json.dumps(js_items)
    final_html = HTML_HEADER.replace("__MEDIA_DATA_PLACEHOLDER__", json_data_str)
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as out_f:
        out_f.write(final_html)
        
    print(f"\\n✅ Success! Unified Dashboard ready at: {OUTPUT_HTML} !!")

if __name__ == "__main__":
    build_dashboard()
