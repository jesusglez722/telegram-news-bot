import feedparser
import requests
import os
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCOUNTS = {
    "ReutersBiz": "-1003749568108",
    "ReuterChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# ─────────────────────────────
# LIMPIAR TEXTO Y EXTRAER LINK DEL ARTÍCULO
# ─────────────────────────────

def limpiar_tweet_y_link(texto):
    links = re.findall(r'https?://\S+', texto)
    articulo = links[0] if links else ""
    texto_limpio = re.sub(r'https?://\S+', '', texto).strip()
    return texto_limpio, articulo

# ─────────────────────────────

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file):
        return ""
    with open(file, "r") as f:
        return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f:
        f.write(link)

# ─────────────────────────────
# TELEGRAM
# ─────────────────────────────

def send_telegram(chat_id, msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    })

def send_photo(chat_id, caption, image_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, data={
        "chat_id": chat_id,
        "photo": image_url,
        "caption": caption,
        "parse_mode": "HTML"
    })

# Emojis por medio
EMOJIS = {
    "ReutersBiz": "🟡",
    "ReuterChina": "🐉",
    "business": "💼",
    "WSJ": "🔵",
    "FT": "🟣",
    "TheEconomist": "🔴"
}

# ─────────────────────────────

for account, chat_id in ACCOUNTS.items():
    feed_url = f"https://nitter.net/{account}/rss"
    feed = feedparser.parse(feed_url)

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link:
            break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()

        for post in new_posts:
            texto, articulo = limpiar_tweet_y_link(post.title)
            emoji = EMOJIS.get(account, "📰")

            mensaje = f"""
<b>{emoji} {account.upper()}</b>

{texto}

<a href="{articulo}">🔗 Leer artículo</a>
"""

            # 🔥 NUEVO: enviar imagen si existe
            imagen = None
            if hasattr(post, "media_content"):
                try:
                    imagen = post.media_content[0]["url"]
                except:
                    imagen = None

            if imagen:
                send_photo(chat_id, mensaje, imagen)
            else:
                send_telegram(chat_id, mensaje)

        save_last_link(account, new_posts[-1].link)
