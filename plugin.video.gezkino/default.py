# -*- coding: utf-8 -*-
# IT('s) Possible 
# 2026.10.19
# GEZ-KiNO Addon default.py 
import sys
import urllib.parse
import xbmcgui
import xbmcplugin
import requests
import xbmc
import xbmcaddon
import os
import xbmcvfs
import json
import re
import string

BASE_URL = sys.argv[0]
ADDON_HANDLE = int(sys.argv[1])
ARGS = urllib.parse.parse_qs(sys.argv[2].lstrip('?'))

ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
MEDIA_DIR = os.path.join(ADDON_PATH, "media")

ADDON_DATA_DIR = xbmcvfs.translatePath("special://profile/addon_data/plugin.video.gezkino/")
if not os.path.exists(ADDON_DATA_DIR):
    os.makedirs(ADDON_DATA_DIR)
JSON_PATH = os.path.join(ADDON_DATA_DIR, "movies.json")
GITHUB_JSON_URL = 'https://raw.githubusercontent.com/Chrisophy/GEZ-KiNO/refs/heads/main/movies.json'

def lade_oder_aktualisiere_json(erzwinge_download=False):
    if erzwinge_download or not os.path.exists(JSON_PATH):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(GITHUB_JSON_URL, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    with open(JSON_PATH, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    return data
        except Exception as e:
            xbmc.log(f"[GEZ-Kino] Fehler beim Download der Datenbank: {str(e)}", xbmc.LOGERROR)
    
    if os.path.exists(JSON_PATH):
        try:
            with open(JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            xbmc.log(f"[GEZ-Kino] Fehler beim Lesen der Datenbank: {str(e)}", xbmc.LOGERROR)
    return []

def aktualisiere_datenbank():
    data = lade_oder_aktualisiere_json(erzwinge_download=True)
    if data:
        xbmcgui.Dialog().notification('GEZ Kino', f'Filmliste erfolgreich aktualisiert ({len(data)} Filme)!', xbmcgui.NOTIFICATION_INFO, 3000)
    else:
        xbmcgui.Dialog().notification('GEZ Kino', 'Fehler beim Aktualisieren der Filmliste!', xbmcgui.NOTIFICATION_ERROR, 3000)
    xbmc.executebuiltin('Container.Refresh')

def hole_live_tv_sender():
    iptv_url = "https://raw.githubusercontent.com/jnk22/kodinerds-iptv/master/iptv/clean/clean_tv_main.m3u"
    tv_liste = []
    try:
        r = requests.get(iptv_url, timeout=5)
        if r.status_code == 200:
            lines = r.text.splitlines()
            for i in range(len(lines)):
                if lines[i].startswith("#EXTINF"):
                    logo_match = re.search(r'tvg-logo="([^"]+)"', lines[i])
                    name = lines[i].split(',')[-1].strip()
                    if i + 1 < len(lines) and lines[i + 1].startswith("http"):
                        url = lines[i + 1].strip()
                        tv_liste.append({
                            "title": f"[TV] {name}",
                            "url": url,
                            "desc": "Live-TV Sender",
                            "rating": "LIVE",
                            "thumb": logo_match.group(1) if logo_match else "",
                            "genres": ["Live-TV"],
                            "year": "",
                            "director": "",
                            "actors": []
                        })
    except Exception as e:
        xbmc.log(f"[GEZ-Kino] IPTV Fehler: {e}", xbmc.LOGERROR)
    
    tv_liste.sort(key=lambda x: x['title'].lower())
    return tv_liste

def hole_lokale_filme_aus_json(genre_filter, suchbegriff_suche=None, start_char=None, year_filter=None, rating_range=None):
    if genre_filter == 'Live-TV':
        return hole_live_tv_sender()

    movies = lade_oder_aktualisiere_json()
    if not movies:
        return None
        
    filme_liste = []
    for m in movies:
        title = m.get('title', '')
        url = m.get('video_url', '')
        if not url or not title:
            continue
            
        year = str(m.get('year', ''))
        if year in ['None', 'LIVE', '']:
            year = ''
            
        genres = m.get('genres_list', ['Sonstige'])
        if not genres:
            genres = ['Sonstige']
            
        rating_str = m.get('rating', 'N/A')
        director = m.get('director', '') or ''
        actors = m.get('actors', []) or []
        plot = m.get('plot', '') or 'Keine Beschreibung verfügbar.'
        thumb = m.get('thumb', '')
        if thumb == 'placeholder.png':
            thumb = ''
            
        if suchbegriff_suche:
            sb = suchbegriff_suche.lower()
            actors_combined = " ".join(actors).lower()
            if sb not in title.lower() and sb not in director.lower() and sb not in actors_combined:
                continue
                
        if start_char:
            first_char = title[0].upper()
            if start_char == '#':
                if first_char.isalpha():
                    continue
            else:
                if first_char != start_char:
                    continue
        
        if year_filter:
            if year != year_filter:
                continue
        
        if rating_range is not None:
            try:
                r_val = float(rating_str)
                start_range = float(rating_range)
                if start_range == 9.0:
                    if not (start_range <= r_val <= start_range + 1):
                        continue
                else:
                    if not (start_range <= r_val < start_range + 1):
                        continue
            except:
                continue

        if genre_filter not in ['AZ', 'YEAR', 'RATING']:
            if genre_filter == 'Alle':
                pass
            elif genre_filter == 'Sonstige':
                if genres and genres != ['Sonstige']: 
                    continue
            else:
                if genre_filter not in genres: 
                    continue
        
        filme_liste.append({
            "title": title, "url": url, "desc": plot,
            "rating": rating_str, "thumb": thumb, "genres": genres,
            "year": year, "director": director, "actors": actors
        })
    
    filme_liste.sort(key=lambda x: x['title'].lower())
    return filme_liste

def zeige_hauptmenue():
    p_icon1 = os.path.join(MEDIA_DIR, "icon1.png")
    p_icon2 = os.path.join(MEDIA_DIR, "icon2.png")
    p_icon3 = os.path.join(MEDIA_DIR, "icon3.png")
    p_icon4 = os.path.join(MEDIA_DIR, "icon4.png")
    p_icon5 = os.path.join(MEDIA_DIR, "icon5.png")
    p_icon6 = os.path.join(MEDIA_DIR, "icon6.png")
    p_icon7 = os.path.join(MEDIA_DIR, "icon7.png") 
    
    li1 = xbmcgui.ListItem(label="[ Alle Spielfilme ]")
    li1.setInfo('video', {'title': "Alle Spielfilme", 'plot': "Zeigt die komplette Liste vieler Spielfilme aus den öffentlich-rechtlichen Mediatheken an. Komplett alphabetisch sortiert."})
    li1.setArt({'icon': p_icon1, 'thumb': p_icon1})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=list&query=Alle", listitem=li1, isFolder=True)
    
    li_az = xbmcgui.ListItem(label="[ Filme A-Z ]")
    li_az.setInfo('video', {'title': "Filme A-Z", 'plot': "Durchsuche die Filmliste alphabetisch."})
    li_az.setArt({'icon': p_icon5, 'thumb': p_icon5})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=az_menu", listitem=li_az, isFolder=True)
    
    li_year = xbmcgui.ListItem(label="[ Nach Jahren sortiert ]")
    li_year.setInfo('video', {'title': "Nach Jahren sortiert", 'plot': "Zeigt die Filme nach Produktionsjahren gruppiert an."})
    li_year.setArt({'icon': p_icon6, 'thumb': p_icon6})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=years_menu", listitem=li_year, isFolder=True)

    li_rating = xbmcgui.ListItem(label="[ Nach Bewertung sortiert ]")
    li_rating.setInfo('video', {'title': "Nach Bewertung sortiert", 'plot': "Filme sortiert nach TMDB-Bewertung."})
    li_rating.setArt({'icon': p_icon7, 'thumb': p_icon7})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=rating_menu", listitem=li_rating, isFolder=True)

    li2 = xbmcgui.ListItem(label="[ Nach Genres sortiert ]")
    li2.setInfo('video', {'title': "Nach Genres sortiert", 'plot': "Öffnet das Genre-Menü. Hier kannst du gezielt nach Kategorien wie Krimi, Action, Drama, Komödien oder Dokumentationen suchen."})
    li2.setArt({'icon': p_icon2, 'thumb': p_icon2})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=genres_menu", listitem=li2, isFolder=True)
    
    li3 = xbmcgui.ListItem(label="[ Film / Regie / Cast suchen... ]")
    li3.setInfo('video', {'title': "Suchen", 'plot': "Öffnet eine Tastatur, um die Filmliste gezielt nach Filmtitel, Regisseur oder Schauspielern zu durchsuchen."})
    li3.setArt({'icon': p_icon3, 'thumb': p_icon3})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=search", listitem=li3, isFolder=True)
    
    li4 = xbmcgui.ListItem(label="[ Mediathek aktualisieren ]")
    li4.setInfo('video', {'title': "Filmliste aktualisieren", 'plot': "Lädt die aktuelle Datenbank vom Server herunter."})
    li4.setArt({'icon': p_icon4, 'thumb': p_icon4})
    xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=f"{BASE_URL}?action=sync", listitem=li4, isFolder=False)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def zeige_az_menue():
    addon_icon = os.path.join(MEDIA_DIR, "icon.png")
    buchstaben = ['#'] + list(string.ascii_uppercase)
    for buchstabe in buchstaben:
        url = f"{BASE_URL}?action=list&query=AZ&char={buchstabe}"
        li = xbmcgui.ListItem(label=buchstabe)
        plot = f"Alle Spielfilme, deren Titel mit '{buchstabe}' beginnt." if buchstabe != '#' else "Alle Spielfilme, deren Titel mit einer Zahl oder einem Sonderzeichen beginnt."
        li.setInfo('video', {'title': f"Filme mit {buchstabe}", 'plot': plot})
        if os.path.exists(addon_icon):
            li.setArt({'icon': addon_icon, 'thumb': addon_icon})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def zeige_jahre_menue():
    addon_icon = os.path.join(MEDIA_DIR, "icon.png")
    jahre = set()
    movies = lade_oder_aktualisiere_json()
    for m in movies:
        y = str(m.get('year', ''))
        if y and y.isdigit() and len(y) == 4:
            jahre.add(y)
    jahre_liste = sorted(list(jahre), reverse=True)

    if not jahre_liste:
        li = xbmcgui.ListItem(label="Keine Jahresdaten gefunden. Bitte aktualisieren.")
        li.setInfo('video', {'plot': "Es wurden noch keine Jahresdaten in der lokalen Datenbank gefunden."})
        if os.path.exists(addon_icon):
            li.setArt({'icon': addon_icon, 'thumb': addon_icon})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url="", listitem=li, isFolder=False)
    else:
        for jahr in jahre_liste:
            url = f"{BASE_URL}?action=list&query=YEAR&year={jahr}"
            li = xbmcgui.ListItem(label=f"Jahr {jahr}")
            plot = f"Entdecke alle Spielfilme und Produktionen aus dem Jahr {jahr}."
            li.setInfo('video', {'title': f"Jahr {jahr}", 'plot': plot})
            if os.path.exists(addon_icon):
                li.setArt({'icon': addon_icon, 'thumb': addon_icon})
            xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
            
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def zeige_rating_menue():
    addon_icon = os.path.join(MEDIA_DIR, "icon.png")
    for i in range(10):
        label = f"Bewertung {i}-{i+1}"
        url = f"{BASE_URL}?action=list&query=RATING&range={i}"
        li = xbmcgui.ListItem(label=label)
        plot = f"Filme mit einer TMDB-Bewertung im Bereich von {i} bis {i+1} Sternen."
        li.setInfo('video', {'title': label, 'plot': plot})
        if os.path.exists(addon_icon):
            li.setArt({'icon': addon_icon, 'thumb': addon_icon})
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def zeige_genre_menue():
    genres = [
        ("Live-TV", "Live-TV"), ("Action", "Action"),
        ("Abenteuer", "Abenteuer"), ("Animation", "Animation"), ("Komödien", "Komödie"),
        ("Krimi", "Krimi"), ("Dokumentationen", "Doku"), ("Dramen", "Drama"),
        ("Familie", "Familie"), ("Fantasy", "Fantasy"), ("Historie", "Historie"),
        ("Horror", "Horror"), ("Musik", "Musik"), ("Mystery", "Mystery"),
        ("Liebesfilme und Romantik", "Romanze"), ("Science Fiction", "Sci-Fi"),
        ("TV-Film", "TV-Film"), ("Thriller", "Thriller"), ("Krieg", "Krieg"),
        ("Western", "Western"), ("Sonstige (Unkategorisiert)", "Sonstige")
    ]
    
    genre_plots = {
        "Live-TV": "Aktuelles Fernsehprogramm rund um die Uhr.",
        "Action": "Hier knallt es richtig. Nichts für schwache Nerven.",
        "Abenteuer": "Ferne Welten, verborgene Schätze und epische Reisen.",
        "Animation": "Kunstvolle Welten, die durch Farbe und Bewegung zum Leben erweckt werden.",
        "Komödie": "Lachen garantiert. Die besten Komödien und Satiren.",
        "Krimi": "Spannende Ermittlungen, rätselhafte Fälle und eiskalte Täter.",
        "Doku": "Faszinierende Einblicke in Natur, Geschichte und Gesellschaft.",
        "Drama": "Gefühlvolle Geschichten, tiefe Charaktere und bewegende Schicksale.",
        "Familie": "Unterhaltung für Groß und Klein. Gemeinsam schauen und genießen.",
        "Fantasy": "Magische Reiche, sagenhafte Kreaturen und unmögliche Abenteuer.",
        "Historie": "Eintauchen in vergangene Zeiten und bedeutende Ereignisse der Geschichte.",
        "Horror": "Nervenkitzel pur. Dunkle Mächte und schreckliche Monster.",
        "Musik": "Die Welt der Klänge, Konzerte und Musicals.",
        "Mystery": "Unerklärliche Phänomene, rätselhafte Ereignisse und dunkle Geheimnisse.",
        "Romanze": "Herzerwärmende Romanzen, große Gefühle und wahre Liebe.",
        "Sci-Fi": "Zukunftsgeschichten, fremde Planeten und revolutionäre Technik.",
        "TV-Film": "Die besten Fernsehfilme aus den Mediatheken.",
        "Thriller": "Atemlose Spannung, psychologische Spiele und unerwartete Wendungen.",
        "Krieg": "Realistische Darstellungen historischer Konflikte und Schicksale.",
        "Western": "Reitende Helden, weite Prärien und Duelle im Morgengrauen.",
        "Sonstige": "Filme, die in keine andere Schublade passen."
    }
    
    for label, internal_name in genres:
        url = f"{BASE_URL}?action=list&query={urllib.parse.quote_plus(internal_name)}"
        
        icon_filename = f"{label.lower()}.png"
        icon_path = os.path.join(MEDIA_DIR, icon_filename)
        
        li = xbmcgui.ListItem(label=label)

        plot = genre_plots.get(internal_name, 'Keine Beschreibung verfügbar.')
        li.setInfo('video', {'plot': plot})
        
        if os.path.exists(icon_path):
            li.setArt({'icon': icon_path, 'thumb': icon_path})
            
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=url, listitem=li, isFolder=True)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

