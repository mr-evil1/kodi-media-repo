import os
import xml.etree.ElementTree as ET
import re
import hashlib
from PIL import Image, ImageDraw, ImageFont

# Konfiguration für dein Repository
REPO_USER = "mr-evil1"
REPO_NAME = "kodi-media-repo"
GENERATED_DIR = "_generated_assets"

def clean_kodi_text(text):
    """Wandelt Kodi-BBCodes ([COLOR], [B], [CR]) in valides HTML um"""
    if not text:
        return ""
    
    # 1. [COLOR ffaabbcc]Text[/COLOR] zu <span style="color: #aabbcc;">Text</span>
    text = re.sub(r'\[COLOR\s*[0-9a-fA-F]{2}([0-9a-fA-F]{6})\](.*?)\[/COLOR\]', r'<span style="color: #\1;">\2</span>', text, flags=re.IGNORECASE)
    text = re.sub(r'\[COLOR\s*([0-9a-fA-F]{6})\](.*?)\[/COLOR\]', r'<span style="color: #\1;">\2</span>', text, flags=re.IGNORECASE)
    
    # 2. Weitere Standard-Kodi-Tags
    text = re.sub(r'\[B\](.*?)\[/B\]', r'<strong>\1</strong>', text, flags=re.IGNORECASE)
    text = re.sub(r'\[I\](.*?)\[/I\]', r'<em>\1</em>', text, flags=re.IGNORECASE)
    
    # Zeilenumbrüche [CR] durch HTML <br> ersetzen
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

