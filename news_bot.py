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

# IDs de los canales
CHATS = {
    "ReutersBiz": "-1003749568108",
    "ReutersChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def limpiar_titulo(titulo):
    # Quita el nombre del medio al final (ej: " - Reuters")
    limpio = re.sub(r" - [^-]+$", "", titulo).strip()
    return html.escape(limpio)

def extraer_url_real(entry):
    # Si es de Google News, buscamos el link real en el summary
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def obtener_imagen(entry, url_real):
    # 1. Caso especial The Economist (vía RSS)
    if "economist.com" in url_real and "media_content" in entry:
        return entry.media_content[0]["url"]
    
    # 2. Resto de medios: Scrapeamos la etiqueta og:image de la web real
    try:
        r = requests.get(url_real, headers=HEADERS, timeout=10)
        match = re.search(r'property="og:image"\s+content="([^"]+)"', r.text)
        if not match:
            match = re.search(r'content="([^"]+)"\s+property="og:image"', r.text)
        if match: return match.group(1)
    except:
        pass
    return None

def enviar_telegram(chat_id, texto, link, img_url):
    markup = {"inline_keyboard": [[{"text": "Leer noticia completa ↗️", "url": link}]]}
    
    if img_url:
        try:
            # Descarga de imagen para evitar bloqueos de Telegram
            img_data = requests.get(img_url, headers=HEADERS, timeout=15).content
            bio = BytesIO(img_data)
            bio.name = 'foto.jpg'
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            requests.post(url, data={
                "chat_id": chat_id,
                "caption": texto,
                "reply_markup": json.dumps(markup),
                "parse_mode": "HTML"
            }, files={"photo": bio})
            return
        except:
            pass

    # Si falla la imagen, mandamos texto
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": texto,
        "reply_markup": json.dumps(markup),
        "parse_mode": "HTML"
    })

# --- PROCESO ---
for source, feed_url in FEEDS.items():
    print(f"Procesando {source}...")
    feed = feedparser.parse(feed_url)
    
    # Cargamos historial
    file_hist = f"sent_{source}.txt"
    sent_links = set()
    if os.path.exists(file_hist):
        with open(file_hist, "r") as f: sent_links = set(line.strip() for line in f.readlines())

    nuevos = []
    for entry in feed.entries[:10]:
        url_real = extraer_url_real(entry)
        if url_real not in sent_links:
            nuevos.append((entry, url_real))

    if nuevos:
        nuevos.reverse()
        for entry, url in nuevos:
            titulo = limpiar_titulo(entry.title)
            imagen = obtener_imagen(entry, url)
            enviar_telegram(CHATS[source], titulo, url, imagen)
            sent_links.add(url)
            
        # Guardamos historial (limitado a 100)
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-100:]))
