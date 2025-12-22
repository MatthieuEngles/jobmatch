"""PDF text extraction using pdfplumber."""

import logging
from io import BytesIO

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text content from a PDF file.

    Args:
        file_content: Raw bytes of the PDF file.

    Returns:
        Extracted text as a single string with page breaks preserved.

    Raises:
        ValueError: If the PDF cannot be read or is empty.
    """
    try:
        text_parts = []

        with pdfplumber.open(BytesIO(file_content)) as pdf:
            if len(pdf.pages) == 0:
                raise ValueError("PDF has no pages")

            for page_num, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                    logger.debug(f"Extracted {len(page_text)} chars from page {page_num}")

        if not text_parts:
            raise ValueError("No text could be extracted from PDF")

        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} chars from {len(text_parts)} pages")

        return full_text

    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}") from e