def generate_fanart(addon_id, name):
    out_dir = os.path.join(GENERATED_DIR, addon_id)
    out_path = os.path.join(out_dir, "fanart.jpg")
    if os.path.exists(out_path):
        return out_path

    os.makedirs(out_dir, exist_ok=True)
    color = get_color_for_id(addon_id)
    darker = tuple(max(c - 70, 0) for c in color)
    img = Image.new("RGB", (1280, 720), darker)
    draw = ImageDraw.Draw(img)

    for x in range(0, 1280, 2):
        ratio = x / 1280
        blended = tuple(int(darker[i] + (color[i] - darker[i]) * ratio) for i in range(3))
        draw.line([(x, 0), (x, 720)], fill=blended)

    display_name = name or addon_id
    font = get_font(60)
    bbox = draw.textbbox((0, 0), display_name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(((1280 - text_w) / 2 - bbox[0], (720 - text_h) / 2 - bbox[1]), display_name, font=font, fill=(255, 255, 255))

    img.save(out_path, quality=85)
    return out_path

def generate_html():
    if not os.path.exists("addons.xml"):
        print("Fehler: Keine addons.xml im Verzeichnis gefunden!")
        return

    tree = ET.parse("addons.xml")
    root = tree.getroot()
    
    addon_cards_html = ""

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
            sum_elem = metadata.find("./summary[@lang='de']") or metadata.find("./summary")
            desc_elem = metadata.find("./description[@lang='de']") or metadata.find("./description")
            
            if sum_elem is not None: summary = sum_elem.text
            if desc_elem is not None: description = desc_elem.text

        final_desc = description or summary or "Keine Beschreibung verfügbar."
        
        final_desc = clean_kodi_text(final_desc)
        clean_name = clean_kodi_text(name)

        icon_path = None
        fanart_path = None

        assets = addon.find(".//extension[@point='xbmc.addon.metadata']/assets")
        if assets is not None:
            icon_elem = assets.find("icon")
            fanart_elem = assets.find("fanart")
            if icon_elem is not None and icon_elem.text:
                icon_path = icon_elem.text.strip()
            if fanart_elem is not None and fanart_elem.text:
                fanart_path = fanart_elem.text.strip()

        icon_url = find_asset(addon_id, icon_path, "icon.png")
        if icon_url is None:
            local_path = generate_icon(addon_id, name).replace("\\", "/")
            icon_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/refs/heads/main/{local_path}"

        fanart_url = find_asset(addon_id, fanart_path, ["fanart.png", "fanart.jpg", "fanart.jpeg"])
        if fanart_url is None:
            local_path = generate_fanart(addon_id, name).replace("\\", "/")
            fanart_url = f"https://raw.githubusercontent.com/{REPO_USER}/{REPO_NAME}/refs/heads/main/{local_path}"

        # KORRIGIERTER ZIP-PFAD (Direkt im Addon-Ordner via refs/heads/main)
        zip_url = f"https://github.com/{REPO_USER}/{REPO_NAME}/raw/refs/heads/main/{addon_id}/{addon_id}-{version}.zip"

        addon_cards_html += f"""
            <div class="mac-window">
                <div class="window-header">
                    <div class="traffic-lights">
                        <div class="dot red"></div>
                        <div class="dot yellow"></div>
                        <div class="dot green"></div>
                    </div>
                    <div class="window-title">{addon_id} v{version}</div>
                </div>
                
                <div class="addon-gallery">
                    <img src="{fanart_url}" alt="Fanart">
                    <img src="{icon_url}" alt="Icon" style="object-fit: contain; background: rgba(0,0,0,0.4); padding: 10px;">
                </div>

                <div class="window-content">
                    <h2 class="addon-name">{clean_name}</h2>
                    <p class="addon-desc">{final_desc}</p>
                    <a href="{zip_url}" class="mac-btn">Download ZIP (v{version})</a>
                </div>
            </div>
        """

    full_html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kodi Media Repo</title>
    <style>
        :root {{
            --mac-bg: radial-gradient(circle at 0% 0%, #3b2d54, transparent 55%), 
                      radial-gradient(circle at 100% 0%, #1d3d54, transparent 55%), 
                      #0f111a;
            --glass-bg: rgba(255, 255, 255, 0.06);
            --glass-border: rgba(255, 255, 255, 0.1);
            --text-main: #ffffff;
            --text-sub: #a0aec0;
            --apple-blue: #007aff;
            --apple-blue-hover: #1485ff;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: var(--mac-bg);
            background-attachment: fixed;
            color: var(--text-main);
            margin: 0;
            padding: 0;
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
        }}

        .mac-menu-bar {{
            background: rgba(15, 17, 26, 0.75);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 0.4rem 2rem;
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            font-weight: 500;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
        }}

        .menu-left span {{ margin-right: 1.5rem; cursor: default; }}
        .menu-left .apple-logo {{ font-size: 1rem; }}

        header {{ text-align: center; padding: 7rem 1rem 3rem 1rem; }}
        header h1 {{
            font-size: 2.8rem;
            font-weight: 700;
            letter-spacing: -0.05rem;
            margin: 0 0 0.5rem 0;
            background: linear-gradient(180deg, #fff 0%, #a5a5a5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .repo-url-box {{
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--glass-border);
            padding: 0.6rem 1.2rem;
            border-radius: 20px;
            display: inline-flex;
            align-items: center;
            font-family: monospace;
            font-size: 0.95rem;
            color: #34c759;
            margin-top: 1rem;
        }}

        main {{ max-width: 1100px; margin: 0 auto; padding: 2rem 1rem 6rem 1rem; }}
        .addon-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 2.5rem; }}

        .mac-window {{
            background: var(--glass-bg);
            backdrop-filter: blur(30px);
            -webkit-backdrop-filter: blur(30px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.3s ease;
        }}

        .mac-window:hover {{ transform: scale(1.02); box-shadow: 0 35px 60px -10px rgba(0, 0, 0, 0.7); }}
        .window-header {{ background: rgba(0, 0, 0, 0.2); padding: 0.8rem 1rem; display: flex; align-items: center; position: relative; border-bottom: 1px solid rgba(255, 255, 255, 0.05); }}
        .traffic-lights {{ display: flex; gap: 8px; }}
        .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
        .dot.red {{ background: #ff5f56; }}
        .dot.yellow {{ background: #ffbd2e; }}
        .dot.green {{ background: #27c93f; }}
        .window-title {{ position: absolute; left: 50%; transform: translateX(-50%); font-size: 0.85rem; font-weight: 600; color: var(--text-sub); letter-spacing: 0.02rem; }}

        .addon-gallery {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2px; background: rgba(0,0,0,0.2); height: 200px; }}
        .addon-gallery img {{ width: 100%; height: 100%; object-fit: cover; }}

        .window-content {{ padding: 1.5rem; display: flex; flex-direction: column; flex-grow: 1; }}
        .addon-name {{ margin: 0 0 0.75rem 0; font-size: 1.6rem; font-weight: 600; letter-spacing: -0.02rem; }}
        .addon-desc {{ color: var(--text-sub); font-size: 0.95rem; line-height: 1.5; margin-bottom: 2rem; flex-grow: 1; }}

        .mac-btn {{
            display: inline-block;
            text-align: center;
            background: var(--apple-blue);
            color: white;
            text-decoration: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            transition: background 0.15s ease, transform 0.1s ease;
            align-self: flex-start;
        }}
        .mac-btn:hover {{ background: var(--apple-blue-hover); }}
        .mac-btn:active {{ transform: scale(0.98); }}

        @media (max-width: 600px) {{
            .addon-grid {{ grid-template-columns: 1fr; }}
            .mac-menu-bar {{ display: none; }}
            header {{ padding-top: 3rem; }}
        }}
    </style>
</head>
<body>

    <div class="mac-menu-bar">
        <div class="menu-left">
            <span class="apple-logo"></span>
            <strong>Finder</strong>
            <span>Ablage</span>
            <span>Bearbeiten</span>
            <span>Addons</span>
        </div>
        <div class="menu-right">
            <span>Repo OS v1.4</span>
        </div>
    </div>

    <header>
        <h1>Kodi Media Repo</h1>
        <p style="color: var(--text-sub); margin-bottom: 0.5rem;">Füge diese Source in Kodi hinzu:</p>
        <div class="repo-url-box">
            <span>https://{REPO_USER}.github.io/{REPO_NAME}/</span>
        </div>
    </header>

    <main>
        <div class="addon-grid">
            {addon_cards_html}
        </div>
    </main>

</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(full_html)
        
    print("✓ index.html wurde erfolgreich mit den korrekten ZIP-Download-Links generiert!")

if __name__ == "__main__":
    generate_html()
