import re

def parse_resume(content: bytes):
    text = content.decode(errors="ignore")

    email = re.findall(r"[a-zA-Z0-9+._%-]+@[a-zA-Z0-9._%-]+\.[a-zA-Z]{2,}", text)
    phone = re.findall(r"\+?\d[\d\s\-()]{7,}\d", text)

    return {
        "raw_text_preview": text[:300],
        "emails": email,
        "phones": phone
    }
