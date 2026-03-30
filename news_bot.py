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
    if not os.path.exists(file):
        return ""
    with open(file, "r") as f:
        return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f:
        f.write(link)

def find_original_link(entry):
    """
    Busca dentro del contenido del post un enlace que NO sea de nitter o twitter.
    Esto suele devolver el link directo a Bloomberg, Reuters, etc.
    """
    # Buscamos todas las URLs en la descripción del post
    links = re.findall(r'https?://[^\s<>"]+', entry.summary)
    for link in links:
        # Si el link no contiene nitter ni t.co (acortador de twitter), es el artículo
        if 'nitter' not in link and 't.co' not in link:
            return link
    # Si no encuentra nada especial, devolvemos el link original por si acaso
    return entry.link

def send_telegram(chat_id, msg, btn_link):
    """
    Envía el mensaje con un botón elegante para el enlace,
    así evitamos que el link largo ensucie el chat.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Creamos un botón "Ver artículo" para ocultar la URL larga
    reply_markup = {
        "inline_keyboard": [[
            {"text": "Leer artículo completo ↗️", "url": btn_link}
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }
    
    requests.post(url, data=payload)

# Usamos una instancia estable de Nitter
NITTER_BASE = "https://nitter.poast.org"

for account, chat_id in ACCOUNTS.items():
    feed_url = f"{NITTER_BASE}/{account}/rss"
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
            # 1. Obtenemos el link REAL del periódico (Bloomberg, Reuters, etc.)
            real_url = find_original_link(post)
            
            # 2. Limpiamos el título:
            # - Quitamos cualquier link que haya quedado en el texto
            # - Escapamos caracteres HTML para que no de error la API
            clean_title = re.sub(r'https?://\S+', '', post.title).strip()
            clean_title = html.escape(clean_title)
            
            # El mensaje ahora solo contiene el titular
            message = f"<b>{clean_title}</b>"
            
            send_telegram(chat_id, message, real_url)

        save_last_link(account, new_posts[-1].link)
