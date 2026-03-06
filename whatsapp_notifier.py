"""
notifier.py (formerly whatsapp_notifier.py)
Sends Telegram notifications via the free Telegram Bot API.

Setup:
1. Create a bot via @BotFather on Telegram → get BOT_TOKEN
2. Send /start to your bot in Telegram
3. Run get_telegram_chat_id.py to find your CHAT_ID
4. Add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to your .env
"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_API_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_whatsapp_alert(
    to_number: str,
    company_name: str,
    announcement_title: str,
    announcement_date: str,
    announcement_category: str,
    pdf_url: str,
    listing_url: str,
    summary: str,
) -> bool:
    """
    Send a Telegram message with announcement details.
    (Parameter names kept for compatibility with monitor.py)
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error(
            "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env"
        )
        return False

    message_body = _format_message(
        company_name,
        announcement_title,
        announcement_date,
        announcement_category,
        pdf_url,
        listing_url,
        summary,
    )

    try:
        logger.info("Sending Telegram message to chat %s ...", TELEGRAM_CHAT_ID)
        response = requests.post(
            TELEGRAM_API_URL,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message_body,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )

        if response.status_code == 200:
            logger.info("Telegram message sent successfully")
            return True
        else:
            logger.error(
                "Telegram returned HTTP %s: %s",
                response.status_code,
                response.text[:300],
            )
            return False

    except requests.RequestException as e:
        logger.error("Telegram request failed: %s", e)
        return False


def _format_message(
    company_name: str,
    title: str,
    date_str: str,
    category: str,
    pdf_url: str,
    listing_url: str,
    summary: str,
) -> str:
    """Format the Telegram message using Markdown."""

    # Telegram has a 4096 character limit — trim summary if needed
    summary_trimmed = summary[:1200] + "..." if len(summary) > 1200 else summary

    doc_line = f"[📄 View Document]({pdf_url})" if pdf_url else f"[🔗 View Listing]({listing_url})"

    message = (
        f"📢 *Corporate Announcement Alert*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 *Company:* {company_name}\n"
        f"📅 *Date:* {date_str}\n"
        f"🏷️ *Category:* {category}\n"
        f"📝 *Subject:* {title}\n"
        f"\n"
        f"{doc_line}\n"
        f"\n"
        f"📊 *Summary:*\n"
        f"{summary_trimmed}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Powered by Corporate Announcement Monitor_"
    )

    return message


def send_test_message(to_number: str) -> bool:
    """Send a test Telegram message to verify credentials and setup."""
    return send_whatsapp_alert(
        to_number=to_number,
        company_name="TEST COMPANY LTD",
        announcement_title="Test Announcement - System Check",
        announcement_date="25 Feb 2026, 07:12 PM",
        announcement_category="Test",
        pdf_url="https://www.bseindia.com/",
        listing_url="https://www.bseindia.com/",
        summary="• This is a test message from your Corporate Announcement Monitor.\n• If you received this, Telegram notifications are working correctly! ✅",
    )
