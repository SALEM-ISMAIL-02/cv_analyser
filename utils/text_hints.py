"""Regex-based hints from raw CV text to guide LLM extraction."""

import re

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,4}(?:[\s.-]?\d{1,4})?"
)
LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[\w%-]+/?", re.I)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[\w%-]+/?", re.I)
URL_RE = re.compile(r"https?://[\w.-]+(?:/[\w._~:/?#[\]@!$&'()*+,;=%-]*)?", re.I)


def extract_hints(text: str) -> dict:
    emails = EMAIL_RE.findall(text)
    phones = [p.strip() for p in PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) >= 8]
    profiles = []
    for match in LINKEDIN_RE.findall(text):
        profiles.append({"network": "LinkedIn", "url": match.rstrip("/")})
    for match in GITHUB_RE.findall(text):
        profiles.append({"network": "GitHub", "url": match.rstrip("/")})
    urls = [u for u in URL_RE.findall(text) if "linkedin" not in u.lower() and "github" not in u.lower()]
    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "profiles": profiles,
        "website": urls[0] if urls else None,
    }
