import feedparser
import requests
import os
import re
import json
import html

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCOUNTS = {
    "ReutersBiz": "-1003749568108",
    "ReuterChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# Lista de instancias de Nitter (nitter.net suele fallar mucho)
NITTER_URL = "https://nitter.poast.org" 

def get_last_link(account):
    file = f"last_{account}.txt"
    return open(file, "r").read().strip() if os.path.exists(file) else ""

def save_last_link(account, link):
    with open(f"last_{account}.txt", "w") as f:
        f.write(link)

def send_telegram(chat_id, text, link, image_url=None):
    # Creamos un botón para el enlace original
    reply_markup = {"inline_keyboard": [[{"text": "Ver Artículo ↗️", "url": link}]]}
    
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    if image_url:
        # Si hay imagen, usamos sendPhoto (usamos un proxy para asegurar que Telegram la cargue)
        img_proxy = f"https://wsrv.nl/?url={image_url}"
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload["photo"] = img_proxy
        payload["caption"] = text
    else:
        # Si no hay imagen, enviamos solo mensaje
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload["text"] = text

    requests.post(url, data=payload)

def extract_image(entry):
    """Busca la URL de la imagen en la descripción de Nitter"""
    if 'description' in entry:
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match:
            img_url = img_match.group(1)
            if img_url.startswith('/'): img_url = f"{NITTER_URL}{img_url}"
            return img_url
    return None

for account, chat_id in ACCOUNTS.items():
    feed = feedparser.parse(f"{NITTER_URL}/{account}/rss")
    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link:
            break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # Limpiamos el título de enlaces (ya que irán en el botón)
            clean_title = html.escape(re.sub(r'http\S+', '', post.title).strip())
            
            # Buscamos la imagen
            img = extract_image(post)
            
            # El link original (en Nitter suele ser el link del tuit)
            # El botón llevará al usuario al tuit/noticia directamente
            send_telegram(chat_id, clean_title, post.link, img)

        save_last_link(account, new_posts[-1].link)
