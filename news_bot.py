import feedparser
import requests
import os
import json
import re
import html # Importante para limpiar el texto

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
    reply_markup = {"inline_keyboard": [[{"text": "Source ↗️", "url": link}]]}
    
    # Preparamos la base del envío
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    if image_url and image_url.startswith('http'):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload["photo"] = image_url
        payload["caption"] = msg
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload["text"] = msg

    r = requests.post(url, data=payload)
    if r.status_code != 200:
        print(f"Error enviando a Telegram: {r.text}") # Esto nos dirá qué falló exactamente

def extract_image(entry, base_url):
    """Extrae la imagen y asegura que sea una URL completa"""
    if 'description' in entry:
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match:
            img_url = img_match.group(1)
            if img_url.startswith('//'): return "https:" + img_url
            if img_url.startswith('/'): return base_url + img_url
            return img_url
    return None

# Instancia de Nitter (puedes cambiarla si falla)
NITTER_BASE = "https://nitter.poast.org"

for account, chat_id in ACCOUNTS.items():
    print(f"--- Revisando {account} ---")
    feed_url = f"{NITTER_BASE}/{account}/rss"
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print(f"Aviso: No se pudieron obtener entradas de {account}. Nitter podría estar caído.")
        continue

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        # Limpiamos el link para comparar (quitamos el dominio por si cambió)
        entry_id = entry.link.split('/')[-1] if '/' in entry.link else entry.link
        last_id = last_link.split('/')[-1] if '/' in last_link else last_link
        
        if entry_id == last_id:
            break
        new_posts.append(entry)

    print(f"Nuevas noticias: {len(new_posts)}")

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # LIMPIEZA CRÍTICA: Escapamos el texto para que no rompa el HTML de Telegram
            clean_title = html.escape(re.sub(r'http\S+', '', post.title).strip())
            message = f"<b>{account}</b>\n\n{clean_title}"
            
            image_url = extract_image(post, NITTER_BASE)
            send_telegram(chat_id, message, post.link, image_url)

        save_last_link(account, new_posts[-1].link)
