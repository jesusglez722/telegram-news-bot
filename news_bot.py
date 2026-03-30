import feedparser
import requests
import os
import re
import json
import html

# Configuración
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

def send_telegram(chat_id, text, button_url):
    """Envía el mensaje usando el botón elegante"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Configuración del botón
    markup = {
        "inline_keyboard": [[
            {"text": "Ver artículo completo ↗️", "url": button_url}
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(markup),
        "parse_mode": "HTML"
    }
    
    r = requests.post(url, data=payload)
    return r.status_code

# --- INICIO DEL PROCESO ---
print("🚀 Iniciando el bot de noticias...")

for account, chat_id in ACCOUNTS.items():
    print(f"🔎 Revisando: {account}")
    
    # Mantenemos nitter.net porque es el que te funciona bien
    feed_url = f"https://nitter.net/{account}/rss"
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print(f"  ⚠️ No se han podido cargar noticias de {account}")
        continue

    last_link = get_last_link(account)
    new_posts = []

    for entry in feed.entries:
        if entry.link == last_link:
            break
        new_posts.append(entry)

    print(f"  ✨ Noticias nuevas: {len(new_posts)}")

    if new_posts:
        new_posts.reverse()
        for post in new_posts:
            # 1. Extraer el enlace real del título si existe
            # (Twitter/Nitter suelen poner el link de la noticia al final del titular)
            enlaces = re.findall(r'https?://\S+', post.title)
            button_link = enlaces[0] if enlaces else post.link
            
            # 2. Limpiar el titular
            # Quitamos los links del texto y el @usuario no lo incluimos
            clean_title = re.sub(r'https?://\S+', '', post.title).strip()
            # Escapamos caracteres especiales para que Telegram no falle
            clean_title = html.escape(clean_title)
            
            # Enviamos a Telegram
            status = send_telegram(chat_id, clean_title, button_link)
            print(f"  📤 Envío a {account}: {status}")

        save_last_link(account, new_posts[-1].link)

print("✅ Proceso terminado.")
