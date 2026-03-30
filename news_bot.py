import requests
import os
import re

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Canales de Telegram
CHANNELS = {
    "ReutersBiz": "-1003749568108",
    "ReutersChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126"
}

# Usuarios de X a vigilar (RSSHub)
FEEDS = {
    "ReutersBiz": "https://rsshub.app/twitter/user/ReutersBiz",
    "ReutersChina": "https://rsshub.app/twitter/user/ReutersChina",
    "business": "https://rsshub.app/twitter/user/business",
    "WSJ": "https://rsshub.app/twitter/user/WSJ",
    "FT": "https://rsshub.app/twitter/user/FT",
    "TheEconomist": "https://rsshub.app/twitter/user/TheEconomist"
}

# Emojis por medio
EMOJIS = {
    "ReutersBiz": "🟠",
    "ReutersChina": "🐉",
    "business": "🟡",
    "WSJ": "⚪",
    "FT": "🟤",
    "TheEconomist": "🔴",
    
}

# ─────────────────────────────────────────────

def limpiar_tweet(texto):
    return re.sub(r'http\S+', '', texto).strip()

def format_tweet(source, text, url):
    emoji = EMOJIS.get(source, "📰")
    return f"""
<b>{emoji} {source.upper()}</b>

{text}

<a href="{url}">🔗 Leer en X</a>
"""

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    requests.post(url, data=data)

# Guardar último tweet enviado
def load_last(source):
    file = f"last_{source}.txt"
    if os.path.exists(file):
        with open(file, "r") as f:
            return f.read().strip()
    return ""

def save_last(source, tweet_id):
    with open(f"last_{source}.txt", "w") as f:
        f.write(tweet_id)

# ─────────────────────────────────────────────

def check_feed(source, feed_url, chat_id):
    print(f"Checking {source}...")

    last_id = load_last(source)

    r = requests.get(feed_url)
    if r.status_code != 200:
        print("RSS error")
        return

    items = r.text.split("<item>")[1:]

    new_items = []

    for item in items:
        link = item.split("<link>")[1].split("</link>")[0]
        tweet_id = link.split("/")[-1]

        if tweet_id == last_id:
            break

        title = item.split("<title>")[1].split("</title>")[0]
        title = limpiar_tweet(title)

        new_items.append((tweet_id, title, link))

    # Enviar en orden cronológico correcto
    new_items.reverse()

    for tweet_id, title, link in new_items:
        msg = format_tweet(source, title, link)
        send_telegram(chat_id, msg)
        save_last(source, tweet_id)

# ─────────────────────────────────────────────

def main():
    for source in FEEDS:
        check_feed(source, FEEDS[source], CHANNELS[source])

if __name__ == "__main__":
    main()
