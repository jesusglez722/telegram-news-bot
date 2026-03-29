import feedparser
import requests
import os
import json
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

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file): return ""
    with open(file, "r") as f: return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f: f.write(link)

def send_telegram(chat_id, msg, link, image_url=None):
    # Crear el botón "Source"
    reply_markup = {
        "inline_keyboard": [[
            {"text": "Source ↗️", "url": link}
        ]]
    }

    payload = {
        "chat_id": chat_id,
        "caption": msg if image_url else None,
        "text": msg if not image_url else None,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    if image_url:
        # Si hay imagen, usamos sendPhoto
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload["photo"] = image_url
        requests.post(url, data=payload)
    else:
        # Si no hay imagen, usamos sendMessage
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data=payload)

def extract_image(entry):
    """Intenta extraer la URL de la imagen del feed de Nitter"""
    if 'description' in entry:
        # Nitter suele poner la imagen en una etiqueta <img> dentro de la descripción
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match:
            return img_match.group(1)
    return None

for account, chat_id in ACCOUNTS.items():
    # Usando una instancia alternativa más estable
    feed_url = f"https://nitter.poast.org/{account}/rss"
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
            # Limpiamos el texto para que no sea solo el link
            title = post.title
            # Si el título es muy largo o tiene el link de nitter al final, lo limpiamos
            clean_text = re.sub(r'http\S+', '', title).strip()
            
            message = f"<b>{account}</b>\n\n{clean_text}"
            
            image_url = extract_image(post)
            
            # Enviamos el link original de Bloomberg/Reuters, no el de Nitter
            # Nitter suele poner el link original en el campo 'link'
            send_telegram(chat_id, message, post.link, image_url)

        save_last_link(account, new_posts[-1].link)
