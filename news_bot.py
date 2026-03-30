import feedparser
import requests
import os
import json
import re
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

NITTER_INSTANCES = [
    "https://nitter.perennialte.ch",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
    "https://nitter.projectsegfau.lt"
]

# Headers para que Nitter nos deje descargar la imagen
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def find_real_link(entry):
    """Busca el enlace al artículo original dentro de la descripción"""
    # Buscamos cualquier link que NO sea de nitter o twitter
    links = re.findall(r'https?://[^\s<>"]+', entry.description)
    for link in links:
        if 'nitter' not in link and 't.co' not in link:
            # Limpiar posibles etiquetas HTML pegadas al final
            return link.split('<')[0].split('"')[0]
    return entry.link # Si no hay otro, devolvemos el de nitter

def send_telegram(chat_id, msg, link, image_url=None):
    reply_markup = {"inline_keyboard": [[{"text": "Ver Artículo ↗️", "url": link}]]}
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    if image_url and image_url.startswith('http'):
        try:
            # PASO CLAVE: Descargamos la imagen para enviarla como archivo
            img_res = requests.get(image_url, headers=HEADERS, timeout=15)
            if img_res.status_code == 200:
                photo_bytes = BytesIO(img_res.content)
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': ('image.jpg', photo_bytes, 'image/jpeg')}
                payload["caption"] = msg
                r = requests.post(url, data=payload, files=files)
                if r.status_code == 200:
                    print("✅ Noticia enviada con imagen.")
                    return
        except Exception as e:
            print(f"⚠️ Error procesando imagen: {e}")

    # Si falla la imagen o no hay, enviamos solo texto
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload["text"] = msg
    requests.post(url, data=payload)
    print("✅ Noticia enviada (solo texto).")

# ... (El resto de funciones extract_image y fetch_feed se mantienen igual que la versión anterior)

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
    return open(file, "r").read().strip() if os.path.exists(file) else ""

def save_last_link(account, link):
    with open(f"last_{account}.txt", "w") as f: f.write(link)

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
        if entry_id == last_id: break
        new_posts.append(entry)

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # Buscamos el link real (Bloomberg, etc)
            real_link = find_real_link(post)
            # Limpiamos el texto y escapamos HTML
            clean_title = html.escape(re.sub(r'https?://\S+', '', post.title).strip())
            
            message = f"<b>{account}</b>\n\n{clean_title}"
            image_url = extract_image(post, working_instance)
            
            send_telegram(chat_id, message, real_link, image_url)
        
        save_last_link(account, new_posts[-1].link)
