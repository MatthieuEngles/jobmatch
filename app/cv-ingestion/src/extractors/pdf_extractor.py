"""PDF text and image extraction with automatic detection."""

import io
import logging
from io import BytesIO
from typing import NamedTuple

import pdfplumber
from pdf2image import convert_from_bytes
from PIL import Image

from ..config import settings

logger = logging.getLogger(__name__)

# Minimum text length to consider a PDF as text-based
MIN_TEXT_LENGTH = 100
# Minimum text-to-page ratio to consider text extraction valid
MIN_TEXT_PER_PAGE = 50


class PDFContent(NamedTuple):
    """Result of PDF extraction."""

    is_text_based: bool
    text: str | None
    images: list[bytes] | None


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


def convert_pdf_to_images(file_content: bytes, dpi: int = 200) -> list[bytes]:
    """
    Convert PDF pages to PNG images.

    Args:
        file_content: Raw bytes of the PDF file.
        dpi: Resolution for image conversion (default 200 for good quality/size balance).

    Returns:
        List of PNG image bytes, one per page.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        # Convert PDF to PIL Images
        images = convert_from_bytes(file_content, dpi=dpi)
        logger.info(f"Converted PDF to {len(images)} images at {dpi} DPI")

        # Convert PIL Images to PNG bytes
        result = []
        for idx, img in enumerate(images):
            buffer = io.BytesIO()
            img.save(buffer, format="PNG", optimize=True)
            png_bytes = buffer.getvalue()
            result.append(png_bytes)
            logger.debug(f"Page {idx + 1}: {len(png_bytes)} bytes PNG")

        return result

    except Exception as e:
        logger.error(f"PDF to image conversion failed: {e}")
        raise ValueError(f"Failed to convert PDF to images: {e}") from e


def is_text_based_pdf(file_content: bytes) -> bool:
    """
    Determine if a PDF contains extractable text or is image-based.

    Heuristic:
    - Extract text from all pages
    - If total text length > MIN_TEXT_LENGTH and avg text per page > MIN_TEXT_PER_PAGE,
      consider it text-based
    - Otherwise, it's likely an image-based/scanned PDF

    Args:
        file_content: Raw bytes of the PDF file.

    Returns:
        True if PDF has sufficient extractable text, False otherwise.
    """
    try:
        with pdfplumber.open(BytesIO(file_content)) as pdf:
            if len(pdf.pages) == 0:
                return False

            total_text_length = 0
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    total_text_length += len(page_text.strip())

            avg_per_page = total_text_length / len(pdf.pages)

            is_text = total_text_length >= MIN_TEXT_LENGTH and avg_per_page >= MIN_TEXT_PER_PAGE

            logger.info(
                f"PDF analysis: {total_text_length} chars total, {avg_per_page:.1f} avg/page, is_text_based={is_text}"
            )

            return is_text

    except Exception as e:
        logger.warning(f"Could not analyze PDF for text content: {e}")
        return False


def extract_pdf_content(file_content: bytes) -> PDFContent:
    """
    Smart PDF extraction: automatically detect text vs image-based PDF.

    Strategy:
    1. Try to detect if PDF has extractable text
    2. If text-based: extract text directly
    3. If image-based: convert to images for Vision LLM processing

    Args:
        file_content: Raw bytes of the PDF file.

    Returns:
        PDFContent with either text or images based on detection.

    Raises:
        ValueError: If both extraction methods fail.
    """
    # Check if PDF has extractable text
    if is_text_based_pdf(file_content):
        logger.info("PDF detected as text-based, extracting text")
        try:
            text = extract_text_from_pdf(file_content)
            return PDFContent(is_text_based=True, text=text, images=None)
        except ValueError:
            logger.warning("Text extraction failed, falling back to image conversion")

    # Image-based PDF or text extraction failed
    logger.info("PDF detected as image-based, converting to images")
    images = convert_pdf_to_images(file_content)
    return PDFContent(is_text_based=False, text=None, images=images)


def ocr_images(images: list[bytes]) -> str:
    """
    Perform OCR on images using Tesseract (fallback when Vision LLM not available).

    Args:
        images: List of PNG image bytes.

    Returns:
        Extracted text from all images.

    Raises:
        ValueError: If OCR fails or no text extracted.
    """
    try:
        import pytesseract
    except ImportError as e:
        raise ValueError("pytesseract not installed. Install with: pip install pytesseract") from e

    text_parts = []

    for idx, img_bytes in enumerate(images):
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # Configure Tesseract for multi-language support
            ocr_lang = getattr(settings, "OCR_LANGUAGE", "fra+eng")
            page_text = pytesseract.image_to_string(img, lang=ocr_lang)

            if page_text.strip():
                text_parts.append(page_text.strip())
                logger.debug(f"OCR page {idx + 1}: {len(page_text)} chars")
        except Exception as e:
            logger.warning(f"OCR failed for page {idx + 1}: {e}")

    if not text_parts:
        raise ValueError("OCR could not extract any text from images")

    full_text = "\n\n".join(text_parts)
    logger.info(f"OCR extracted {len(full_text)} chars from {len(images)} pages")

    return full_text
