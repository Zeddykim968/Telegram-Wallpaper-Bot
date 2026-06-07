import os
import random
import json
import requests
import asyncio

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

# THEMES

Themes = {
    "nature":    ("Nature HD"),
    "city":      ("City HD"),
    "cars":      ("Cars HD"),
    "space":     ("Space HD"),
    "ocean":     ("Ocean HD"),
    "mountains": ("Mountains HD"),
    "architecture":  ("Architecture HD"),
    "animals":   ("Animals HD"),
    "forest":    ("Forest HD"),
    "Sunset":    ("Sunset HD"),
    "Thechnology":  ("Technology HD"),
    "abstract":  ("Abstract HD"),
    "programming":  ("Programming"),

}


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
        image_url = photo["src"]["large2x"]
        image_path = f"wallpaper_{i}.jpg"

        try:
            image_response = requests.get(image_url, timeout=20)
            with open(image_path, "wb") as file:
                file.write(image_response.content)

            caption = (
                f"{theme_emoji} *{theme_label} Wallpaper {i + 1}/{len(selected)}*\n"
                f"Enjoy your wallpaper of the day! 🔥"
            )

            with open(image_path, "rb") as photo_file:
                await bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=photo_file,
                    caption=caption,
                    parse_mode="Markdown"
                )

            print(f"  ✓ Photo {i + 1} sent.")

        except Exception as e:
            print(f"  ✗ Failed to send photo {i + 1}: {e}")

        finally:
            if os.path.exists(image_path):
                os.remove(image_path)

        # Small delay between sends to avoid Telegram rate limits
        await asyncio.sleep(2)

    # Update posted IDs for this theme
    posted_ids.extend([p["id"] for p in selected])
    save_posted_ids_for_theme(db, theme_key, posted_ids)

    print(f"Done! {len(selected)} wallpapers posted for theme: {theme_label}")    



    

# SCHEDULER + MAIN LOOP

scheduler = AsyncIOScheduler()

async def main():
    
    scheduler.add_job(
        send_daily_wallpaper,
        "interval",
        hours=4
    )

    scheduler.start()

    print("Bot is running...")

    while True:
        await ayncio.sleep(60)

    

if __name__ == "__main__":
    asyncio.run(main())  




    