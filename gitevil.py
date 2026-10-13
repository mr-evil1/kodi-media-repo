import os
import xml.etree.ElementTree as ET
import re
import hashlib
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Konfiguration für dein Repository
REPO_USER = "mr-evil1"
REPO_NAME = "kodi-media-repo"
GENERATED_DIR = "_generated_assets"
BANNER_URL = "https://raw.githubusercontent.com/{}/{}/refs/heads/main/repository.kodi.media/kodi-media.jpg".format(REPO_USER, REPO_NAME)

def clean_kodi_text(text):
    """Wandelt Kodi-BBCodes ([COLOR], [B], [CR]) in valides HTML um"""
    if not text:
        return ""
    
    color_map = {
        'blue': '#3498db', 'red': '#e74c3c', 'green': '#2ecc71',
        'yellow': '#f1c40f', 'orange': '#e67e22', 'white': '#ffffff',
        'black': '#000000', 'cyan': '#1abc9c', 'magenta': '#9b59b6',
        'grey': '#95a5a6', 'gray': '#95a5a6'
    }
    
    def replace_color(match):
        col_val = match.group(1).lower()
        content = match.group(2)
        if col_val in color_map:
            hex_code = color_map[col_val]
        elif len(col_val) == 8:
            hex_code = f"#{col_val[2:]}"
        elif len(col_val) == 6:
            hex_code = f"#{col_val}"
        else:
            hex_code = '#ffffff'
        return f'<span style="color: {hex_code};">{content}</span>'

    text = re.sub(r'\[COLOR\s*([a-zA-Z0-9#]+)\](.*?)\[/COLOR\]', replace_color, text, flags=re.IGNORECASE)
    text = re.sub(r'\[B\](.*?)\[/B\]', r'<strong>\1</strong>', text, flags=re.IGNORECASE)
    text = re.sub(r'\[I\](.*?)\[/I\]', r'<em>\1</em>', text, flags=re.IGNORECASE)
    text = text.replace("[CR]", "<br>").replace("[cr]", "<br>")
    
    return text

def find_asset(addon_id, explicit_path, fallback_filenames):
    candidates = []
    if explicit_path:
        candidates.append(os.path.join(addon_id, explicit_path))
    if isinstance(fallback_filenames, str):
        fallback_filenames = [fallback_filenames]
    for filename in fallback_filenames:
        candidates.append(os.path.join(addon_id, filename))
        candidates.append(os.path.join(addon_id, "resources", filename))
        candidates.append(os.path.join(addon_id, "media", filename))
    for path in candidates:
        if os.path.exists(path):
            url_path = path.replace("\\", "/")
            return f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/refs/heads/main/{url_path}"
    return None

def get_color_for_id(addon_id):
    digest = hashlib.md5(addon_id.encode("utf-8")).hexdigest()
    r = max(int(digest[0:2], 16), 40)
    g = max(int(digest[2:4], 16), 40)
    b = max(int(digest[4:6], 16), 40)
    return (r, g, b)

def get_font(size):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def get_initials(name, addon_id):
    source = name or addon_id.split(".")[-1]
    words = re.sub(r'[^A-Za-z0-9 ]', ' ', source).split()
    letters = "".join(w[0] for w in words[:2]).upper()
    return letters or "?"

def generate_icon(addon_id, name):
    out_dir = os.path.join(GENERATED_DIR, addon_id)
    out_path = os.path.join(out_dir, "icon.png")
    if os.path.exists(out_path):
        return out_path
    os.makedirs(out_dir, exist_ok=True)
    color = get_color_for_id(addon_id)
    img = Image.new("RGB", (256, 256), color)
    draw = ImageDraw.Draw(img)
    letters = get_initials(name, addon_id)
    font = get_font(110)
    bbox = draw.textbbox((0, 0), letters, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((256 - text_w) / 2 - bbox[0], (256 - text_h) / 2 - bbox[1]), letters, font=font, fill=(255, 255, 255))
    img.save(out_path)
    return out_path

