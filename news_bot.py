import feedparser
import requests
import os
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/business&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003749568108",
        "emoji": "🟠"
    },
    "ReutersChina": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/world/china&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003724765047",
        "emoji": "🟠"
    },
    "business": {
        "url": "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003760302624",
        "emoji": "🟡"
    },
    "WSJ": {
        "url": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003861476711",
        "emoji": "⚪"
    },
    "FT": {
        "url": "https://news.google.com/rss/search?q=site:ft.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003561464477",
        "emoji": "🟤"
    },
    "TheEconomist": {
        "url": "https://www.economist.com/latest/rss.xml",
        "chat": "-1003897620126",
        "emoji": "🔴"
    }
}

MAX_HISTORY = 300
MAX_POSTS_PER_RUN = 5

# ─────────────────────────────
# LIMPIEZA TEXTO / URL
# ─────────────────────────────

def limpiar_html(texto):
    limpio = re.sub("<.*?>", "", texto)
    return limpio.strip()

def limpiar_url_google(link):
    return link.split("?")[0]

def obtener_imagen(entry):
    if "media_content" in entry:
        return entry.media_content[0]["url"]
    if "links" in entry:
        for l in entry.links:
            if "image" in l.type:
                return l.href
    return None

# ─────────────────────────────
# SISTEMA NUEVO ANTI DUPLICADOS
# ─────────────────────────────

def load_sent_links(source):
    file = f"sent_{source}.txt"
    if not os.path.exists(file):
        return set()
    with open(file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_sent_links(source, links_set):
    file = f"sent_{source}.txt"
    links = list(links_set)[-MAX_HISTORY:]
    with open(file, "w", encoding="utf-8") as f:
        f.write("\n".join(links))

# ─────────────────────────────
# TELEGRAM
# ─────────────────────────────

def send_photo(chat_id, caption, photo):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML"
        }
    )

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
    )

# ─────────────────────────────
# MAIN LOOP
# ─────────────────────────────

for source, data in FEEDS.items():
    print(f"Checking {source}...")
    feed = feedparser.parse(data["url"])
    sent_links = load_sent_links(source)

    nuevos = []

    for entry in feed.entries:
        link = limpiar_url_google(entry.link)

        if link in sent_links:
            continue

        nuevos.append(entry)
        sent_links.add(link)

    # evita avalanchas
    nuevos = nuevos[:MAX_POSTS_PER_RUN]

    for post in reversed(nuevos):
        titulo = limpiar_html(post.title)
        link = limpiar_url_google(post.link)
        imagen = obtener_imagen(post)

        caption = f"""
<b>{data['emoji']} {source.upper()}</b>

{titulo}

<a href="{link}">📰 Leer noticia</a>
"""

        if imagen:
            send_photo(data["chat"], caption, imagen)
        else:
            send_message(data["chat"], caption)

    save_sent_links(source, sent_links)
