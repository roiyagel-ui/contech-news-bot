import asyncio
import json
import os
import re
import time
from bs4 import BeautifulSoup
import feedparser
import requests
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
HISTORY_FILE = "sent_contech_articles.json"
LAST_HEARTBEAT_FILE = "last_heartbeat.json"

# חיווי הישרדות: 6 שעות בשניות (6 * 3600 = 21600)
HEARTBEAT_INTERVAL = 21600

# Header למניעת חסימת סורקים (User-Agent Simulation)
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

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
    # 3. ערים חכמות והתחדשות עירונית (Smart Cities & Urban Renewal)
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
    "Urban Renewal",
    "התחדשות עירונית",
    "Sustainable Urban",
    "Urban Infrastructure",
    "Eurocities",
    # 4. בנייה טרומית, מודולרית ומתועשת (Prefabricated, Modular & Robotics)
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
    "Smart Construction",
    "Construction Robot",
    "רובוטיקה בבנייה",
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
    # 6. תשתיות לאומיות, מגה-פרויקטים וחידושים מסין והעולם
    "מנהור",
    "Tunnelling",
    "TBM",
    "גשרים",
    "רכבת קלה",
    "מטרו",
    "תשתיות לאומיות",
    "Civil Engineering",
    "הנדסה אזרחית",
    "Mega Projects",
    "Infrastructure Funding",
    "China Infrastructure",
    "Chinese Construction",
    "High-speed Rail",
    "תשתיות בסין",
]

# מקורות מידע גלובליים - ארה"ב, אירופה, סין וישראל
RSS_FEEDS = [
    # --- סין (Chinese Official Feeds - Infrastructure & Tech Innovation) ---
    "http://www.xinhuanet.com/english/rss/businessrss.xml",  # Xinhua English - Business & Mega Infra
    "http://www.xinhuanet.com/english/rss/sciencerss.xml",  # Xinhua English - Science, Smart Tech & Innovation
    "http://www.chinadaily.com.cn/rss/cndy_rss.xml",  # China Daily - National Developments & Infrastructure
    # --- ארה"ב (US Premier InfraTech & ConTech) ---
    "https://www.constructiondive.com/feeds/news/",  # Construction Dive US
    "https://techcrunch.com/category/construction/feed/",  # TechCrunch ConTech
    "https://www.enr.com/rss/all",  # Engineering News-Record (ENR US)
    "https://www.bdcnetwork.com/rss.xml",  # Building Design+Construction
    "https://www.builtworlds.com/feed/",  # BuiltWorlds US
    "https://www.asce.org/rss/civil-engineering-magazine/",  # ASCE American Society of Civil Engineers
    # --- אירופה (European Urban Renewal, Infra & Tech) ---
    "https://www.globalconstructionreview.com/feed/",  # Global Construction Review (UK/Europe)
    "https://www.infrastructure-intelligence.com/rss.xml",  # Infrastructure Intelligence Europe
    "https://eurocities.eu/feed/",  # Eurocities - התחדשות וערים חכמות באירופה
    "https://www.gim-international.com/rss.xml",  # Geospatial, BIM & Mapping Europe
    "https://www.cece.eu/feed",  # Committee for European Construction Equipment
    # --- ישראל (Local Ecosystem) ---
    "https://www.civileng.co.il/rss",  # CivilEng Israel
    "https://www.calcalist.co.il/Integration/RED/rssC2C.xml",  # כלכליסט טכנולוגיה
    "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeedsProviders?FolderID=3312",  # גלובס תשתיות
    "https://www.pc.co.il/feed/",  # אנשים ומחשבים
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


def get_last_heartbeat():
  if os.path.exists(LAST_HEARTBEAT_FILE):
    try:
      with open(LAST_HEARTBEAT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("last_sent", 0)
    except Exception as e:
      print(f"Error loading heartbeat file: {e}")
      return 0
  return 0


def save_last_heartbeat(timestamp):
  with open(LAST_HEARTBEAT_FILE, "w", encoding="utf-8") as f:
    json.dump({"last_sent": timestamp}, f, ensure_ascii=False, indent=2)


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
  now = time.time()

  for feed_url in RSS_FEEDS:
    print(f"Scanning feed: {feed_url}")
    try:
      response = requests.get(feed_url, headers=FETCH_HEADERS, timeout=15)
      if response.status_code != 200:
        print(
            f"Warning: HTTP {response.status_code} when fetching {feed_url}"
        )
        continue

      feed = feedparser.parse(response.content)

      for entry in feed.entries:
        link = entry.get("link", "")
        title = entry.get("title", "")
        summary = clean_html(entry.get("summary", ""))

        if not link or link in sent_articles:
          continue

        if is_relevant(title, summary):
          msg = (
              f"🏗️ **חדשנות, תשתיות והתחדשות (ConTech Global)**\n\n*{title}*\n\n[לקריאת"
              f" הכתבה المלאה]({link})"
          )
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
    save_last_heartbeat(now)
    print(f"Saved {new_sent_count} new articles.")
  else:
    print("No new relevant articles found.")
    last_heartbeat = get_last_heartbeat()
    if (now - last_heartbeat) >= HEARTBEAT_INTERVAL:
      try:
        heartbeat_msg = (
            "🔍 **סריקה תקופתית:** הבוט סרק בהצלחה את כל מקורות המידע בארה\"ב,"
            " אירופה, סין וישראל. לא נמצאו כתבות חדשות ב-6 השעות האחרונות."
        )
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=heartbeat_msg,
            parse_mode="Markdown",
        )
        save_last_heartbeat(now)
        print("Sent 6-hour heartbeat status message.")
      except Exception as e:
        print(f"Failed to send heartbeat message: {e}")


if __name__ == "__main__":
  asyncio.run(fetch_and_send())
