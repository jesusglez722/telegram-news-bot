import feedparser
import requests
import os
import json
import re
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

NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.projectsegfau.lt",
    "https://nitter.perennialte.ch"
]

def find_real_link(entry):
    """Busca el enlace al artículo original dentro de la descripción"""
    links = re.findall(r'https?://[^\s<>"]+', entry.description)
    for link in links:
        if 'nitter' not in link and 't.co' not in link:
            return link.split('<')[0].split('"')[0]
    return entry.link

def get_proxied_image_url(image_url):
    """Encapsula la URL de la imagen en el proxy wsrv.nl para saltar bloqueos"""
    if image_url and image_url.startswith('http'):
        # wsrv.nl es un proxy gratuito y fiable de imágenes
        return f"https://wsrv.nl/?url={image_url}"
    return None

def send_telegram(chat_id, msg, link, image_url=None):
    reply_markup = {"inline_keyboard": [[{"text": "Ver Artículo ↗️", "url": link}]]}
    
    # Preparamos los parámetros básicos del mensaje
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    # Intentamos usar el proxy de imágenes si existe URL
    proxied_image = get_proxied_image_url(image_url)
    
    if proxied_image:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        # Para sendPhoto, el texto debe ir en 'caption'
        payload["photo"] = proxied_image
        payload["caption"] = msg
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            print("✅ Noticia enviada con imagen (vía proxy).")
            return

    # Si no hay imagen o el envío falló, enviamos solo texto
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload["text"] = msg
    requests.post(url, data=payload)
    print("✅ Noticia enviada (solo texto).")

def extract_image(entry, base_url):
    if 'description' in entry:
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match:
            img_url = img_match.group(1)
            if img_url.startswith('//'): return "https:" + img_url
            if img_url.startswith('/'): return base_url + img_url
            return img_url
    return None

def fetch_feed(account):
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{account}/rss"
        try:
            feed = feedparser.parse(url)
            if feed.entries: return feed, instance
        except: continue
    return None, None

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file): return ""
    with open(file, "r") as f: return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f: f.write(link)

# --- BUCLE PRINCIPAL ---
for account, chat_id in ACCOUNTS.items():
    print(f"--- {account} ---")
    feed, working_instance = fetch_feed(account)
    if not feed: continue

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        entry_id = entry.link.split('/')[-1] if '/' in entry.link else entry.link
        last_id = last_link.split('/')[-1] if '/' in last_link else last_link
        
        if entry_id == last_id:
            break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # 1. Buscamos el link real (Bloomberg, etc)
            real_link = find_real_link(post)
            
            # 2. LIMPIEZA DEL TEXTO (NUEVO DISEÑO)
            # Quitamos todos los enlaces basura y escapamos HTML
            clean_title = html.escape(re.sub(r'https?://\S+', '', post.title).strip())
            
            # Formato final del mensaje: solo el titular limpio
            message = clean_title 
            
            # 3. Procesamos la imagen
            image_url = extract_image(post, working_instance)
            
            # 4. Enviamos a Telegram
            send_telegram(chat_id, message, real_link, image_url)

        save_last_link(account, new_posts[-1].link)
