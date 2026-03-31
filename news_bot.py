import feedparser
import requests
import os
import re
import json
import html
import hashlib

BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/business&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003749568108", "emoji": "🟠"
    },
    "ReutersChina": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/world/china&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003724765047", "emoji": "🟠"
    },
    "business": {
        "url": "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003760302624", "emoji": "🟡"
    },
    "WSJ": {
        "url": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003861476711", "emoji": "⚪"
    },
    "FT": {
        "url": "https://news.google.com/rss/search?q=site:ft.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003561464477", "emoji": "🟤"
    },
    "TheEconomist": {
        "url": "https://www.economist.com/latest/rss.xml",
        "chat": "-1003897620126", "emoji": "🔴"
    }
}

MAX_HISTORY = 500
MAX_POSTS_PER_RUN = 5

def limpiar_html(texto):
    limpio = re.sub("<.*?>", "", texto)
    limpio = re.sub(r" - [^-]+$", "", limpio)
    return limpio.strip()

def extraer_url_real_google(entry):
    if "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0].split('#')[0].lower()
    return entry.link.split('?')[0].lower()

def obtener_imagen_robusta(entry, url_real):
    # TRUCO: Google News oculta una miniatura en el 'summary'
    if "summary" in entry:
        img_match = re.search(r'<img src="([^"]+)"', entry.summary)
        if img_match:
            img_url = img_match.group(1)
            # Evitamos el logo de Google News
            if "lh3.googleusercontent.com" in img_url or "google" not in img_url.lower():
                return img_url

    # Fallback para The Economist o si el anterior falla
    if "media_content" in entry:
        return entry.media_content[0]["url"]
    
    return None

def load_sent_links(source):
    file = f"sent_{source}.txt"
    if not os.path.exists(file): return set()
    with open(file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_sent_links(source, links_set):
    file = f"sent_{source}.txt"
    links = list(links_set)[-MAX_HISTORY:]
    with open(file, "w", encoding="utf-8") as f:
        f.write("\n".join(links))

def send_to_telegram(chat_id, caption, image=None):
    if image:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False}
    
    r = requests.post(url, data=payload)
    print(f"Status Telegram: {r.status_code}")

# --- MAIN ---
for source, data in FEEDS.items():
    print(f"Checking {source}...")
    feed = feedparser.parse(data["url"])
    sent_hashes = load_sent_links(source)
    nuevos = []

    for entry in feed.entries:
        url_real = extraer_url_real_google(entry)
        titulo_limpio = limpiar_html(entry.title)
        
        # SOLUCIÓN WSJ: Usamos un hash del título + URL para evitar repetidos
        # A veces cambian la URL pero el título es idéntico
        post_id = hashlib.md_id = hashlib.md5(f"{titulo_limpio}{url_real}".encode()).hexdigest()

        if post_id in sent_hashes:
            continue

        entry.final_link = url_real
        entry.post_id = post_id
        nuevos.append(entry)
        sent_hashes.add(post_id)

    nuevos = nuevos[:MAX_POSTS_PER_RUN]

    for post in reversed(nuevos):
        titulo = limpiar_html(post.title)
        link = post.final_link
        imagen = obtener_imagen_robusta(post, link)

        caption = f"<b>{data['emoji']} {source.upper()}</b>\n\n{titulo}\n\n<a href='{link}'>📰 Leer noticia</a>"
        send_to_telegram(data["chat"], caption, imagen)

    save_sent_links(source, sent_hashes)
