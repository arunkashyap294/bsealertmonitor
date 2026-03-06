# BSE Corporate Announcement Monitor 🔔

Monitors BSE India for new corporate announcements and sends instant **Telegram** alerts with an AI-generated summary of each official document.

---

## Features

- ✅ **Multi-company monitoring** — track any number of BSE-listed companies (by scrip code)
- ✅ **Configurable polling interval** — run it every 5, 10, or 15 minutes
- ✅ **Smart deduplication** — remembers what it's already sent so you never get duplicates
- ✅ **AI summaries** — Google Gemini 2.5 Flash reads the exact PDFs and returns a 3-5 bullet point summary of exactly what the announcement contains
- ✅ **Telegram alerts** — totally free, unlimited, real-time push notifications delivered to your phone
- ✅ **Cloud ready** — ready to run 24/7 as a background process on a free Google Cloud VM

---

## Quick Setup

### 1. Install Dependencies

```bash
git clone https://github.com/YOUR_USERNAME/tijori-alerts.git
cd tijori-alerts

# Create a virtual environment (Required on newer Linux/Ubuntu)
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API Keys

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```ini
# Google Gemini API Key
# Get your key from: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key

# Telegram Bot Token & Chat ID
# See "Telegram Bot Setup" below
TELEGRAM_BOT_TOKEN=123456:xxxxx_xxxxxxxxxxxx
TELEGRAM_CHAT_ID=123456789
```

### 3. Configure Companies to Monitor

Edit `config.yaml` to track your desired stocks:

```yaml
interval_minutes: 10  # Check every 10 minutes

companies:
  - name: "Utkarsh Small Finance Bank"
    scripcode: "543942"
  - name: "Infosys"
    scripcode: "500209"
```

> **Finding a scrip code**: Go to a stock's page on the BSE website. The 6-digit number in the URL is the scrip code. Example: `bseindia.com/.../`**543942**`/`

---

## Telegram Bot Setup (Free & Unlimited)

1. Open Telegram and search for **@BotFather**
2. Send the message `/newbot` and follow the prompts to give your bot a name and username.
3. BotFather will give you a **HTTP API Token** (this goes into `TELEGRAM_BOT_TOKEN`).
4. **Important:** Search for your new bot in Telegram and send it the message `/start`. It cannot message you until you do this!
5. To get your **Chat ID**, run the included helper script:
   ```bash
   python get_telegram_chat_id.py
   ```
   *Follow the instructions in the script to find your ID, then add it to `.env` as `TELEGRAM_CHAT_ID`.*

---

## Running the Monitor

You can run the script manually or leave it running continuously.

```bash
# Start the scheduler (runs continuously every X minutes)
python monitor.py

# Test: run one polling cycle and exit
python monitor.py --run-once

# Fetch announcements from the last 2 days
python monitor.py --lookback-hours 48

# Send a test Telegram message to verify your bot is set up
python monitor.py --test-whatsapp

# Show all configured companies
python monitor.py --list-companies
```

---

## Project Structure

```
tijori_alerts/
├── monitor.py            # Main entry point + scheduler
├── bse_scraper.py        # BSE India announcement fetcher + PDF downloader
├── summarizer.py         # Google Gemini document summarizer
├── whatsapp_notifier.py  # Telegram sender (legacy file name)
├── state_manager.py      # Deduplication logic (tracks seen announcements)
├── config.yaml           # Companies and polling interval list
├── .env                  # API keys (never commit this!)
└── logs/
    └── monitor.log       # Activity log
```

---

## Sample Telegram Alert

```
📢 Corporate Announcement Alert
━━━━━━━━━━━━━━━━━━━━━━
🏢 Company: Utkarsh Small Finance Bank
📅 Date: 26 Feb 2026, 09:30 AM
🏷️ Category: Board Meeting
📝 Subject: Notice Of The NCLT Convened Meeting

📄 View Document (link)

📊 Summary:
• The Board of Directors convened a meeting regarding the merger
• Timeline has been set for March 28, 2026
• Voting results will be submitted within 48 hours
━━━━━━━━━━━━━━━━━━━━━━
Powered by Corporate Announcement Monitor
```