def generate_html():
    if not os.path.exists("addons.xml"):
        print("Fehler: Keine addons.xml im Verzeichnis gefunden!")
        return

    tree = ET.parse("addons.xml")
    root = tree.getroot()
    
    addons_data = []

    for addon in root.findall("addon"):
        addon_id = addon.get("id")
        name = addon.get("name")
        version = addon.get("version")
        
        if "repository" in addon_id:
            continue

        summary = ""
        description = ""
        
        metadata = addon.find(".//extension[@point='xbmc.addon.metadata']")
        if metadata is not None:
            sum_elem = metadata.find("./summary[@lang='de']")
            if sum_elem is None:
                sum_elem = metadata.find("./summary")
                
            desc_elem = metadata.find("./description[@lang='de']")
            if desc_elem is None:
                desc_elem = metadata.find("./description")
            
            if sum_elem is not None and sum_elem.text: 
                summary = sum_elem.text
            if desc_elem is not None and desc_elem.text: 
                description = desc_elem.text

        final_desc = description or summary or "Keine Beschreibung verfügbar."
        final_desc = clean_kodi_text(final_desc)
        clean_name = clean_kodi_text(name)

        is_script_module = False
        if "script.module" in addon_id.lower():
            is_script_module = True
        for ext in addon.findall("extension"):
            point = ext.get("point", "")
            if "xbmc.python.modules" in point:
                is_script_module = True

        is_video_plugin = False
        if "plugin.video" in addon_id.lower():
            is_video_plugin = True
        for ext in addon.findall("extension"):
            point = ext.get("point", "")
            if "xbmc.python.pluginsource" in point and "video" in addon_id.lower():
                is_video_plugin = True

        icon_path = None
        assets = addon.find(".//extension[@point='xbmc.addon.metadata']/assets")
        if assets is not None:
            icon_elem = assets.find("icon")
            if icon_elem is not None and icon_elem.text:
                icon_path = icon_elem.text.strip()

        icon_url = find_asset(addon_id, icon_path, "icon.png")
        if icon_url is None:
            local_path = generate_icon(addon_id, name).replace("\\", "/")
            icon_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/refs/heads/main/{local_path}"

        zip_url = f"https://github.com/{REPO_USER}/{REPO_NAME}/raw/refs/heads/main/{addon_id}/{addon_id}-{version}.zip"

        addons_data.append({
            "id": addon_id,
            "name": clean_name,
            "raw_name": re.sub(r'<[^>]+>', '', clean_name),
            "version": version,
            "desc": final_desc,
            "icon": icon_url,
            "zip": zip_url,
            "is_script_module": is_script_module,
            "is_video_plugin": is_video_plugin
        })

    def render_cards(items):
        html = ""
        for item in items:
            cat_type = "all"
            if item['is_script_module']: cat_type = "scripts"
            elif item['is_video_plugin']: cat_type = "videos"

            html += f"""
                <div class="cyan-card" data-category="{cat_type}" data-name="{item['raw_name'].lower()}">
                    <div class="card-media">
                        <img src="{item['icon']}" alt="Icon">
                    </div>
                    <div class="card-info">
                        <h3 class="card-title">{item['name']}</h3>
                        <p class="card-desc">{item['desc']}</p>
                        <a href="{item['zip']}" class="cyan-btn">▶ ZIP herunterladen</a>
                    </div>
                </div>
            """
        return html

    all_cards_html = render_cards(addons_data)

    full_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kodi Media Repo - Cyan Edition</title>
    <style>
        :root {{
            --cyan-bg: #0b131a;
            --cyan-card-bg: #131c25;
            --cyan-primary: #00bcd4;
            --cyan-hover: #00acc1;
            --text-main: #ffffff;
            --text-sub: #b0bec5;
            --border-color: #22303c;
        }}

        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: var(--cyan-bg);
            color: var(--text-main);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }}

        .cyan-header {{
            text-align: center;
            padding: 3rem 1rem 2rem 1rem;
            background: linear-gradient(180deg, rgba(0, 188, 212, 0.12) 0%, rgba(11, 19, 26, 1) 100%);
        }}

        .banner-container {{
            max-width: 1000px;
            margin: 0 auto 1.5rem auto;
            padding: 0 1rem;
        }}

        .banner-container img {{
            width: 100%;
            height: auto;
            max-height: 220px;
            object-fit: cover;
            border-radius: 12px;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.7), 0 0 20px rgba(0, 188, 212, 0.15);
            border: 1px solid var(--border-color);
        }}

        .cyan-header h1 {{
            font-size: 3rem;
            font-weight: 800;
            margin: 0 0 0.5rem 0;
            color: var(--cyan-primary);
            letter-spacing: -0.03rem;
            /* Fetter, mehrschichtiger Schatten für den Titel */
            text-shadow: 0 3px 6px rgba(0, 0, 0, 0.9), 0 0 25px rgba(0, 188, 212, 0.4);
        }}

        .repo-url-box {{
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid var(--border-color);
            padding: 0.6rem 1.2rem;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            font-family: monospace;
            font-size: 0.95rem;
            color: var(--cyan-primary);
            margin-top: 0.8rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
        }}

        .category-nav {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin: 1.5rem auto 2.5rem auto;
            padding: 0 1rem;
            flex-wrap: wrap;
        }}

        .cat-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 0.6rem 1.2rem;
            border-radius: 30px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
            transition: all 0.2s ease;
        }}

        .cat-btn:hover {{
            background: rgba(0, 188, 212, 0.15);
            border-color: var(--cyan-primary);
            transform: translateY(-2px);
            box-shadow: 0 6px 15px rgba(0, 188, 212, 0.2);
        }}

        .cat-btn.active {{
            background: var(--cyan-primary);
            border-color: var(--cyan-primary);
            color: #000;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(0, 188, 212, 0.45);
        }}

        /* GRID: Standardmäßig 3 Spalten */
        main {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem 2rem 6rem 2rem;
        }}

        .addon-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2.5rem;
        }}

        /* CYAN CARD DESIGN MIT SCHATTENEFFEKT */
        .cyan-card {{
            background-color: var(--cyan-card-bg);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5), 0 1px 3px rgba(0, 188, 212, 0.05);
            display: flex;
            flex-direction: column;
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            border: 1px solid var(--border-color);
        }}

        .cyan-card:hover {{
            transform: translateY(-5px) scale(1.01);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7), 0 0 25px rgba(0, 188, 212, 0.3);
            border-color: var(--cyan-primary);
            z-index: 10;
        }}

        .card-media {{
            width: 100%;
            height: 160px;
            background-color: #000;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            border-bottom: 1px solid var(--border-color);
        }}

        .card-media img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 12px;
        }}

        .card-info {{
            padding: 1.2rem 1.5rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            align-items: center;
            text-align: center;
        }}

        .card-title {{
            margin: 0 0 0.5rem 0;
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-main);
            text-align: center;
            width: 100%;
            line-height: 1.3;
        }}

        .card-desc {{
            color: var(--text-sub);
            font-size: 0.88rem;
            line-height: 1.4;
            margin-bottom: 1.5rem;
            flex-grow: 1;
            text-align: center;
            width: 100%;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .cyan-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: var(--cyan-primary);
            color: #000;
            text-decoration: none;
            padding: 0.6rem 1.2rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 700;
            box-shadow: 0 4px 15px rgba(0, 188, 212, 0.3);
            transition: background-color 0.2s ease, transform 0.1s ease, box-shadow 0.2s ease;
            margin: 0 auto;
            text-align: center;
            width: fit-content;
        }}

        .cyan-btn:hover {{
            background-color: var(--cyan-hover);
            box-shadow: 0 6px 20px rgba(0, 188, 212, 0.5);
            transform: translateY(-1px);
        }}

        /* MEDIA QUERY: Bei kleineren Bildschirmen (Portrait / Smartphones) exakt 2 Spalten */
        @media (max-width: 900px) {{
            .addon-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 1.2rem;
            }}
            main {{
                padding: 1rem;
            }}
        }}
    </style>
