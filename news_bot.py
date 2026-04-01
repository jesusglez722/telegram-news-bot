import feedparser
import requests
import os
import re
import json
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCOUNTS = {
    "ReutersBiz": "-1003749568108",
    "ReuterChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────
# LIMPIAR TEXTO + EXTRAER LINK
# ─────────────────────────────
def limpiar_texto_y_link(texto):
    links = re.findall(r'https?://\S+', texto)
    articulo = links[0] if links else ""
    texto_limpio = re.sub(r'https?://\S+', '', texto).strip()
    return texto_limpio, articulo

def get_tweet_id(link):
    return link.split("/")[-1]

# ─────────────────────────────
# EXTRAER MEDIA REAL DEL TWEET (VIDEO O IMAGEN)
# ─────────────────────────────
def obtener_media_tweet(tweet_id):
    try:
        url = f"https://api.vxtwitter.com/Twitter/status/{tweet_id}?full=true"
        r = requests.get(url, headers=HEADERS, timeout=20)

        if r.status_code != 200:
            return None, None

        data = r.json()

        # 1️⃣ VIDEO directo
        if "videoURLs" in data and data["videoURLs"]:
            return "video", data["videoURLs"][0]

        # 2️⃣ VIDEO desde media_extended (EL CASO DE REUTERS)
        if "media_extended" in data:
            for m in data["media_extended"]:
                if m.get("type") == "video":
                    variants = m.get("video_info", {}).get("variants", [])
                    mp4s = [v["url"] for v in variants if "mp4" in v.get("content_type","")]
                    if mp4s:
                        return "video", mp4s[-1]

        # 3️⃣ IMAGEN
        if "mediaURLs" in data and data["mediaURLs"]:
            return "photo", data["mediaURLs"][0]

    except Exception as e:
        print("Error media:", e)

    return None, None

# ─────────────────────────────
# ANTI DUPLICADOS
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
# BOTONES TELEGRAM
# ─────────────────────────────
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

# ─────────────────────────────
# ENVÍOS TELEGRAM
# ─────────────────────────────
def send_message(chat_id, text, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    })
    time.sleep(2)

def send_photo(chat_id, caption, photo, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    requests.post(url, data={
        "chat_id": chat_id,
        "photo": photo,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    })
    time.sleep(2)

def send_video(chat_id, caption, video, reply_markup=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
    requests.post(url, data={
        "chat_id": chat_id,
        "video": video,
        "caption": caption,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    })
    time.sleep(2)

# ─────────────────────────────
# LOOP PRINCIPAL
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
            media_type, media_url = obtener_media_tweet(tweet_id)

            if media_type == "video":
                send_video(chat_id, texto, media_url, botones)
            elif media_type == "photo":
                send_photo(chat_id, texto, media_url, botones)
            else:
                send_message(chat_id, texto, botones)

        save_last_link(account, new_posts[-1].link)
