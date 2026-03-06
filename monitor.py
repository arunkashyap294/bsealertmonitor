"""
monitor.py — Corporate Announcement Monitor
===========================================
Main entry point. Run this script to start monitoring BSE corporate announcements.

Usage:
    python monitor.py                  # Start the scheduler (runs forever)
    python monitor.py --run-once       # One polling cycle (good for testing)
    python monitor.py --test-whatsapp  # Send a test WhatsApp message and exit
    python monitor.py --list-companies # Print configured companies and exit
"""

import argparse
import logging
import sys
import time
from datetime import datetime, date
from pathlib import Path

import yaml
import schedule
from dotenv import load_dotenv

# Load .env before importing our modules
load_dotenv()

from bse_scraper import get_recent_announcements, download_pdf_text
from state_manager import is_new, mark_seen, get_seen_count
from summarizer import summarize_announcement
from whatsapp_notifier import send_whatsapp_alert, send_test_message

# ─── Logging Setup ────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "monitor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("monitor")

# ─── Config Loading ───────────────────────────────────────────────────────────

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    """Load and validate config.yaml"""
    if not CONFIG_FILE.exists():
        logger.error("config.yaml not found at %s", CONFIG_FILE)
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Validate required fields
    if "companies" not in cfg or not cfg["companies"]:
        logger.error("No companies configured in config.yaml")
        sys.exit(1)

    if "whatsapp" not in cfg or not cfg["whatsapp"].get("to_number"):
        logger.error("WhatsApp to_number not configured in config.yaml")
        sys.exit(1)

    interval = cfg.get("interval_minutes", 10)
    if interval not in (5, 10, 15, 30, 60):
        logger.warning("interval_minutes=%s is unusual. Allowed: 5, 10, 15, 30, 60", interval)

    return cfg


# ─── Core Polling Logic ───────────────────────────────────────────────────────

def _hours_since_midnight() -> float:
    """Return how many hours have elapsed since midnight today (minimum 1)."""
    now = datetime.now()
    midnight = datetime.combine(date.today(), datetime.min.time())
    elapsed = (now - midnight).total_seconds() / 3600
    return max(elapsed, 1.0)  # At least 1 hour to avoid edge cases at midnight


def poll(config: dict, lookback_hours: float | None = None):
    """
    Run one polling cycle: check all configured companies for new announcements.
    For each new announcement: extract PDF text → summarize → send WhatsApp.

    Args:
        lookback_hours: How many hours back to search. Defaults to 2 (normal
                        scheduled polls). Pass a larger value (e.g. hours since
                        midnight) for the startup / --run-once scan.
    """
    companies     = config["companies"]
    to_number     = config["whatsapp"]["to_number"]
    summarizer_cfg = config.get("summarizer", {})
    max_chars     = summarizer_cfg.get("max_chars", 8000)
    summary_style = summarizer_cfg.get("summary_style", "in 3-5 bullet points, plain English")

    if lookback_hours is None:
        lookback_hours = 2  # Default for recurring scheduled polls

    logger.info(
        "━━━━ Poll started at %s | Monitoring %d companies | Lookback: %.1f hr ━━━━",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        len(companies),
        lookback_hours,
    )

    total_new = 0

    for company in companies:
        name      = company.get("name", "Unknown Company")
        scripcode = str(company.get("scripcode", "")).strip()

        if not scripcode:
            logger.warning("Skipping %s — no scripcode configured", name)
            continue

        try:
            announcements = get_recent_announcements(
                scripcode=scripcode,
                company_name=name,
                lookback_hours=lookback_hours,
            )
        except Exception as e:
            logger.error("Error fetching announcements for %s: %s", name, e)
            continue

        for ann in announcements:
            ann_id = ann["id"]

            if not is_new(ann_id):
                logger.debug("Already seen: [%s] %s — skipping", name, ann["title"])
                continue

            logger.info("🆕 New announcement: [%s] %s", name, ann["title"])

            # Step 1: Extract PDF text
            pdf_text = ""
            if ann.get("pdf_url"):
                pdf_text = download_pdf_text(ann["pdf_url"])

            # Step 2: Summarize
            summary = summarize_announcement(
                company_name=name,
                title=ann["title"],
                document_text=pdf_text,
                max_chars=max_chars,
                summary_style=summary_style,
            )

            # Step 3: Send WhatsApp
            sent = send_whatsapp_alert(
                to_number=to_number,
                company_name=name,
                announcement_title=ann["title"],
                announcement_date=ann["date"],
                announcement_category=ann["category"],
                pdf_url=ann.get("pdf_url", ""),
                listing_url=ann.get("bse_listing_url", ""),
                summary=summary,
            )

            if sent:
                mark_seen(ann_id)
                total_new += 1
                logger.info("✅ Alert sent for [%s]: %s", name, ann["title"])
            else:
                logger.warning("⚠️  WhatsApp send failed for [%s]: %s", name, ann["title"])

    logger.info(
        "━━━━ Poll complete | %d new announcements sent | %d total seen ━━━━",
        total_new,
        get_seen_count(),
    )


# ─── Scheduler ────────────────────────────────────────────────────────────────

def run_scheduler(config: dict):
    """Start the scheduler and run poll() at the configured interval."""
    interval = config.get("interval_minutes", 10)
    logger.info("Starting Corporate Announcement Monitor")
    logger.info("Polling every %d minutes for %d companies", interval, len(config["companies"]))
    logger.info("WhatsApp alerts → %s", config["whatsapp"]["to_number"])

    # On startup: scan all of today's announcements so nothing is missed
    today_hours = _hours_since_midnight()
    logger.info("Startup scan: checking announcements since midnight (%.1f hours back)", today_hours)
    poll(config, lookback_hours=today_hours)

    # Schedule recurring runs using the shorter window (avoids re-alerting)
    schedule.every(interval).minutes.do(poll, config=config)

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user.")


# ─── CLI Entry Point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="BSE Corporate Announcement Monitor — sends WhatsApp alerts for new announcements"
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run a single polling cycle and exit (useful for testing)",
    )
    parser.add_argument(
        "--test-whatsapp",
        action="store_true",
        help="Send a test WhatsApp message to verify setup, then exit",
    )
    parser.add_argument(
        "--list-companies",
        action="store_true",
        help="Print configured companies and exit",
    )
    parser.add_argument(
        "--lookback-hours",
        type=float,
        default=None,
        metavar="N",
        help="Scan announcements from the last N hours and exit (e.g. 36 covers yesterday+today)",
    )
    args = parser.parse_args()

    config = load_config()

    if args.list_companies:
        print("\nConfigured companies:")
        for c in config["companies"]:
            print(f"  • {c['name']} (scripcode: {c.get('scripcode', 'NOT SET')})")
        print()
        return

    if args.test_whatsapp:
        to_number = config["whatsapp"]["to_number"]
        logger.info("Sending test WhatsApp message to %s ...", to_number)
        success = send_test_message(to_number)
        if success:
            logger.info("✅ Test message sent successfully!")
        else:
            logger.error("❌ Failed to send test message. Check your Twilio credentials in .env")
        return

    if args.lookback_hours is not None:
        logger.info("--lookback-hours: scanning last %.1f hours", args.lookback_hours)
        poll(config, lookback_hours=args.lookback_hours)
        return

    if args.run_once:
        today_hours = _hours_since_midnight()
        logger.info("--run-once: scanning announcements since midnight (%.1f hours back)", today_hours)
        poll(config, lookback_hours=today_hours)
        return

    # Default: start the scheduler
    run_scheduler(config)


if __name__ == "__main__":
    main()
