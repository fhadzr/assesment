"""Document ingestion + text extraction (task 2.1).

Stages (each pure and testable; composed by docintel.core):
  ingest -> extract_text (pdf | ocr) -> mask -> llm_extract -> validate -> route.

Document-level statuses:
  ok | review | ocr_unavailable | extraction_error | ingest_error
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

try:
    import pytesseract
except ImportError:  # pragma: no cover - pytesseract is pinned in requirements
    pytesseract = None

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}


@dataclass
class Document:
    filename: str
    content: bytes

    @property
    def suffix(self) -> str:
        return Path(self.filename).suffix.lower()


def is_pdf(doc: Document) -> bool:
    return doc.content[:5] == b"%PDF-"


def is_image(doc: Document) -> bool:
    from PIL import Image

    try:
        Image.open(__import__("io").BytesIO(doc.content))
        return True
    except Exception:
        return False


def extract_pdf_text(doc: Document) -> str:
    """Extract the PDF text layer. Raises on non-PDF or corrupt content."""
    reader = PdfReader(__import__("io").BytesIO(doc.content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def ocr_available() -> bool:
    """Probe whether the Tesseract binary is installed and usable."""
    import shutil

    return shutil.which("tesseract") is not None


def extract_image_text_ocr(doc: Document) -> str:
    """Run the real Tesseract OCR engine over an image document.

    Raises RuntimeError when the binary is unavailable — callers must check
    ocr_available() first; the pipeline maps that to `ocr_unavailable`.
    """
    import io

    from PIL import Image

    if not ocr_available():
        raise RuntimeError("Tesseract binary not found; OCR unavailable")
    img = Image.open(io.BytesIO(doc.content))
    return pytesseract.image_to_string(img)
