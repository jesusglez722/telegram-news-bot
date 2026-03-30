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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def find_real_link(entry):
    links = re.findall(r'https?://[^\s<>"]+', entry.description)
    for link in links:
        if 'nitter' not in link and 't.co' not in link:
            return link.split('<')[0].split('"')[0]
    return entry.link

def get_og_image(url):
    """Visita la noticia y extrae la imagen de vista previa original"""
    try:
        if 'nitter' in url: return None
        response = requests.get(url, headers=HEADERS, timeout=10)
        # Buscamos la etiqueta meta og:image que usan todos los periódicos
        image_match = re.search(r'<meta [^>]*property="og:image" [^>]*content="([^"]+)"', response.text)
        if not image_match:
            image_match = re.search(r'<meta [^>]*content="([^"]+)" [^>]*property="og:image"', response.text)
        
        if image_match:
            img_url = image_match.group(1)
            # Algunas webs usan proxies para sus imágenes, las limpiamos
            if img_url.startswith('http'):
                return img_url
    except:
        pass
    return None

def send_telegram(chat_id, msg, link, image_url=None):
    reply_markup = {"inline_keyboard": [[{"text": "Ver Artículo ↗️", "url": link}]]}
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    # Intentamos primero la imagen del artículo, si no, la de Nitter con proxy
    final_image = get_og_image(link) or (f"https://wsrv.nl/?url={image_url}" if image_url else None)

    if final_image:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload["photo"] = final_image
        payload["caption"] = msg
        r = requests.post(url, data=payload)
        if r.status_code == 200:
            print("✅ Enviado con imagen.")
            return
        else:
            print(f"⚠️ Falló imagen ({r.status_code}), enviando texto...")

    # Fallback: Solo texto
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload["text"] = msg
    requests.post(url, data=payload)
    print("✅ Enviado (solo texto).")

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

# --- BUCLE ---
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
            real_link = find_real_link(post)
            # Limpieza: sin nombre de cuenta, solo titular
            clean_title = html.escape(re.sub(r'https?://\S+', '', post.title).strip())
            
            # Buscamos imagen en Nitter por si el artículo no tiene
            nitter_img = extract_nitter_image(post, working_instance)
            
            send_telegram(chat_id, clean_title, real_link, nitter_img)

        save_last_link(account, new_posts[-1].link)
