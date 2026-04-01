import feedparser
import requests
import os
import re
import json

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

def limpiar_texto_y_link(texto):
    links = re.findall(r'https?://\S+', texto)
    articulo = links[0] if links else ""
    texto_limpio = re.sub(r'https?://\S+', '', texto).strip()
    return texto_limpio, articulo

def get_tweet_id(link):
    return link.split("/")[-1]

# 🖼️ imagen del tweet (vxtwitter)
def obtener_imagen_tweet(tweet_id):
    try:
        url = f"https://api.vxtwitter.com/Twitter/status/{tweet_id}"
        r = requests.get(url, timeout=10).json()
        if "mediaURLs" in r and len(r["mediaURLs"]) > 0:
            return r["mediaURLs"][0]
    except:
        return None
    return None

# ─────────────────────────────

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file):
        return ""
    with open(file, "r") as f:
        return f.read().strip()

def save_last_link(account, link):
    with open(f"last_{account}.txt", "w") as f:
        f.write(link)

# ─────────────────────────────
# 🔘 BOTONES TELEGRAM (con artículo opcional)

def crear_botones(tweet_url, articulo_url):
    if articulo_url:
        keyboard = {
            "inline_keyboard": [[
                {"text": "🐦 Ver tweet", "url": tweet_url},
                {"text": "📰 Leer artículo", "url": articulo_url}
            ]]
        }
    else:
        keyboard = {
            "inline_keyboard": [[
                {"text": "🐦 Ver tweet", "url": tweet_url}
            ]]
        }
    return json.dumps(keyboard)

def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    })

def send_photo(chat_id, caption, photo, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, data={
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    })

# ─────────────────────────────

for account, chat_id in ACCOUNTS.items():
    feed = feedparser.parse(f"https://nitter.net/{account}/rss")

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link:
            break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()

        for post in new_posts:
            texto, articulo = limpiar_texto_y_link(post.title)
            tweet_id = get_tweet_id(post.link)
            tweet_fx = post.link.replace("nitter.net", "fxtwitter.com")

            botones = crear_botones(tweet_fx, articulo)
            caption = texto

            imagen = obtener_imagen_tweet(tweet_id)

            if imagen:
                send_photo(chat_id, caption, imagen, botones)
            else:
                send_message(chat_id, caption, botones)

        save_last_link(account, new_posts[-1].link)
