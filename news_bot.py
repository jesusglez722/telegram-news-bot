import requests
import os
import re
import json
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")

ACCOUNTS = {
    "ReutersBiz": "-1003749568108",
    "ReuterChina": "-1003724765047",
    "business": "-1003760302624",
    "WSJ": "-1003861476711",
    "FT": "-1003561464477",
    "TheEconomist": "-1003897620126",
    "aleabitoreddit": "-1003627209266"
}

HEADERS_BASE = {"User-Agent":"Mozilla/5.0"}

# ─────────────────────────────
# 🔥 Obtener guest token (truco del frontend de Twitter)
def get_guest_token():
    r = requests.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers={
            "Authorization":"Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA"
        }
    )
    return r.json()["guest_token"]

# ─────────────────────────────
def get_last_id(account):
    file=f"last_{account}.txt"
    if not os.path.exists(file):
        return ""
    return open(file).read().strip()

def save_last_id(account,id):
    open(f"last_{account}.txt","w").write(id)

# ─────────────────────────────
def crear_botones(tweet_url, articulo_url):
    if articulo_url:
        kb={"inline_keyboard":[[
            {"text":"🐦 Ver tweet","url":tweet_url},
            {"text":"📰 Leer artículo","url":articulo_url}
        ]]}
    else:
        kb={"inline_keyboard":[[
            {"text":"🐦 Ver tweet","url":tweet_url}
        ]]}
    return json.dumps(kb)

# ─────────────────────────────
def send_message(chat_id,text,buttons=None):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={
        "chat_id":chat_id,
        "text":text,
        "parse_mode":"HTML",
        "disable_web_page_preview":True,
        "reply_markup":buttons
    })
    time.sleep(2)

def send_photo(chat_id,text,url,buttons=None):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",data={
        "chat_id":chat_id,
        "photo":url,
        "caption":text,
        "parse_mode":"HTML",
        "reply_markup":buttons
    })
    time.sleep(2)

def send_video(chat_id,text,url,buttons=None):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",data={
        "chat_id":chat_id,
        "video":url,
        "caption":text,
        "parse_mode":"HTML",
        "reply_markup":buttons
    })
    time.sleep(2)

# ─────────────────────────────
def limpiar_texto(texto):
    links=re.findall(r'https?://\S+',texto)
    articulo=links[0] if links else ""
    texto=re.sub(r'https?://\S+','',texto).strip()
    return texto,articulo

# ─────────────────────────────
# 🔥 Obtener tweets reales (endpoint interno)
def obtener_tweets(user,guest_token):
    url=f"https://api.twitter.com/2/timeline/profile/{user}.json"

    headers={
        "authorization":"Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAA",
        "x-guest-token":guest_token,
        "user-agent":"Mozilla/5.0"
    }

    try:
        data=requests.get(url,headers=headers,timeout=20).json()
        tweets=[]
        instrucciones=data["timeline"]["instructions"]

        for inst in instrucciones:
            if "addEntries" not in inst:
                continue
            for entry in inst["addEntries"]["entries"]:
                if "tweet" in entry.get("content",{}):
                    tweets.append(entry["content"]["tweet"])

        return tweets
    except:
        return []

# ─────────────────────────────
guest_token=get_guest_token()

for account,chat_id in ACCOUNTS.items():

    tweets=obtener_tweets(account,guest_token)
    if not tweets:
        continue

    last_id=get_last_id(account)
    nuevos=[]

    for t in tweets:
        id=t["id_str"]
        if id==last_id:
            break
        nuevos.append(t)

    if not nuevos:
        continue

    nuevos.reverse()

    for t in nuevos:
        texto,articulo=limpiar_texto(t["full_text"])
        tweet_url=f"https://fxtwitter.com/{account}/status/{t['id_str']}"
        botones=crear_botones(tweet_url,articulo)

        media=t.get("extended_entities",{}).get("media",[])

        if media:
            m=media[0]
            if m["type"]=="photo":
                send_photo(chat_id,texto,m["media_url_https"],botones)
            elif m["type"]=="video":
                send_video(chat_id,texto,m["video_info"]["variants"][0]["url"],botones)
            else:
                send_message(chat_id,texto,botones)
        else:
            send_message(chat_id,texto,botones)

    save_last_id(account,nuevos[-1]["id_str"])
