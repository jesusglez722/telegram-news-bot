import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

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

# User-Agent de navegador real para saltar bloqueos de Bloomberg/Reuters
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
}

def extraer_url_real(entry):
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def obtener_imagen_real(url_real, entry):
    """Extrae la imagen original de la web o del feed si es The Economist"""
    if "economist.com" in url_real:
        if "media_content" in entry: return entry.media_content[0]["url"]
        return None
    
    try:
        # Entramos en la web para buscar la etiqueta og:image
        r = requests.get(url_real, headers=HEADERS, timeout=10)
        match = re.search(r'property="og:image"\s+content="([^"]+)"', r.text)
        if not match:
            match = re.search(r'content="([^"]+)"\s+property="og:image"', r.text)
        
        if match:
            img_url = match.group(1)
            if "google" in img_url: return None # Ignorar logos de Google
            return img_url
    except:
        pass
    return None

def enviar_telegram(chat_id, texto, img_url):
    """Descarga la imagen y la sube físicamente a Telegram"""
    if img_url:
        try:
            # EL BOT DESCARGA LA IMAGEN
            resp = requests.get(img_url, headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                # LA SUBE COMO ARCHIVO (Multipart/form-data)
                img_data = BytesIO(resp.content)
                img_data.name = 'photo.jpg'
                
                requests.post(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id, "caption": texto, "parse_mode": "HTML"},
                    files={"photo": img_data}
                )
                return
        except Exception as e:
            print(f"Error subiendo imagen: {e}")

    # Si falla la imagen, envía solo texto para no perder la noticia
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
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
            # Título limpio (sin nombre de medio al final)
            titulo = re.sub(r" - [^-]+$", "", entry.title).strip()
            
            # Texto final: Sin negritas de cuenta, link acortado al final
            mensaje = f"<b>{html.escape(titulo)}</b>\n\n<a href='{url}'>Ver artículo completo</a>"
            
            img = obtener_imagen_real(url, entry)
            enviar_telegram(CHATS[source], mensaje, img)
            sent_links.add(url)
            
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-200:]))
