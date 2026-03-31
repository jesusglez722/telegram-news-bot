import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import time

RSS_URL = "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en"

seen_links = set()

def get_real_article_url(google_link):
    try:
        parsed = urlparse(google_link)

        if "news.google.com" not in parsed.netloc:
            return google_link

        query = parse_qs(parsed.query)
        if "url" in query:
            return query["url"][0]

        return google_link
    except:
        return google_link


def scrape_article_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")

        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]

        tw = soup.find("meta", property="twitter:image")
        if tw and tw.get("content"):
            return tw["content"]

    except:
        pass

    return None


def get_image_from_entry(entry):
    if "media_content" in entry:
        return entry.media_content[0]["url"]

    if "media_thumbnail" in entry:
        return entry.media_thumbnail[0]["url"]

    real_url = get_real_article_url(entry.link)
    return scrape_article_image(real_url)


def get_news():
    feed = feedparser.parse(RSS_URL)
    news_list = []

    for entry in feed.entries:
        real_url = get_real_article_url(entry.link)

        if real_url in seen_links:
            continue
        seen_links.add(real_url)

        image = get_image_from_entry(entry)

        news_list.append({
            "title": entry.title,
            "link": real_url,
            "image": image
        })

        time.sleep(1)  # evita bloqueos por scraping

    return news_list


if __name__ == "__main__":
    news = get_news()

    for n in news[:5]:
        print("📰", n["title"])
        print("🔗", n["link"])
        print("🖼️", n["image"])
        print("-----")
