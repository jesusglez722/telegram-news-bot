import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com&ceid=US:en&hl=en-US&gl=US",
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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'}

def extraer_url_real(entry):
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def obtener_imagen(url_real, entry):
    """Busca la foto original usando un puente para evitar el bloqueo de Bloomberg/Reuters"""
    if "economist.com" in url_real:
        if "media_content" in entry: return entry.media_content[0]["url"]
        return None
    
    try:
        # Intentamos obtener el HTML de la noticia
        r = requests.get(url_real, headers=HEADERS, timeout=10)
        m = re.search(r'property="og:image" content="([^"]+)"', r.text)
        if not m: m = re.search(r'content="([^"]+)" property="og:image"', r.text)
        
        if m:
            img_url = m.group(1)
            # Si es una imagen de Google, la ignoramos para no mandar el logo
            if "google" in img_url: return None
            return img_url
    except:
        pass
    return None

def enviar_telegram(chat_id, texto, img_url):
    """Descarga la imagen a través de un puente (wsrv.nl) y la sube a Telegram"""
    if img_url:
        try:
            # USAMOS UN PUENTE (wsrv.nl) para que Bloomberg no bloquee la descarga del bot
            puente_url = f"https://wsrv.nl/?url={img_url}"
            img_data = requests.get(puente_url, timeout=15).content
            img_file = BytesIO(img_data)
            img_file.name = 'news.jpg'
            
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                data={"chat_id": chat_id, "caption": texto, "parse_mode": "HTML"},
                files={"photo": img_file}
            )
            return
        except:
            pass

    # Si falla la foto, mandamos el texto con la previsualización de enlace normal
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
            titulo = re.sub(r" - [^-]+$", "", entry.title).strip()
            # DISEÑO: Sin negritas de cuenta y link acortado en el texto
            mensaje = f"{html.escape(titulo)}\n\n<a href='{url}'>Ver artículo completo</a>"
            
            img = obtener_imagen(url, entry)
            enviar_telegram(CHATS[source], mensaje, img)
            sent_links.add(url)
            
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-200:]))
