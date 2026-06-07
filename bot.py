import os
import random
import json
import requests
import asyncio
import traceback

from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing")


CHANNEL_ID = os.getenv("CHANNEL_ID")

if not CHANNEL_ID:
    raise ValueError("CHANNEL_ID missing")

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

if not PEXELS_API_KEY:
    raise ValueError("PEXELS_API_KEY missing")

DATABASE_FILE = "data/posted_wallpapers.json"

PHOTOS_PER_POST = 5

# THEMES

THEMES = {
    "nature": ("🌿", "Cool Nature HD"),
    "city": ("🏙️", "Cool City HD"),
    "cars": ("🚗", "Cool Cars HD"),
    "space": ("🚀", "Cool Space HD"),
    "ocean": ("🌊", "Cool Ocean HD"),
    "mountains": ("⛰️", "Cool Mountains HD"),
    "architecture": ("🏛️", "Cool Architecture HD"),
    "animals": ("🐾", "Cool Animals HD"),
    "forest": ("🌲", "Cool Forest HD"),
    "sunset": ("🌅", "Cool Sunset HD"),
    "technology": ("💻", "Cool Technology HD"),
    "abstract": ("🎨", "Cool Abstract HD"),
    "programming": ("⌨️", "Cool Programming HD"),
}

def get_quote():
    try:
        response = requests.get("https://zenquotes.io/api/random", timeout=10)

        response.raise_for_status()

        data = response.json()[0]
        quote = data["q"]
        author = data["a"]

        return f'"{quote}"\n- {author}'

    except Exception as e:
        fallback_quote = [
            "The only way to do great work is to love what you do. - Steve Jobs",
            "In the middle of every difficulty lies opportunity. - Albert Einstein",
            "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
            "Believe you can and you're halfway there. - Theodore Roosevelt",
            "Your time is limited, so don't waste it living someone else's life. - Steve Jobs",
            "The best way to predict the future is to invent it. - Alan Kay",
            "Don't watch the clock; do what it does. Keep going. - Sam Levenson",
            "The harder you work for something, the greater you'll feel when you achieve it. - Vince Lombardi"
        ]

        return f'"{random.choice(fallback_quote)}"'


# ----------------------------
# DATABASE FUNCTIONS
# ----------------------------
def load_db():
    """Load the full DB: { posted_ids: { theme: [id, ...] } }"""
    try:
        with open(DATABASE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"posted_ids": {}}


def save_db(db):
    os.makedirs("data", exist_ok=True)
    with open(DATABASE_FILE, "w") as f:
        json.dump(db, f, indent=4)


def get_posted_ids_for_theme(db, theme):
    return db["posted_ids"].get(theme, [])


def save_posted_ids_for_theme(db, theme, ids):
    db["posted_ids"][theme] = ids
    save_db(db)


# FETCH PHOTOS

def fetch_photos(theme_key, page=1):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": f"{theme_key} 4k wallpaper",
        "per_page": 80,
        "page": page,
    }
    response = requests.get(url, headers=headers, params=params, timeout=20)
    data = response.json()
    return data.get("photos", [])
 



# MAIN WALLPAPER FUNCTION


async def send_daily_wallpaper():

    bot = Bot(token=BOT_TOKEN)

    # Pick a random theme for this run
    theme_key = random.choice(list(THEMES.keys()))
    theme_emoji, theme_label = THEMES[theme_key]

    print(f"Theme: {theme_label} | Fetching photos...")

    db = load_db()
    posted_ids = get_posted_ids_for_theme(db, theme_key)


    # Fetch page 1
    photos = fetch_photos(theme_key, page=1)

    if not photos:
        print(f"No photos returned for theme '{theme_label}'. Skipping.")
        return

    # Filter new photos
    new_photos = [p for p in photos if p["id"] not in posted_ids]

    # If not enough new photos, try page 2
    if len(new_photos) < PHOTOS_PER_POST:
        print(f"Not enough new photos ({len(new_photos)}), fetching page 2...")
        page2 = fetch_photos(theme_key, page=2)
        new_photos += [p for p in page2 if p["id"] not in posted_ids]

    # If still not enough, reset this theme's history and use all from page 1
    if len(new_photos) < PHOTOS_PER_POST:
        print(f"Theme '{theme_label}' exhausted — resetting history and reusing photos.")
        posted_ids = []
        new_photos = photos  


    # Pick PHOTOS_PER_POST random photos (no repeats within the batch)
    selected = random.sample(new_photos, min(PHOTOS_PER_POST, len(new_photos)))

    print(f"Sending {len(selected)} photos for theme: {theme_label}...")

    for i, photo in enumerate(selected):
        image_url = photo["src"]["large"] or photo["src"]["medium"] or photo["src"]["original"]  # Try different sizes if needed
        image_path = f"wallpaper_{i}.jpg"

        try:
            image_response = requests.get(image_url, timeout=20)
            with open(image_path, "wb") as file:
                file.write(image_response.content)

            quote_caption = (
                f"{theme_emoji} *{theme_label}*\n\n"
                f"{get_quote()}\n\n"
                f"_Photo by {photo['photographer']} on Pexels_"
            )

            with open(image_path, "rb") as photo_file:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo_file,
                    caption=quote_caption,
                    parse_mode="Markdown",
                    
                )

            print(f"  ✓ Photo {i + 1} sent.")

        except Exception as e:
            print(f"  ✗ Failed to send photo {i + 1}")
            traceback.print_exc()

        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

        # Small delay between sends to avoid Telegram rate limits
        await asyncio.sleep(2)

    # Update posted IDs for this theme
    successfuly_sent = []
    successfuly_sent.extend([photo["id"] for photo in selected])
    posted_ids.extend(successfuly_sent)
    save_posted_ids_for_theme(db, theme_key, posted_ids)

    print(f"Done! {len(selected)} wallpapers posted for theme: {theme_label}")    



    

# SCHEDULER + MAIN LOOP

scheduler = AsyncIOScheduler()

async def main():

    await send_daily_wallpaper()  # Send immediately on startup
    
    scheduler.add_job(
        send_daily_wallpaper,
        "interval",
        hours=4
    )

    scheduler.start()

    print("Bot is running...")

    while True:
        await asyncio.sleep(60)

    

if __name__ == "__main__":
    asyncio.run(main())  




    