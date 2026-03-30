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

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file): return ""
    with open(file, "r") as f: return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f: f.write(link)

def send_telegram(chat_id, title, link):
    """Envía el mensaje con un botón y sin links largos en el texto"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Creamos el botón "Ver Artículo"
    reply_markup = {
        "inline_keyboard": [[
            {"text": "Ver Artículo Completo ↗️", "url": link}
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": title,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }
    
    requests.post(url, data=payload)

# He puesto poast.org porque nitter.net suele fallar, 
# pero si a ti te funciona .net, puedes cambiarlo.
BASE_URL = "https://nitter.poast.org" 

for account, chat_id in ACCOUNTS.items():
    feed_url = f"{BASE_URL}/{account}/rss"
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
            # 1. Limpiamos el título: quitamos el link y el @usuario
            # Buscamos si hay un link dentro del título para usarlo en el botón
            link_en_titulo = re.search(r'https?://\S+', post.title)
            real_link = link_en_titulo.group(0) if link_en_titulo else post.link
            
            # Limpiamos el titular de cualquier URL y espacios raros
            clean_title = re.sub(r'https?://\S+', '', post.title).strip()
            # Escapamos HTML para que Telegram no de error con símbolos como < o >
            clean_title = html.escape(clean_title)
            
            # 2. Enviamos solo el titular (sin el @account)
            send_telegram(chat_id, clean_title, real_link)

        save_last_link(account, new_posts[-1].link)
