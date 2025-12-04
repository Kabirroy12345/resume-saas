# backend/app/parser.py

import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from pdfminer.high_level import extract_text
import spacy

from .skills import SKILLS, SYNONYMS

# Load spaCy model once
nlp = spacy.load("en_core_web_sm")


def _pdf_bytes_to_text(content: bytes) -> str:
    """Convert uploaded PDF bytes to text, with a safe fallback."""
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        text = extract_text(tmp_path) or ""
        Path(tmp_path).unlink(missing_ok=True)
    except Exception:
        # Fallback: treat bytes as utf-8 text
        text = content.decode("utf-8", errors="ignore")

    return text


def extract_name(text: str) -> str | None:
    """Use spaCy NER to extract candidate person name from top of resume."""
    if not text:
        return None
    doc = nlp(text[:1000])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return None


def extract_skills(text: str) -> list[str]:
    """Extract skills based on SKILLS + SYNONYMS."""
    text_low = text.lower()
    found = set()

    for skill in SKILLS:
        if skill.lower() in text_low:
            found.add(skill)

    for syn, real in SYNONYMS.items():
        if syn in text_low:
            found.add(real)

    return sorted(found)


def extract_contacts(text: str) -> tuple[list[str], list[str]]:
    """Extract emails + phone numbers with basic cleanup."""
    emails = re.findall(
        r"[a-zA-Z0-9+._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,}",
        text,
    )

    phones_raw = re.findall(r"\+?\d[\d\s\-()]{7,}\d", text)
    phones_cleaned: list[str] = []
    for p in phones_raw:
        digits_only = re.sub(r"[^\d+]", "", p)
        digit_count = len(re.sub(r"[^\d]", "", digits_only))
        if 10 <= digit_count <= 14:
            phones_cleaned.append(digits_only)

    # Deduplicate while keeping order
    emails_unique = list(dict.fromkeys(emails))
    phones_unique = list(dict.fromkeys(phones_cleaned))

    return emails_unique, phones_unique


def parse_resume(content: bytes) -> dict:
    """
    Main parser entrypoint.

    Returns:
        {
            "name": str | None,
            "emails": list[str],
            "phones": list[str],
            "skills": list[str],
            "snippet": str,      # first 600 chars
            "full_text": str     # entire extracted resume text
        }
    """
    text = _pdf_bytes_to_text(content)
    if not text:
        text = ""

    name = extract_name(text)
    emails, phones = extract_contacts(text)
    skills = extract_skills(text)

    snippet = text[:600].replace("\r", " ").strip()

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "skills": skills,
        "snippet": snippet,
        "full_text": text,
    }
