"""
bse_scraper.py
Fetches corporate announcements from BSE India for a given scrip code.
Uses the `bse` pip package (BseIndiaApi) which handles BSE's cookie/session auth.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import io
import re

logger = logging.getLogger(__name__)

BSE_BASE_URL = "https://www.bseindia.com"
BSE_DOWNLOADS_URL = "https://www.bseindia.com/xml-data/corpfiling/AttachLive"


def get_recent_announcements(
    scripcode: str,
    company_name: str,
    lookback_hours: int = 2,
    download_folder: str = "./downloads",
) -> list[dict]:
    """
    Fetch new corporate announcements from BSE for the given scrip code.

    Args:
        scripcode:       BSE 6-digit scrip code (e.g. "543942")
        company_name:    Human-readable company name for logging
        lookback_hours:  Only return announcements made in the last N hours
        download_folder: Folder for the BSE session cookie/cache files

    Returns:
        List of announcement dicts with keys:
          - id          : unique BSE announcement identifier
          - title       : subject/category of the announcement
          - date        : announcement datetime string
          - pdf_url     : direct link to the PDF/document
          - company     : company display name
          - scripcode   : BSE scrip code
    """
    try:
        from bse import BSE
    except ImportError:
        raise ImportError(
            "The 'bse' package is not installed. Run: pip install bse"
        )

    Path(download_folder).mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now() - timedelta(hours=lookback_hours)
    results = []

    with BSE(download_folder=download_folder) as bse:
        logger.info(
            "Fetching announcements for %s (scrip: %s) from %s to now",
            company_name, scripcode, cutoff.strftime("%Y-%m-%d %H:%M")
        )
        # Pass explicit from_date so BSE API searches back to the cutoff date.
        # Without this, the API defaults both from_date and to_date to today only.
        response = bse.announcements(
            scripcode=scripcode,
            from_date=cutoff,
            to_date=datetime.now(),
        )

        table = response.get("Table", [])
        logger.info("Got %d announcements for %s", len(table), company_name)

        for item in table:
            try:
                ann = _parse_announcement(item, company_name, scripcode, cutoff)
                if ann:
                    results.append(ann)
            except Exception as e:
                logger.warning("Error parsing announcement: %s | item=%s", e, item)

    return results


def _parse_announcement(item: dict, company_name: str, scripcode: str, cutoff: datetime) -> Optional[dict]:
    """Parse a raw BSE API response dict into a clean announcement dict."""

    # BSE response keys (from sample JSON in BseIndiaApi repo)
    # SLNO, NEWS_DT, CATEGORYNAME, SUBCATNAME, HEADLINE, ATTACHMENTNAME,
    # SCRIP_CD, COMPANYNAME, ...
    # BSE API returns NEWSID (UUID) as the unique identifier
    ann_id = str(
        item.get("NEWSID") or item.get("SLNO") or item.get("slno") or ""
    ).strip()
    if not ann_id:
        return None

    # Parse date
    date_str = item.get("NEWS_DT") or item.get("news_dt") or ""
    ann_date = _parse_bse_date(date_str)
    if ann_date is None:
        return None

    # Only include announcements newer than cutoff
    if ann_date < cutoff:
        return None

    category = item.get("CATEGORYNAME") or item.get("SUBCATNAME") or "Corporate Announcement"
    # NEWSSUB has the full subject, HEADLINE has the body text — prefer NEWSSUB
    headline = item.get("NEWSSUB") or item.get("HEADLINE") or item.get("SUBCATNAME") or category

    # Build PDF URL
    attachment = item.get("ATTACHMENTNAME") or ""
    pdf_url = ""
    if attachment:
        pdf_url = f"{BSE_DOWNLOADS_URL}/{attachment}"

    return {
        "id": ann_id,
        "title": headline.strip(),
        "category": category.strip(),
        "date": ann_date.strftime("%d %b %Y, %I:%M %p"),
        "date_raw": ann_date,
        "pdf_url": pdf_url,
        "company": company_name,
        "scripcode": scripcode,
        "bse_listing_url": f"{BSE_BASE_URL}/stock-share-price/--/--/{scripcode}/corp-announcements/",
    }


def _parse_bse_date(date_str: str) -> Optional[datetime]:
    """Try to parse BSE date strings in various formats."""
    if not date_str:
        return None

    # BSE returns dates like "20250225T093000" or "2025-02-25T09:30:00" or "25/02/2025 09:30:00"
    formats = [
        "%Y%m%dT%H%M%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]

    # Remove trailing timezone info if present
    clean = re.split(r"[+-]\d{2}:\d{2}$", date_str)[0].strip()
    # Strip fractional seconds (e.g. "2026-02-24T20:07:46.99" -> "2026-02-24T20:07:46")
    clean = re.sub(r"\.\d+$", "", clean)

    for fmt in formats:
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue

    logger.warning("Could not parse date string: %s", date_str)
    return None


def download_pdf_text(pdf_url: str) -> str:
    """
    Download the PDF from `pdf_url` and extract its text content.
    Returns the extracted text, or empty string on failure.
    """
    if not pdf_url:
        return ""

    try:
        import requests
        import pdfplumber

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": BSE_BASE_URL,
        }

        logger.info("Downloading PDF: %s", pdf_url)
        response = requests.get(pdf_url, headers=headers, timeout=20)
        response.raise_for_status()

        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            pages = []
            for page in pdf.pages[:6]:  # Read up to 6 pages to keep it fast
                text = page.extract_text()
                if text:
                    pages.append(text)

        full_text = "\n".join(pages)
        logger.info("Extracted %d characters from PDF", len(full_text))
        return full_text

    except Exception as e:
        logger.warning("Could not extract PDF text from %s: %s", pdf_url, e)
        return ""
