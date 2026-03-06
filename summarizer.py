"""
summarizer.py
Uses Google Gemini API to summarize corporate announcement documents.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def summarize_announcement(
    company_name: str,
    title: str,
    document_text: str,
    max_chars: int = 8000,
    summary_style: str = "in 3-5 bullet points, plain English",
) -> str:
    """
    Summarize the announcement text using Google Gemini.

    Args:
        company_name:   Name of the company that made the announcement
        title:          Announcement headline/subject
        document_text:  Raw text extracted from the PDF document
        max_chars:      Truncation limit before sending to LLM
        summary_style:  Style instruction appended to the prompt

    Returns:
        A formatted summary string, or a fallback message if summarization fails.
    """
    if not document_text or not document_text.strip():
        return "_(No document content available for summarization)_"

    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — skipping summarization")
        return "_(Document summary unavailable: GEMINI_API_KEY not configured)_"

    # Truncate to avoid token limits
    truncated_text = document_text[:max_chars]
    if len(document_text) > max_chars:
        truncated_text += "\n...[document truncated]"

    prompt = f"""You are a financial analyst assistant. Below is the text of a corporate announcement filed by {company_name} on the BSE (Bombay Stock Exchange) India.

Announcement Subject: {title}

Document Content:
---
{truncated_text}
---

Please provide a concise summary of this announcement {summary_style}.
Focus on: key decisions, financial figures, dates, and impact on shareholders.
Be factual and avoid speculation."""

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        logger.info("Sending document to Gemini for summarization...")
        response = model.generate_content(prompt)
        summary = response.text.strip()
        logger.info("Summarization complete (%d chars)", len(summary))
        return summary

    except Exception as e:
        logger.error("Gemini summarization failed: %s", e)
        return f"_(Summarization failed: {e})_"
