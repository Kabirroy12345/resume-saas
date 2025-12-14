# backend/app/parser.py

import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from pdfminer.high_level import extract_text
from .skills import SKILLS, SYNONYMS

# Lazy load spaCy model to prevent blocking at startup
_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        print("Loading spaCy model...")
        _nlp = spacy.load("en_core_web_sm")
        print("spaCy model loaded!")
        print("spaCy model loaded!")
    return _nlp


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
    nlp = get_nlp()
    doc = nlp(text[:1000])
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
    return None


def extract_skills(text: str) -> list[str]:
    """Extract skills based on SKILLS + SYNONYMS."""
    text_low = text.lower()
    found = set()

    # Create a regex pattern for strict matching
    # Sort skills by length (descending) so 'c++' matches before 'c'
    all_skills = sorted(SKILLS, key=len, reverse=True)
    
    # Escape special regex chars in skills (like c++, c#, .net)
    # \b matches word boundary. 
    # For symbols like C++, \b might not work at the end if followed by space, so we use a more complex pattern or just simple whitespace boundaries
    # A safe pattern for "C++" is (?<!\w)C\+\+(?!\w)
    
    # But for simplicity and performance with this list:
    for skill in all_skills:
        # Construct pattern: lookbehind/ahead for non-word char, OR start/end of string
        # We handle the special cases where skill itself contains non-word chars (like c++, .net)
        
        s_esc = re.escape(skill.lower())
        pattern = r'(?:^|[\s,.\/;:\(\)\[\]])' + s_esc + r'(?:$|[\s,.\/;:\(\)\[\]])'
        
        if re.search(pattern, text_low):
            found.add(skill)

    for syn, real in SYNONYMS.items():
        s_esc = re.escape(syn)
        pattern = r'(?:^|[\s,.\/;:\(\)\[\]])' + s_esc + r'(?:$|[\s,.\/;:\(\)\[\]])'
        if re.search(pattern, text_low):
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

    skills = extract_skills(text)

    # Improved Snippet Extraction
    snippet = ""
    # 1. Try to find "Summary" or "Profile" header
    summary_match = re.search(r"(?i)(?:summary|profile|objective|about me)[\s:]+(.{50,500})", text, re.DOTALL)
    if summary_match:
        snippet = summary_match.group(1).strip().replace("\n", " ")[:600]
    else:
        # 2. Fallback: First paragraph that looks like specific content
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 40]
        if lines:
            snippet = " ".join(lines[:3])[:600]
        else:
            snippet = text[:600].replace("\r", " ").strip()

    return {
        "name": name,
        "emails": emails,
        "phones": phones,
        "skills": skills,
        "snippet": snippet,
        "full_text": text,
    }
