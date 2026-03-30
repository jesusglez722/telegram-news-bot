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

# Lista de instancias para rotar si una falla
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.projectsegfau.lt",
    "https://nitter.perennialte.ch",
    "https://nitter.homeoncloud.com"
]

def get_last_link(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file): return ""
    with open(file, "r") as f: return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f: f.write(link)

def send_telegram(chat_id, msg, link, image_url=None):
    reply_markup = {"inline_keyboard": [[{"text": "Source ↗️", "url": link}]]}
    payload = {
        "chat_id": chat_id,
        "reply_markup": json.dumps(reply_markup),
        "parse_mode": "HTML"
    }

    # Intentamos enviar con foto si existe
    if image_url and image_url.startswith('http'):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload["photo"] = image_url
        payload["caption"] = msg
        print(f"Intentando enviar foto a {chat_id}...")
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload["text"] = msg
        print(f"Intentando enviar texto a {chat_id}...")

    response = requests.post(url, data=payload)
    
    # ESTO NOS DIRÁ EL ERROR REAL
    if response.status_code == 200:
        print("✅ Mensaje enviado correctamente a Telegram.")
    else:
        print(f"❌ ERROR TELEGRAM ({response.status_code}): {response.text}")
        
        # Si falló la foto, reintentamos solo con texto por si la URL de la imagen era el problema
        if image_url:
            print("Reintentando sin imagen...")
            url_text = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload_text = {
                "chat_id": chat_id,
                "text": msg,
                "reply_markup": json.dumps(reply_markup),
                "parse_mode": "HTML"
            }
            re_response = requests.post(url_text, data=payload_text)
            print(f"Resultado reintento: {re_response.status_code}")

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
    """Prueba diferentes instancias hasta obtener el feed"""
    for instance in NITTER_INSTANCES:
        url = f"{instance}/{account}/rss"
        print(f"Probando {instance}...")
        feed = feedparser.parse(url)
        if feed.entries:
            return feed, instance
    return None, None

for account, chat_id in ACCOUNTS.items():
    print(f"--- Revisando {account} ---")
    feed, working_instance = fetch_feed(account)

    if not feed:
        print(f"❌ Error: Todas las instancias de Nitter fallaron para {account}.")
        continue

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        entry_id = entry.link.split('/')[-1] if '/' in entry.link else entry.link
        last_id = last_link.split('/')[-1] if '/' in last_link else last_link
        
        if entry_id == last_id:
            break
        new_posts.append(entry)

    print(f"✅ Éxito usando {working_instance}. Noticias nuevas: {len(new_posts)}")

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            clean_title = html.escape(re.sub(r'http\S+', '', post.title).strip())
            message = f"<b>{account}</b>\n\n{clean_title}"
            image_url = extract_image(post, working_instance)
            send_telegram(chat_id, message, post.link, image_url)

        save_last_link(account, new_posts[-1].link)
