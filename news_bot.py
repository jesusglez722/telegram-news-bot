import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# RSS Google News búsqueda
RSS_URL = "https://news.google.com/rss/search?q=stock+market&hl=en-US&gl=US&ceid=US:en"

# Para evitar duplicados
seen_links = set()


def get_real_article_url(google_link):
    """
    Extrae la URL real del artículo desde el redirect de Google News
    """
    try:
        parsed = urlparse(google_link)
        if "news.google.com" in parsed.netloc:
            return google_link  # algunos ya vienen limpios

        # Google usa parámetro url= o ?u=
        query = parse_qs(parsed.query)
        if "url" in query:
            return query["url"][0]

        return google_link
    except:
        return google_link


def scrape_article_image(url):
    """
    Entra al artículo y busca la imagen og:image (la real)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")

        og = soup.find("meta", property="og:image")
        if og and og.get("content"):
            return og["content"]

        # fallback twitter:image
        tw = soup.find("meta", property="twitter:image")
        if tw and tw.get("content"):
            return tw["content"]

    except:
        pass

    return None


def get_image_from_entry(entry):
    """
    Primero intenta RSS → si no existe → scraping real
    """

    # 1️⃣ intentar RSS
    if "media_content" in entry:
        return entry.media_content[0]["url"]

    if "media_thumbnail" in entry:
        return entry.media_thumbnail[0]["url"]

    # 2️⃣ scraping del artículo (la clave del fix)
    real_url = get_real_article_url(entry.link)
    img = scrape_article_image(real_url)

    return img


def get_news():
    feed = feedparser.parse(RSS_URL)
    news_list = []

    for entry in feed.entries:

        real_url = get_real_article_url(entry.link)

        # 🚫 eliminar duplicados (WSJ etc)
        if real_url in seen_links:
            continue
        seen_links.add(real_url)

        image = get_image_from_entry(entry)

        news_list.append({
            "title": entry.title,
            "link": real_url,
            "image": image
        })

    return news_list


# --- PROBAR ---
news = get_news()

for n in news[:10]:
    print("📰", n["title"])
    print("🔗", n["link"])
    print("🖼️", n["image"])
    print("----")
