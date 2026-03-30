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
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.perennialte.ch"
]

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

def find_real_link(entry):
    """Extrae el link del medio original (Bloomberg, Reuters, etc.)"""
    links = re.findall(r'https?://[^\s<>"]+', entry.description)
    for link in links:
        if 'nitter' not in link and 't.co' not in link:
            return link.split('<')[0].split('"')[0]
    return entry.link

def get_og_image(url):
    """Obtiene la imagen de portada directamente del sitio web original"""
    try:
        if 'nitter' in url or 'twitter' in url: return None
        r = requests.get(url, headers=HEADERS, timeout=10)
        img_match = re.search(r'<meta [^>]*property="og:image" [^>]*content="([^"]+)"', r.text)
        if not img_match:
            img_match = re.search(r'<meta [^>]*content="([^"]+)" [^>]*property="og:image"', r.text)
        return img_match.group(1) if img_match else None
    except:
        return None

def send_telegram(chat_id, msg, link, nitter_img=None):
    reply_markup = {"inline_keyboard": [[{"text": "Ver Artículo ↗️", "url": link}]]}
    
    # Intentamos obtener la imagen de la web original o de nitter como plan B
    image_url = get_og_image(link) or nitter_img
    
    if image_url:
        try:
            # Descargamos la imagen para enviarla como archivo físico (evita bloqueos de URL)
            target = f"https://wsrv.nl/?url={image_url}" if 'nitter' in image_url else image_url
            img_res = requests.get(target, headers=HEADERS, timeout=15)
            
            if img_res.status_code == 200:
                photo = BytesIO(img_res.content)
                photo.name = 'image.jpg'
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': photo}
                data = {
                    "chat_id": chat_id,
                    "caption": msg, # El texto va aquí cuando hay foto
                    "reply_markup": json.dumps(reply_markup),
                    "parse_mode": "HTML"
                }
                r = requests.post(url, data=data, files=files)
                if r.status_code == 200:
                    print("✅ Noticia enviada con éxito (Imagen cargada).")
                    return
        except Exception as e:
            print(f"⚠️ Error con la imagen: {e}")

    # Fallback: Si no hay imagen o falló la carga, enviamos solo texto
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": msg,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }
    requests.post(url, data=payload)
    print("✅ Noticia enviada (Solo texto).")

def extract_nitter_image(entry, base_url):
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
    print(f"--- Revisando {account} ---")
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
            real_link = find_real_link(post)
            # Titular limpio, sin nombre de cuenta
            clean_title = html.escape(re.sub(r'https?://\S+', '', post.title).strip())
            
            n_img = extract_nitter_image(post, working_instance)
            send_telegram(chat_id, clean_title, real_link, n_img)

        save_last_link(account, new_posts[-1].link)
