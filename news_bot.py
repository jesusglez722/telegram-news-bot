import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCOUNTS = {
    "ReutersBiz": "-1003749568108",
    "ReuterChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# Instancias de Nitter para rotar si una falla
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.perennialte.ch"
]

def find_article_link(post):
    """Busca el link real de la noticia (Bloomberg, Reuters, etc.)"""
    content = post.title + " " + post.get('summary', '')
    enlaces = re.findall(r'https?://[^\s<>"]+', content)
    for url in enlaces:
        if 'nitter' not in url and 't.co' not in url:
            return url.split(')')[0].split('<')[0]
    return post.link

def send_telegram(chat_id, text, button_url, image_url=None):
    """Descarga la imagen y la sube a Telegram como archivo para evitar errores"""
    reply_markup = {"inline_keyboard": [[{"text": "Ver artículo completo ↗️", "url": button_url}]]}
    
    if image_url:
        try:
            # Truco final: usamos el proxy de WordPress solo para la descarga interna del bot
            # Esto asegura que el bot de GitHub pueda descargar la foto de Nitter
            download_url = f"https://i0.wp.com/{image_url.replace('https://', '')}"
            img_res = requests.get(download_url, timeout=15)
            
            if img_res.status_code == 200:
                photo_file = BytesIO(img_res.content)
                photo_file.name = 'news.jpg'
                
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': photo_file}
                data = {
                    "chat_id": chat_id,
                    "caption": text,
                    "reply_markup": json.dumps(reply_markup),
                    "parse_mode": "HTML"
                }
                r = requests.post(url, data=data, files=files)
                if r.status_code == 200:
                    print(f"✅ Noticia enviada con foto cargada")
                    return
        except Exception as e:
            print(f"⚠️ Error cargando imagen: {e}")

    # Si no hay imagen o falló la subida, enviamos texto limpio
    url_text = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }
    requests.post(url_text, data=payload)
    print(f"✅ Noticia enviada (solo texto)")

def extract_nitter_image(entry, base_url):
    if 'description' in entry:
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match:
            img_url = img_match.group(1)
            if img_url.startswith('/'): return f"{base_url}{img_url}"
            return img_url
    return None

def get_last_link(account):
    file = f"last_{account}.txt"
    return open(file, "r").read().strip() if os.path.exists(file) else ""

def save_last_link(account, link):
    with open(f"last_{account}.txt", "w") as f: f.write(link)

# --- BUCLE PRINCIPAL ---
for account, chat_id in ACCOUNTS.items():
    print(f"--- {account} ---")
    
    feed = None
    working_inst = ""
    for inst in NITTER_INSTANCES:
        f = feedparser.parse(f"{inst}/{account}/rss")
        if f.entries:
            feed = f
            working_inst = inst
            break
            
    if not feed: continue

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link: break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # 1. Link real para el botón
            real_url = find_article_link(post)
            
            # 2. Titular limpio (Sin negritas y sin URLs de texto)
            clean_title = re.sub(r'https?://\S+', '', post.title).strip()
            clean_title = html.escape(clean_title)
            
            # 3. Imagen de Nitter
            img = extract_nitter_image(post, working_inst)
            
            # 4. Envío
            send_telegram(chat_id, clean_title, real_url, img)

        save_last_link(account, new_posts[-1].link)
