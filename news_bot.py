import requests
import os
import time
import json

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

HEADERS_BASE = {
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA",
    "user-agent": "Mozilla/5.0"
}

ACCOUNTS = [
    "CNNEE",
    "BBCWorld",
    "Reuters",
    "AP"
]

# ─────────────────────────────────────────────
# OBTENER GUEST TOKEN (NUEVO MÉTODO FUNCIONAL)
# ─────────────────────────────────────────────
def get_guest_token():
    r = requests.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers=HEADERS_BASE,
        timeout=20
    )
    data = r.json()
    if "guest_token" not in data:
        raise Exception("Twitter bloqueó guest token")
    return data["guest_token"]

# ─────────────────────────────────────────────
# OBTENER TWEETS DESDE GRAPHQL (MÉTODO NUEVO)
# ─────────────────────────────────────────────
def get_tweets(username, guest_token):

    headers = HEADERS_BASE.copy()
    headers["x-guest-token"] = guest_token

    url = f"https://api.twitter.com/2/search/adaptive.json?q=from:{username}&count=5&tweet_mode=extended"

    r = requests.get(url, headers=headers, timeout=20)
    data = r.json()

    if "globalObjects" not in data:
        return []

    tweets = data["globalObjects"]["tweets"]
    users = data["globalObjects"]["users"]

    result = []

    for tweet_id in tweets:
        t = tweets[tweet_id]

        text = t.get("full_text", "")
        media_urls = []
        video_url = None

        if "extended_entities" in t:
            media = t["extended_entities"]["media"]

            for m in media:
                if m["type"] == "photo":
                    media_urls.append(m["media_url_https"])

                if m["type"] == "video" or m["type"] == "animated_gif":
                    variants = m["video_info"]["variants"]
                    variants = [v for v in variants if "bitrate" in v]
                    if variants:
                        video_url = sorted(
                            variants,
                            key=lambda x: x["bitrate"],
                            reverse=True
                        )[0]["url"]

        result.append({
            "id": tweet_id,
            "text": text,
            "photos": media_urls,
            "video": video_url
        })

    return result


# ─────────────────────────────────────────────
# TELEGRAM SENDER
# ─────────────────────────────────────────────
def send_message(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text}
    )

def send_photo(photo, caption):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
        data={"chat_id": CHAT_ID, "photo": photo, "caption": caption}
    )

def send_video(video, caption):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
        data={"chat_id": CHAT_ID, "video": video, "caption": caption}
    )

# ─────────────────────────────────────────────
# CONTROL DE TWEETS YA ENVIADOS
# ─────────────────────────────────────────────
def load_last():
    if os.path.exists("last.json"):
        return json.load(open("last.json"))
    return {}

def save_last(data):
    json.dump(data, open("last.json","w"))

# ─────────────────────────────────────────────
# MAIN BOT
# ─────────────────────────────────────────────
last_ids = load_last()

guest_token = get_guest_token()

for account in ACCOUNTS:
    print("Revisando:", account)

    tweets = get_tweets(account, guest_token)

    if account not in last_ids:
        last_ids[account] = "0"

    for tweet in reversed(tweets):

        if tweet["id"] <= last_ids[account]:
            continue

        text = f"https://twitter.com/{account}/status/{tweet['id']}\n\n{tweet['text']}"

        # PRIORIDAD 1: VIDEO
        if tweet["video"]:
            print("Enviando VIDEO")
            send_video(tweet["video"], text)

        # PRIORIDAD 2: FOTO
        elif tweet["photos"]:
            print("Enviando FOTO")
            send_photo(tweet["photos"][0], text)

        # PRIORIDAD 3: TEXTO
        else:
            print("Enviando TEXTO")
            send_message(text)

        last_ids[account] = tweet["id"]
        time.sleep(2)

save_last(last_ids)

print("BOT OK")
