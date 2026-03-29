import feedparser
import requests
import os

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
    if not os.path.exists(file):
        return ""
    with open(file, "r") as f:
        return f.read().strip()

def save_last_link(account, link):
    file = f"last_{account}.txt"
    with open(file, "w") as f:
        f.write(link)

def send_telegram(chat_id, msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": msg})

for account, chat_id in ACCOUNTS.items():
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
            message = f"📰 @{account}\n{post.title}\n{post.link}"
            send_telegram(chat_id, message)

        save_last_link(account, new_posts[-1].link)
