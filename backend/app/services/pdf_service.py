from dataclasses import dataclass
import logging

import fitz


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExtractedPDFText:
    text: str
    page_count: int


def extract_text_from_pdf(file_bytes: bytes) -> ExtractedPDFText:
    if not file_bytes:
        raise ValueError("The uploaded file could not be read as a valid PDF.")

    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.exception("Unable to open uploaded file as a PDF.")
        raise ValueError("The uploaded file could not be read as a valid PDF.") from exc

    try:
        page_texts = [page.get_text("text") for page in document]
        text = "\n".join(page_texts).strip()
        page_count = document.page_count
    except Exception as exc:
        logger.exception("Unable to extract text from PDF.")
        raise ValueError("The uploaded file could not be read as a valid PDF.") from exc
    finally:
        document.close()

    if not text:
        raise ValueError("No readable text was found in the PDF.")

    return ExtractedPDFText(text=text, page_count=page_count)