</head>
<body>

    <header class="cyan-header">
        <div class="banner-container">
            <img src="{BANNER_URL}" alt="Kodi Media Repo Banner">
        </div>
        <h1>Kodi Media Repo</h1>
        <p style="color: var(--text-sub); margin: 0;">Füge diese Source in Kodi hinzu:</p>
        <div class="repo-url-box">
            <span>https://{REPO_USER}.github.io/{REPO_NAME}/</span>
        </div>
    </header>

    <div class="category-nav">
        <button class="cat-btn active" onclick="filterCategory('all', this)">✨ Alle anzeigen</button>
        <button class="cat-btn" onclick="filterCategory('videos', this)">🎬 Video-Plugins</button>
        <button class="cat-btn" onclick="filterCategory('scripts', this)">📜 Script-Module</button>
        <button class="cat-btn" onclick="sortData('az', this)" id="btn-az">🔤 A - Z (A ↓)</button>
    </div>

    <main>
        <div class="addon-grid" id="cards-grid">
            {all_cards_html}
        </div>
    </main>

    <script>
        let currentFilter = 'all';
        let azAsc = true;

        function filterCategory(category, btn) {{
            currentFilter = category;
            document.querySelectorAll('.cat-btn').forEach(b => {{
                if(!b.id.startsWith('btn-')) b.classList.remove('active');
            }});
            btn.classList.add('active');
            applyView();
        }}

        function sortData(type, btn) {{
            const grid = document.getElementById('cards-grid');
            const cards = Array.from(grid.getElementsByClassName('cyan-card'));

            if (type === 'az') {{
                azAsc = !azAsc;
                btn.innerHTML = azAsc ? '🔤 A - Z (A ↓)' : '🔤 Z - A (Z ↓)';

                cards.sort((a, b) => {{
                    let nameA = a.getAttribute('data-name') || '';
                    let nameB = b.getAttribute('data-name') || '';
                    return azAsc ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA);
                }});
            }}

            cards.forEach(card => grid.appendChild(card));
            applyView();
        }}

        function applyView() {{
            const cards = document.querySelectorAll('.cyan-card');
            cards.forEach(card => {{
                const cat = card.getAttribute('data-category');
                if (currentFilter === 'all' || cat === currentFilter) {{
                    card.style.display = 'flex';
                }} else {{
                    card.style.display = 'none';
                }}
            }});
        }}
    </script>

</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
        
    print("✓ index.html wurde erfolgreich generiert!")

if __name__ == "__main__":
    generate_html()
