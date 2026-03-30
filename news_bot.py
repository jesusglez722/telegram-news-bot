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

def find_article_link(post):
    """Busca un enlace que no sea de nitter en el post"""
    # Buscamos en el título y en el resumen del RSS
    texto_completo = post.title + " " + post.get('summary', '')
    enlaces = re.findall(r'https?://[^\s<>"]+', texto_completo)
    for url in enlaces:
        if 'nitter' not in url and 't.co' not in url:
            # Limpiamos posibles caracteres residuales al final del link
            return url.split(')')[0].split(']')[0].split('<')[0]
    return post.link # Si no hay otro, usamos el de nitter

def send_telegram(chat_id, text, link):
    """Envía el mensaje con un botón para ocultar el link largo"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Creamos el botón
    markup = {
        "inline_keyboard": [[
            {"text": "Ver artículo completo ↗️", "url": link}
        ]]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": json.dumps(markup),
        "parse_mode": "HTML"
    }
    
    requests.post(url, data=payload)

for account, chat_id in ACCOUNTS.items():
    # Usamos nitter.net como en tu código original
    feed_url = f"https://nitter.net/{account}/rss"
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
            # 1. Buscamos el link real del periódico
            original_url = find_article_link(post)
            
            # 2. Limpiamos el título (quitamos enlaces de texto y el nombre de la cuenta)
            # Quitamos cualquier URL que aparezca en el texto
            clean_title = re.sub(r'https?://\S+', '', post.title).strip()
            # Escapamos HTML para evitar errores con símbolos raros
            clean_title = html.escape(clean_title)
            
            # 3. El mensaje ahora es solo el titular limpio
            send_telegram(chat_id, clean_title, original_url)

        save_last_link(account, new_posts[-1].link)
