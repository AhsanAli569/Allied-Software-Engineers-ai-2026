import io
import logging

from docx import Document
from pypdf import PdfReader

logger = logging.getLogger("ase_ai.documents")

MAX_EXTRACTED_CHARS = 50_000


def extract_text(mime_type: str, content: bytes) -> str:
    """Best-effort text extraction. Returns "" if nothing usable was found (e.g. a
    scanned/image-only PDF with no embedded text layer) rather than raising — an empty
    result just means ASE AI won't have that document's context, not a failed upload.
    No OCR here: only embedded/selectable text is extracted (see spec on not OCR'ing
    every PDF unnecessarily).
    """
    try:
        if mime_type == "application/pdf":
            text = _extract_pdf(content)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            text = _extract_docx(content)
        else:
            text = content.decode("utf-8", errors="replace")
    except Exception:
        logger.exception("document_text_extraction_failed")
        return ""

    text = text.strip()
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS] + "\n\n[...truncated...]"
    return text


def _extract_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            pages.append(f"--- Page {i} ---\n{page_text}")
    return "\n\n".join(pages)


def _extract_docx(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())
