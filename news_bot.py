import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configuración completa de tus 6 canales
FEEDS = {
    "ReutersBiz": {
        "url": "https://rsshub.app/reuters/business",
        "chat": "-1003749568108"
    },
    "ReutersChina": {
        "url": "https://rsshub.app/reuters/world/china",
        "chat": "-1003724765047"
    },
    "Bloomberg": {
        "url": "https://rsshub.app/bloomberg/economics",
        "chat": "-1003760302624"
    },
    "WSJ": {
        "url": "https://rsshub.app/wsj/en-us/business",
        "chat": "-1003861476711"
    },
    "FT": {
        "url": "https://rsshub.app/ft/home",
        "chat": "-1003561464477"
    },
    "TheEconomist": {
        "url": "https://www.economist.com/latest/rss.xml",
        "chat": "-1003897620126"
    }
}

def get_last_link(source):
    file = f"sent_{source}.txt"
    if not os.path.exists(file): return set()
    with open(file, "r") as f: return set(line.strip() for line in f.readlines())

def save_sent_links(source, links):
    with open(f"sent_{source}.txt", "w") as f:
        f.write("\n".join(list(links)[-100:]))

def extraer_imagen(entry):
    """Busca la imagen en enclosures o dentro del HTML de la descripción"""
    # 1. Enclosure (Standard RSS como The Economist)
    if 'enclosures' in entry and entry.enclosures:
        return entry.enclosures[0].get('url')
    # 2. Etiqueta <img> en la descripción (Standard RSSHub)
    if 'description' in entry:
        img = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img: return img.group(1)
    return None

def enviar_a_telegram(chat_id, titulo, link, img_url):
    """Descarga la imagen y la sube a Telegram para evitar bloqueos de URL"""
    markup = {"inline_keyboard": [[{"text": "Leer noticia completa ↗️", "url": link}]]}
    
    if img_url:
        try:
            # Bajamos la imagen a la memoria del bot
            resp = requests.get(img_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                bio = BytesIO(resp.content)
                bio.name = 'post.jpg'
                
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                    data={
                        "chat_id": chat_id,
                        "caption": titulo,
                        "reply_markup": json.dumps(markup),
                        "parse_mode": "HTML"
                    },
                    files={"photo": bio}
                )
                return
        except Exception as e:
            print(f"Error con imagen: {e}")

    # Fallback: Solo mensaje de texto si no hay imagen o falla la subida
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={
        "chat_id": chat_id,
        "text": titulo,
        "reply_markup": json.dumps(markup),
        "parse_mode": "HTML"
    })

# --- PROCESO PRINCIPAL ---
for source, data in FEEDS.items():
    print(f"Procesando {source}...")
    feed = feedparser.parse(data["url"])
    sent_links = get_last_link(source)
    
    # Procesamos solo los 5 más recientes para evitar saturar
    for post in reversed(feed.entries[:5]):
        link = post.link.split('?')[0]
        if link in sent_links: continue

        # Limpieza: quitamos el " - Reuters" del final y escapamos HTML
        titulo = html.escape(re.sub(r" - [^-]+$", "", post.title).strip())
        
        imagen = extraer_imagen(post)
        enviar_a_telegram(data["chat"], titulo, link, imagen)
        
        sent_links.add(link)
    
    save_sent_links(source, sent_links)
