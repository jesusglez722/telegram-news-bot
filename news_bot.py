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
    "TheEconomist": "-1003897620126"
}

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ─────────────────────────────
def get_last_id(account):
    file = f"last_{account}.txt"
    if not os.path.exists(file):
        return ""
    return open(file).read().strip()

def save_last_id(account, tweet_id):
    open(f"last_{account}.txt","w").write(tweet_id)

# ─────────────────────────────
def crear_botones(tweet_url, articulo_url):
    if articulo_url:
        kb = {"inline_keyboard":[[
            {"text":"🐦 Ver tweet","url":tweet_url},
            {"text":"📰 Leer artículo","url":articulo_url}
        ]]}
    else:
        kb = {"inline_keyboard":[[
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

def send_video(chat_id,text,path,buttons=None):
    with open(path,"rb") as v:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
        data={"chat_id":chat_id,"caption":text,"parse_mode":"HTML","reply_markup":buttons},
        files={"video":v})
    os.remove(path)
    time.sleep(2)

# ─────────────────────────────
def descargar_video(url):
    name="video.mp4"
    r=requests.get(url,stream=True,timeout=60)
    with open(name,"wb") as f:
        for c in r.iter_content(1024):
            f.write(c)
    return name

# ─────────────────────────────
def limpiar_texto(texto):
    links=re.findall(r'https?://\S+',texto)
    articulo=links[0] if links else ""
    texto=re.sub(r'https?://\S+','',texto).strip()
    return texto,articulo

# ─────────────────────────────
def obtener_tweets(account):
    url=f"https://nitter.net/{account}/tweets?json=true"
    return requests.get(url,headers=HEADERS,timeout=20).json()["tweets"]

# ─────────────────────────────
for account,chat_id in ACCOUNTS.items():

    tweets=obtener_tweets(account)
    last_id=get_last_id(account)
    nuevos=[]

    for t in tweets:
        if t["id"]==last_id:
            break
        nuevos.append(t)

    if not nuevos:
        continue

    nuevos.reverse()

    for t in nuevos:
        texto,articulo=limpiar_texto(t["text"])
        tweet_url=f"https://fxtwitter.com/{account}/status/{t['id']}"
        botones=crear_botones(tweet_url,articulo)

        # VIDEO
        if t["videos"]:
            video_url=t["videos"][0]["url"]
            video_file=descargar_video(video_url)
            send_video(chat_id,texto,video_file,botones)

        # FOTO
        elif t["pictures"]:
            send_photo(chat_id,texto,t["pictures"][0],botones)

        else:
            send_message(chat_id,texto,botones)

    save_last_id(account,nuevos[-1]["id"])
