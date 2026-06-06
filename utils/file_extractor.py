import pdfplumber


def extract_text_from_pdf(file) -> str:
    """Extract text from a digital (text-based) PDF file."""
    parts: list[str] = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                parts.append(page_text)
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError(
            "No text could be extracted from this PDF. "
            "Ensure the file is a text-based PDF (not a scanned image)."
        )
    return text
