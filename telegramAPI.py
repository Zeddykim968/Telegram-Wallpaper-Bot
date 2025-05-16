# This is a simple Telegram bot that fetches random wallpapers from Pexels and posts them to a Telegram channel.
from gettext import install

# auto_wallpaper_bot.py


from json import requests
import json
from telethon import TelegramClient
import random
from os import schedule
import os
import time
from telegramAPI import Bot

#add your telegram API details


api_id = 28110360     # e.g., 123456
api_hash = 'd2afc1392941de3c8c569e2f15927a47'   # e.g., 'abcdef123456...'

with TelegramClient('my_session', api_id, api_hash) as client:
    client.send_message('me', 'Hello from the Telegram API!')


#add your pexels API details
PEXELS_API_KEY = "NL7CEDeaLYhstGAtzBa9BKpB6Iolp7sjS9XHXP6IHRMmlWSB05Wgt1rL"
TELEGRAM_BOT_TOKEN = "7394303574:AAFQPARBk3HputYnifbxGBpi-UkDpSzFikY"
TELEGRAM_CHANNEL_USERNAME = "@cool_4K_HDwallpaper"  # e.g., "@mywallpapershd"


# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def get_random_wallpaper():
    headers = {
        "Authorization": PEXELS_API_KEY
    }

    query = "4k wallpaper"
    per_page = 20
    page = random.randint(1, 20)

    url = f"https://api.pexels.com/v1/search?query={query}&per_page={per_page}&page={page}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        photos = data.get("photos", [])
        if photos:
            photo = random.choice(photos)
            return photo["src"]["original"], photo["photographer"]
    return None, None

def post_wallpaper():
    image_url, photographer = get_random_wallpaper()
    if image_url:
        caption = f"📸 Photographer: {photographer}\n🖼️ Source: Pexels\n#4K #Wallpaper #HD"
        bot.send_photo(chat_id=TELEGRAM_CHANNEL_USERNAME, photo=image_url, caption=caption)
        print("✅ Posted a wallpaper to the channel.")
    else:
        print("❌ Failed to fetch wallpaper.")

# Schedule to post every 2 hours
schedule.every(2).hours.do(post_wallpaper)

# Run immediately on startup
post_wallpaper()

# Keep running the scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
