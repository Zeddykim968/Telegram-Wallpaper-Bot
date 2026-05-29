import os
import random
import json
import requests
import asyncio

from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Application
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

DATABASE_FILE = "data/posted_wallpapers.json"


# ----------------------------
# DATABASE FUNCTIONS
# ----------------------------
def load_posted_ids():
    try:
        with open(DATABASE_FILE, "r") as file:
            data = json.load(file)
            return data.get("posted_ids", [])
    except FileNotFoundError:
        return []


def save_posted_ids(posted_ids):
    os.makedirs("data", exist_ok=True)

    with open(DATABASE_FILE, "w") as file:
        json.dump({"posted_ids": posted_ids}, file, indent=4)


# ----------------------------
# MAIN WALLPAPER FUNCTION
# ----------------------------
async def send_daily_wallpaper():

    bot = Bot(token=BOT_TOKEN)

    print("Fetching wallpapers...")

    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": "4k wallpaper",
        "per_page": 80
    }

    response = requests.get(url, headers=headers, params=params, timeout=20)
    data = response.json()

    photos = data.get("photos", [])

    if not photos:
        print("No photos found.")
        return

    # Load already posted IDs
    posted_ids = load_posted_ids()

    # Filter duplicates
    new_photos = [
        photo for photo in photos
        if photo["id"] not in posted_ids
    ]

    if not new_photos:
        print("No new wallpapers available.")
        return

    # Pick random new wallpaper
    photo = random.choice(new_photos)

    # Save ID
    posted_ids.append(photo["id"])
    save_posted_ids(posted_ids)

    # Safer image size
    image_url = photo["src"]["medium"]

    print("Downloading image...")

    image_response = requests.get(image_url, timeout=20)
    image_data = image_response.content

    # Save temporarily
    image_path = "wallpaper.jpg"

    with open(image_path, "wb") as file:
        file.write(image_data)

    print("Sending to Telegram...")

    with open(image_path, "rb") as photo_file:
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=photo_file,
            caption="🔥 Here is your Daily Wallpaper! Enjoy your day! 🔥"
        )

    print("Wallpaper posted successfully!")


# ----------------------------
# SCHEDULER + MAIN LOOP
# ----------------------------
async def main():



    scheduler = AsyncIOScheduler()

    # Change this for testing (e.g. minutes=1)
    scheduler.add_job(
        send_daily_wallpaper,
        "interval",
        hours=6
    )

    scheduler.start()

    print("Bot is running...")

    app = Application.builder().token(BOT_TOKEN).build()

    await app.run_polling()

    # Keep program alive
    while True:
        await asyncio.sleep(60)


# Run bot
asyncio.run(main())