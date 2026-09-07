import asyncio
import json
import os
import re
from bs4 import BeautifulSoup
import feedparser
import requests
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
HISTORY_FILE = "sent_contech_articles.json"

KEYWORDS = [
    # 1. סטארטאפים, יזמות והשקעות (ConTech & InfraTech Startups)
    "ConTech startup",
    "InfraTech startup",
    "סטארטאפ בנייה",
    "סטארט-אפ בנייה",
    "סטארטאפ תשתיות",
    "חברת הזנק",
    "גיוס הון",
    "סבב גיוס",
    "Seed round",
    "Series A",
    "Series B",
    "Venture Capital",
    "VC",
    "קרן הון סיכון",
    "חממה טכנולוגית",
    "Incubator",
    "Accelerator",
    "אקסלרטור",
    "PropTech",
    "פרופטק",

    # 2. מושגים כלליים ותחומים
    "ConTech",
    "InfraTech",
    "קונטק",
    "אינפרטק",
    "חדשנות בבנייה",
    "טכנולוגיות בנייה",
    "בנייה חכמה",
    "תשתיות חכמות",
    "Smart Infrastructure",
    "Construction Tech",

    # 3. ערים חכמות (Smart Cities)
    "עיר חכמה",
    "ערים חכמות",
    "Smart City",
    "Smart Cities",
    "UrbanTech",
    "אורבנטק",
    "ניהול עירוני חכם",
    "תחבורה חכמה",
    "Smart Mobility",
    "IoT עירוני",
    "Smart Grid",
    "רשת חשמל חכמה",
    "Smart Lighting",

    # 4. בנייה טרומית, מודולרית ומתועשת
    "בנייה טרומית",
    "רכיבים טרומיים",
    "אלמנטים טרומיים",
    "Prefabrication",
    "Prefab",
    "Offsite Construction",
    "בנייה מתועשת",
    "Modular Housing",
    "בנייה מודולרית",
    "Industrialized Building",
    "3D Volumetric Construction",
    "DFMA",

    # 5. טכנולוגיות וטרנדים מתקדמים
    "BIM",
    "Digital Twin",
    "תאומה דיגיטלית",
    "הדפסה בתלת ממד",
    "3D Printing",
    "3D Concrete Printing",
    "בטון ירוק",
    "Green Concrete",
    "Autonomous Construction",
    "ציוד אוטונומי",
    "רחפנים בבנייה",
    "Drone Mapping",
    "Structural Monitoring",
    "חיישנים בתשתיות",
    "סריקת לייזר",
    "Laser Scanning",
    "AI in Construction",

    # 6. תשתיות לאומיות ופרויקטים מורכבים
    "מנהור",
    "Tunnelling",
    "TBM",
    "גשרים",
    "רכבת קלה",
    "מטרו",
    "תשתיות לאומיות",
    "Civil Engineering",
    "הנדסה אזרחית",
]

RSS_FEEDS = [
    # חדשות ConTech וסטארטאפים בעולם
    "https://www.constructiondive.com/feeds/news/",
    "https://techcrunch.com/category/construction/feed/",
    "https://www.builtworlds.com/feed/",
    "https://www.enr.com/rss/all",
    "https://www.bdcnetwork.com/rss.xml",
    # חדשות וסטארטאפים בישראל
    "https://www.civileng.co.il/rss",
    "https://www.calcalist.co.il/Integration/RED/rssC2C.xml",
    "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeedsProviders?FolderID=3312",
]


def load_sent_articles():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception as e:
            print(f"Error loading history: {e}")
            return set()
    return set()


def save_sent_articles(sent_set):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(list(sent_set), f, ensure_ascii=False, indent=2)


def is_relevant(title, summary):
    text = f"{title} {summary}"
    for kw in KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE):
            return True
    return False


def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ").strip()


async def fetch_and_send():
    if not TELEGRAM_TOKEN or not CHANNEL_ID:
        print("CRITICAL ERROR: TELEGRAM_TOKEN or CHANNEL_ID is missing!")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    sent_articles = load_sent_articles()
    new_sent_count = 0

    for feed_url in RSS_FEEDS:
        print(f"Scanning feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                link = entry.get("link", "")
                title = entry.get("title", "")
                summary = clean_html(entry.get("summary", ""))

                if not link or link in sent_articles:
                    continue

                if is_relevant(title, summary):
                    msg = f"🏗️ **חדשנות, סטארטאפים ותשתיות (ConTech)**\n\n*{title}*\n\n[לקריאת הכתבה المלאה]({link})"
                    try:
                        await bot.send_message(
                            chat_id=CHANNEL_ID,
                            text=msg,
                            parse_mode="Markdown",
                        )
                        print(f"Sent: {title}")
                        sent_articles.add(link)
                        new_sent_count += 1
                        await asyncio.sleep(2)
                    except Exception as e:
                        print(f"Failed to send message: {e}")

        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")

    if new_sent_count > 0:
        save_sent_articles(sent_articles)
        print(f"Saved {new_sent_count} new articles.")
    else:
        print("No new relevant articles found.")


if __name__ == "__main__":
    asyncio.run(fetch_and_send())
