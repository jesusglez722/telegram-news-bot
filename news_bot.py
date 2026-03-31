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

# User-Agent de alta calidad para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
}

def limpiar_titulo(titulo):
    limpio = re.sub(r" - [^-]+$", "", titulo).strip()
    return html.escape(limpio)

def extraer_url_real(entry):
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def obtener_imagen(entry, url_real):
    # 1. Caso The Economist
    if "economist.com" in url_real:
        if "media_content" in entry: return entry.media_content[0]["url"]
        if "description" in entry:
            match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
            if match: return match.group(1)

    # 2. Scrapeo robusto para el resto
    try:
        # Primero obtenemos la página real (manejando redirecciones)
        r = requests.get(url_real, headers=HEADERS, timeout=12, allow_redirects=True)
        if r.status_code != 200: return None
        
        # Buscamos la imagen en el HTML con varios patrones
        patterns = [
            r'property="og:image"\s+content="([^"]+)"',
            r'content="([^"]+)"\s+property="og:image"',
            r'name="twitter:image"\s+content="([^"]+)"'
        ]
        for p in patterns:
            match = re.search(p, r.text)
            if match:
                img_url = match.group(1)
                # Si la imagen es un logo o algo de Google News, la ignoramos
                if "google" in img_url.lower() and "news" in img_url.lower(): continue
                return img_url
    except:
        pass
    return None

def enviar_telegram(chat_id, texto, link, img_url):
    markup = {"inline_keyboard": [[{"text": "Leer noticia completa ↗️", "url": link}]]}
    
    if img_url:
        try:
            # Descarga directa para que Telegram no tenga que pedir la foto a la web bloqueada
            img_res = requests.get(img_url, headers=HEADERS, timeout=10)
            if img_res.status_code == 200:
                bio = BytesIO(img_res.content)
                bio.name = 'news.jpg'
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                    data={"chat_id": chat_id, "caption": texto, "reply_markup": json.dumps(markup), "parse_mode": "HTML"},
                    files={"photo": bio})
                return
        except:
            pass

    # Fallback a mensaje de texto
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": chat_id, "text": texto, "reply_markup": json.dumps(markup), "parse_mode": "HTML"
    })

# --- PROCESO ---
for source, feed_url in FEEDS.items():
    print(f"Checking {source}...")
    feed = feedparser.parse(feed_url)
    
    file_hist = f"sent_{source}.txt"
    sent_links = set()
    if os.path.exists(file_hist):
        with open(file_hist, "r") as f: sent_links = set(line.strip() for line in f.readlines())

    nuevos = []
    # Usamos un set temporal para evitar duplicados dentro de la misma iteración (problema WSJ)
    urls_vistas = set()

    for entry in feed.entries[:15]:
        url_real = extraer_url_real(entry).lower()
        if url_real not in sent_links and url_real not in urls_vistas:
            nuevos.append((entry, url_real))
            urls_vistas.add(url_real)

    if nuevos:
        nuevos.reverse()
        for entry, url in nuevos[:5]: # Máximo 5 por vez
            titulo = limpiar_titulo(entry.title)
            imagen = obtener_imagen(entry, url)
            enviar_telegram(CHATS[source], titulo, url, imagen)
            sent_links.add(url)
            
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-300:]))
