import feedparser
import requests
import os
import re
import json
import html
from io import BytesIO

# Configuración (Tus credenciales y feeds)
BOT_TOKEN = os.getenv("BOT_TOKEN")

FEEDS = {
    "ReutersBiz": "https://news.google.com/rss/search?q=site:reuters.com/business&hl=en-US&gl=US&ceid=US:en",
    "ReutersChina": "https://news.google.com/rss/search?q=site:reuters.com/world/china&hl=en-US&gl=US&ceid=US:en",
    "business": "https://news.google.com/rss/search?q=site:bloomberg.com&hl=en-US&gl=US&ceid=US:en",
    "WSJ": "https://news.google.com/rss/search?q=site:wsj.com&hl=en-US&gl=US&ceid=US:en",
    "FT": "https://news.google.com/rss/search?q=site:ft.com&hl=en-US&gl=US&ceid=US:en",
    "TheEconomist": "https://www.economist.com/latest/rss.xml"
}

CHATS = {
    "ReutersBiz": "-1003749568108",
    "ReutersChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# Cabeceras de navegador real para evitar bloqueos
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
}

# --- FUNCIONES DE AYUDA ---

def extraer_url_real_google(entry):
    if "news.google.com" in entry.link and "summary" in entry:
        match = re.search(r'href="(https?://[^"]+)"', entry.summary)
        if match: return match.group(1).split('?')[0]
    return entry.link.split('?')[0]

def buscar_url_imagen(url_real):
    """Visita la web original de la noticia para encontrar la foto real"""
    try:
        if "economist.com" in url_real: return None # The Economist lo manejamos en RSS
        r = requests.get(url_real, headers=HEADERS, timeout=12)
        match = re.search(r'property="og:image"\s+content="([^"]+)"', r.text)
        if not match:
            match = re.search(r'content="([^"]+)"\s+property="og:image"', r.text)
        return match.group(1) if match else None
    except:
        return None

def obtener_imagen_economist(entry):
    """The Economist es el único estable vía RSS"""
    if "media_content" in entry: return entry.media_content[0]["url"]
    if "description" in entry:
        img_match = re.search(r'<img [^>]*src="([^"]+)"', entry.description)
        if img_match: return img_match.group(1)
    return None

def send_telegram(chat_id, formatted_text, image_url=None):
    """Descarga la imagen y la sube físicamente a Telegram para evitar bloqueos"""
    
    # 1. Si tenemos imagen, intentamos descargarla y subirla
    if image_url:
        try:
            # DESCARGAMOS LA IMAGEN A MEMORIA (GITHUB SIDE)
            img_res = requests.get(image_url, headers=HEADERS, timeout=15)
            
            if img_res.status_code == 200:
                # LA SUBIMOS COMO ARCHIVO A TELEGRAM
                photo_bytes = BytesIO(img_res.content)
                photo_bytes.name = 'news.jpg'
                
                url_photo = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                files = {'photo': photo_bytes}
                data = {
                    "chat_id": chat_id,
                    "caption": formatted_text, # El texto va debajo de la foto
                    "parse_mode": "HTML"
                }
                r_photo = requests.post(url_photo, data=data, files=files)
                if r_photo.status_code == 200:
                    print("  ✅ Noticia enviada con imagen cargada.")
                    return # Salimos si el envío con foto funcionó
        except Exception as e:
            print(f"  ⚠️ Falló la carga de imagen, reintentando texto: {e}")

    # 2. Fallback: Si no hay imagen o falla la subida, enviamos solo texto
    url_text = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload_text = {
        "chat_id": chat_id,
        "text": formatted_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(url_text, data=payload_text)
    print("  ✅ Noticia enviada (solo texto).")

# --- PROCESO PRINCIPAL ---
print("🚀 Iniciando bot...")

for source, feed_url in FEEDS.items():
    print(f"Checking {source}...")
    feed = feedparser.parse(feed_url)
    
    file_hist = f"sent_{source}.txt"
    sent_links = set()
    if os.path.exists(file_hist):
        with open(file_hist, "r") as f: sent_links = set(line.strip() for line in f.readlines())

    nuevos = []
    # Usamos set para evitar duplicados en la misma tanda (problema WSJ)
    vistos_ahora = set()

    for entry in feed.entries[:12]:
        url = extraer_url_real_google(entry).lower()
        if url not in sent_links and url not in vistos_ahora:
            nuevos.append((entry, url))
            vistos_ahora.add(url)

    if nuevos:
        nuevos.reverse() # Enviamos del más viejo al más nuevo
        for entry, url in nuevos[:3]: # Máximo 3 por ejecución
            
            # Limpieza y formato (sin negritas redundantes)
            clean_title = re.sub(r" - [^-]+$", "", entry.title).strip()
            # El link va dentro del texto, sin botón
            formatted_message = f"📰 <b>{clean_title}</b>\n\n<a href='{url}'>Ver artículo completo</a>"
            
            # Buscamos imagen (método específico para The Economist vs Resto)
            if source == "TheEconomist":
                imagen = obtener_imagen_economist(entry)
            else:
                imagen = buscar_url_imagen(url)
            
            # Envío definitivo
            send_telegram(CHATS[source], formatted_message, imagen)
            sent_links.add(url)
            
        # Guardamos historial
        with open(file_hist, "w") as f:
            f.write("\n".join(list(sent_links)[-200:]))

print("✅ Bot terminado.")
