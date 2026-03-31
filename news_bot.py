import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

# Configuración
BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": "https://news.google.com/rss/search?q=site:reuters.com/business&hl=en-US&gl=US&ceid=US:en",
    "ReutersChina": "https://news.google.com/rss/search?q=site:reuters.com/world/china&hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
    "WSJ": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
    "FT": "https://news.google.com/rss/search?q=site:ft.com&hl=en-US&gl=US&ceid=US:en",
    "TheEconomist": "https://www.economist.com/latest/rss.xml"
}

CHATS = {
    "ReutersBiz": "-1003749568108",
    "ReutersChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# User-Agent para que los medios no nos bloqueen al pedir la foto
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}

def extraer_url_real(entry):
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def obtener_url_imagen(entry, url_real):
    """Busca la URL de la foto real del artículo"""
    # Para The Economist, la sacamos del feed
    if "economist.com" in url_real:
        if "media_content" in entry: return entry.media_content[0]["url"]
        if "description" in entry:
            m = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
            if m: return m.group(1)
    
    # Para el resto, entramos en la web para buscar la imagen de portada
    try:
        r = requests.get(url_real, headers=HEADERS, timeout=10)
        # Buscamos la etiqueta og:image (la foto oficial de la noticia)
        m = re.search(r'property="og:image" content="([^"]+)"', r.text)
        if not m: m = re.search(r'content="([^"]+)" property="og:image"', r.text)
        
        if m:
            img_url = m.group(1)
            # Si el link es del logo de Google News, lo ignoramos
            if "googleusercontent.com" in img_url or "google.com" in img_url: return None
            return img_url
    except:
        pass
    return None

def enviar_telegram(chat_id, texto, img_url):
    """Envía la noticia descargando la imagen para evitar bloqueos"""
    
    if img_url:
        try:
            # EL TRUCO: El bot descarga la foto y se la 'sube' a Telegram
            img_data = requests.get(img_url, headers=HEADERS, timeout=15).content
            img_file = BytesIO(img_data)
            img_file.name = 'noticia.jpg'
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                data={"chat_id": chat_id, "caption": texto, "parse_mode": "HTML"},
                files={"photo": img_file}
            )
            return
        except:
            pass

    # Si no hay imagen o falla la subida, solo texto
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
        data={"chat_id": chat_id, "text": texto, "parse_mode": "HTML", "disable_web_page_preview": False}
    )

# --- PROCESO ---
for source, feed_url in FEEDS.items():
    feed = feedparser.parse(feed_url)
    file_hist = f"sent_{source}.txt"
    sent_links = set()
    if os.path.exists(file_hist):
        with open(file_hist, "r") as f: sent_links = set(line.strip() for line in f.readlines())

    nuevos = []
    for entry in feed.entries[:10]:
        url = extraer_url_real(entry).lower()
        if url not in sent_links:
            nuevos.append((entry, url))

    if nuevos:
        nuevos.reverse()
        for entry, url in nuevos[:3]:
            # Título limpio sin el nombre del medio
            titulo = re.sub(r" - [^-]+$", "", entry.title).strip()
            # Mensaje con link acortado (hipervínculo)
            mensaje = f"{html.escape(titulo)}\n\n<a href='{url}'>Ver artículo completo</a>"
            
            img = obtener_url_imagen(entry, url)
            enviar_telegram(CHATS[source], mensaje, img)
            sent_links.add(url)
            
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-200:]))
