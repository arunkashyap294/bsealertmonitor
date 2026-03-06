"""
get_telegram_chat_id.py
Run this after:
  1. Creating your bot via @BotFather
  2. Sending /start to your bot in Telegram

Usage: py get_telegram_chat_id.py
"""
import requests

# ← Paste your Bot Token here (from @BotFather)
BOT_TOKEN = "8762316720:AAG4zXbJdOX3Sr5TMyjukAwKicLO2Wk0-KY"

if BOT_TOKEN == "P8762316720:AAG4zXbJdOX3Sr5TMyjukAwKicLO2Wk0-KY":
    print("❌ Please open this file and paste your Bot Token on the BOT_TOKEN line.")
    exit(1)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
print(f"Calling: {url}\n")

response = requests.get(url, timeout=10)
data = response.json()

if not data.get("ok"):
    print(f"❌ Error from Telegram: {data}")
    exit(1)

messages = data.get("result", [])
if not messages:
    print("⚠️  No messages found.")
    print("Make sure you have sent /start to your bot in Telegram, then run this again.")
else:
    print("✅ Found the following chats:\n")
    seen = set()
    for update in messages:
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        chat_name = chat.get("first_name") or chat.get("title") or "Unknown"
        if chat_id and chat_id not in seen:
            seen.add(chat_id)
            print(f"  Chat Name : {chat_name}")
            print(f"  Chat ID   : {chat_id}")
            print(f"  → Add to .env:  TELEGRAM_CHAT_ID={chat_id}\n")
