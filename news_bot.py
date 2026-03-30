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

# ─────────────────────────────

def limpiar_html(texto):
    limpio = re.sub("<.*?>", "", texto)
    return limpio.strip()

def obtener_imagen(entry):
    # Distintos formatos RSS usan campos distintos
    if "media_content" in entry:
        return entry.media_content[0]["url"]
    if "links" in entry:
        for l in entry.links:
            if "image" in l.type:
                return l.href
    return None

# ─────────────────────────────

def get_last_link(source):
    file = f"last_{source}.txt"
    if not os.path.exists(file):
        return ""
    return open(file).read().strip()

def save_last_link(source, link):
    open(f"last_{source}.txt", "w").write(link)

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

for source, data in FEEDS.items():
    feed = feedparser.parse(data["url"])
    last_link = get_last_link(source)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link:
            break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()

        for post in new_posts:
            titulo = limpiar_html(post.title)
            link = post.link
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

        save_last_link(source, new_posts[-1].link)
