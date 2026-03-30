import feedparser
import requests
import os
import re
import json
import html

BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/business&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003749568108",
        "emoji": "🟠"
    },
    "ReutersChina": {
        "url": "https://news.google.com/rss/search?q=site:reuters.com/world/china&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003724765047",
        "emoji": "🟠"
    },
    "business": {
        "url": "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003760302624",
        "emoji": "🟡"
    },
    "WSJ": {
        "url": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003861476711",
        "emoji": "⚪"
    },
    "FT": {
        "url": "https://news.google.com/rss/search?q=site:ft.com&hl=en-US&gl=US&ceid=US:en",
        "chat": "-1003561464477",
        "emoji": "🟤"
    },
    "TheEconomist": {
        "url": "https://www.economist.com/latest/rss.xml",
        "chat": "-1003897620126",
        "emoji": "🔴"
    }
}

MAX_HISTORY = 500  # Aumentado para mayor seguridad
MAX_POSTS_PER_RUN = 5

# ─────────────────────────────
# LIMPIEZA Y EXTRACCIÓN
# ─────────────────────────────

def limpiar_html(texto):
    limpio = re.sub("<.*?>", "", texto)
    # Google News suele añadir " - Nombre del Medio" al final del título
    limpio = re.sub(r" - [^-]+$", "", limpio)
    return limpio.strip()

def limpiar_url_final(link):
    # Limpieza agresiva de parámetros de rastreo
    link = link.split("?")[0].split("#")[0]
    return link.strip().lower()

def extraer_url_real_google(entry):
    # Google News a veces pone la URL real en el summary
    if "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match:
            return match.group(1)
    return entry.link

# ─────────────────────────────
# IMÁGENES (ELIMINANDO LOGOS DE GOOGLE)
# ─────────────────────────────

def obtener_imagen_real(entry, url_real):
    # 1. Ignoramos media_content porque suele ser el LOGO del medio en Google News
    # Solo lo aceptamos si NO es de Google News (como The Economist)
    if "news.google.com" not in entry.link:
        if "media_content" in entry:
            return entry.media_content[0]["url"]

    # 2. Intentamos Scrapping de la web real (og:image)
    # Usamos un User-Agent de navegador real para evitar bloqueos
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url_real, timeout=10, headers=headers)
        # Buscamos og:image o twitter:image
        match = re.search(r'property="og:image"\s+content="([^"]+)"', res.text)
        if not match:
            match = re.search(r'name="twitter:image"\s+content="([^"]+)"', res.text)
        
        if match:
            img_url = match.group(1)
            # Evitar capturar logos pequeños que a veces están en og:image
            if "logo" not in img_url.lower():
                return img_url
    except:
        pass
    return None

# ─────────────────────────────
# SISTEMA DE ARCHIVOS
# ─────────────────────────────

def load_sent_links(source):
    file = f"sent_{source}.txt"
    if not os.path.exists(file): return set()
    with open(file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_sent_links(source, links_set):
    file = f"sent_{source}.txt"
    # Guardamos solo los últimos MAX_HISTORY para no inflar el archivo
    links = list(links_set)[-MAX_HISTORY:]
    with open(file, "w", encoding="utf-8") as f:
        f.write("\n".join(links))

# ─────────────────────────────
# ENVIAR A TELEGRAM
# ─────────────────────────────

def send_to_telegram(chat_id, caption, image=None):
    if image:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {"chat_id": chat_id, "photo": image, "caption": caption, "parse_mode": "HTML"}
    else:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML", "disable_web_page_preview": False}
    
    requests.post(url, data=payload)

# ─────────────────────────────
# MAIN
# ─────────────────────────────

for source, data in FEEDS.items():
    print(f"Checking {source}...")
    feed = feedparser.parse(data["url"])
    sent_links = load_sent_links(source)
    nuevos = []

    for entry in feed.entries:
        url_real = extraer_url_real_google(entry)
        url_limpia = limpiar_url_final(url_real)

        # Doble comprobación de duplicados (URL limpia y el ID de Google)
        if url_limpia in sent_links:
            continue

        entry.final_link = url_limpia
        nuevos.append(entry)
        sent_links.add(url_limpia)

    # Solo procesamos los X más recientes
    nuevos = nuevos[:MAX_POSTS_PER_RUN]

    for post in reversed(nuevos):
        titulo = limpiar_html(post.title)
        link = post.final_link
        
        # Intentar obtener imagen de la web (evitando el logo de Google News)
        imagen = obtener_imagen_real(post, link)

        caption = f"<b>{data['emoji']} {source.upper()}</b>\n\n{titulo}\n\n<a href='{link}'>📰 Leer noticia</a>"

        send_to_telegram(data["chat"], caption, imagen)

    save_sent_links(source, sent_links)