def zeige_filmliste(genre_query, search_str=None, start_char=None, year_filter=None, rating_range=None):
    xbmcplugin.setContent(ADDON_HANDLE, 'movies')
    filme = hole_lokale_filme_aus_json(genre_query, suchbegriff_suche=search_str, start_char=start_char, year_filter=year_filter, rating_range=rating_range)
    if filme is None:
        if xbmcgui.Dialog().yesno("Filmliste leer", "Die lokale Filmliste ist leer. Jetzt herunterladen?"):
            data = lade_oder_aktualisiere_json(erzwinge_download=True)
            filme = hole_lokale_filme_aus_json(genre_query, suchbegriff_suche=search_str, start_char=start_char, year_filter=year_filter, rating_range=rating_range)
        else:
            filme = []
    if not filme:
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url="", listitem=xbmcgui.ListItem(label="Keine Einträge gefunden."), isFolder=False)
        xbmcplugin.endOfDirectory(ADDON_HANDLE)
        return
    for film in filme:
        display_label = film['title']
        if film['year']:
            display_label += f" ({film['year']})"
        if film['rating'] and film['rating'] not in ['N/A', 'LIVE']:
            display_label += f" [★ {film['rating']}]"
        
        meta_plot = ""
        if film.get('director'):
            meta_plot += f"Regie: {film['director']}\n"
        if film.get('actors'):
            meta_plot += f"Cast: {', '.join(film['actors'])}\n"
        if meta_plot:
            meta_plot += "--------------------------------------------------------\n"
        meta_plot += film['desc']
            
        li = xbmcgui.ListItem(label=display_label)
        
        try:
            video_info = li.getVideoInfoTag()
            
            try: video_info.setTitle(film['title'])
            except: pass
            
            try: video_info.setPlot(meta_plot)
            except: pass
            
            try: 
                if film['genres']: video_info.setGenres(film['genres'])
            except: pass
            
            try:
                if film['year'] and film['year'].isdigit():
                    video_info.setPremiered(f"{film['year']}-01-01")
            except: pass
            
            try:
                if film['rating'] and film['rating'] not in ['N/A', 'LIVE']:
                    video_info.setRating(float(film['rating']))
            except: pass
            
            try:
                if film.get('director'):
                    video_info.setDirectors([film['director']])
            except: pass
            
            try:
                if film.get('actors'):
                    cast_objects = []
                    for actor in film['actors']:
                        try: cast_objects.append(xbmcgui.ListItemCastAndRole(name=actor, role=""))
                        except: pass
                    if cast_objects:
                        video_info.setCast(cast_objects)
            except: pass
        except:
            info_dict = {
                'title': film['title'], 
                'plot': meta_plot,
                'genre': ", ".join(film['genres']),
                'year': int(film['year']) if film['year'] and film['year'].isdigit() else 0,
                'rating': float(film['rating']) if film['rating'] not in ['N/A', 'LIVE'] else 0.0,
                'director': film.get('director', ''),
                'cast': film.get('actors', [])
            }
            li.setInfo('video', info_dict)
            
        art_dict = {}
        if film['thumb']:
            art_dict['poster'] = film['thumb']
            art_dict['thumb'] = film['thumb']
            art_dict['icon'] = film['thumb']
            art_dict['fanart'] = film['thumb']
        li.setArt(art_dict)
        li.setProperty('IsPlayable', 'true')
        xbmcplugin.addDirectoryItem(handle=ADDON_HANDLE, url=film['url'], listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(ADDON_HANDLE)

action = ARGS.get('action', [None])[0]
query = ARGS.get('query', [None])[0]
char = ARGS.get('char', [None])[0]
year_param = ARGS.get('year', [None])[0]
range_param = ARGS.get('range', [None])[0]

if action == 'list' and query == 'AZ':
    zeige_filmliste('AZ', start_char=char)
elif action == 'list' and query == 'YEAR':
    zeige_filmliste('YEAR', year_filter=year_param)
elif action == 'list' and query == 'RATING':
    zeige_filmliste('RATING', rating_range=range_param)
elif action == 'list' and query:
    zeige_filmliste(query)
elif action == 'az_menu':
    zeige_az_menue()
elif action == 'years_menu':
    zeige_jahre_menue()
elif action == 'rating_menu':
    zeige_rating_menue()
elif action == 'genres_menu':
    zeige_genre_menue()
elif action == 'sync':
    aktualisiere_datenbank()
elif action == 'search':
    kb = xbmc.Keyboard('', 'Film, Regie oder Schauspieler suchen...')
    kb.doModal()
    if kb.isConfirmed() and kb.getText():
        zeige_filmliste('Alle', search_str=kb.getText())
else:
    zeige_hauptmenue()
