"""
Text extraction utilities for various document formats.
Handles PDF, plain text, and markdown files.
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf_bytes(data: bytes, max_chars: int = 50_000) -> str:
    """
    Extract text from PDF bytes using pdfplumber.

    Handles academic PDFs with complex layouts, embedded fonts, and multi-column text.

    Args:
        data: PDF file bytes
        max_chars: Maximum characters to extract (default 50,000)

    Returns:
        Extracted text content
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed, cannot extract PDF text")
        return "PDF text extraction requires pdfplumber. Install with: pip install pdfplumber"

    try:
        out = []
        total_chars = 0

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            logger.info(
                "Extracting text from PDF", extra={"page_count": len(pdf.pages), "max_chars": max_chars}
            )

            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text() or ""

                    if page_text.strip():
                        out.append(page_text)
                        total_chars += len(page_text)

                        logger.debug(
                            "Extracted page text",
                            extra={
                                "page": page_num,
                                "chars": len(page_text),
                                "total_chars": total_chars,
                            },
                        )

                        # Stop if we've exceeded max_chars
                        if total_chars >= max_chars:
                            logger.info(
                                "Reached max_chars limit",
                                extra={"pages_extracted": page_num, "total_chars": total_chars},
                            )
                            break
                except Exception as page_error:
                    logger.warning(
                        "Failed to extract text from page",
                        extra={"page": page_num, "error": str(page_error)},
                    )
                    continue

        if not out:
            logger.warning("No text extracted from PDF")
            return "Unable to extract text from PDF. The document may be image-based or encrypted."

        full_text = "\n".join(out)
        result = full_text[:max_chars]

        logger.info(
            "PDF text extraction completed",
            extra={
                "total_pages_processed": len(out),
                "total_chars": total_chars,
                "result_chars": len(result),
            },
        )

        return result

    except Exception as e:
        logger.error("PDF text extraction failed", extra={"error": str(e)}, exc_info=True)
        return f"Error extracting text from PDF: {str(e)}"


def extract_text_from_bytes(
    data: bytes, filename: str, max_chars: int = 50_000
) -> str:
    """
    Extract text from file bytes based on file type.

    Args:
        data: File bytes
        filename: Original filename (used to detect file type)
        max_chars: Maximum characters to extract

    Returns:
        Extracted text content
    """
    filename_lower = filename.lower()

    # Handle PDF files
    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf_bytes(data, max_chars)

    # Handle text-based files (txt, md, markdown)
    try:
        text = data.decode("utf-8", errors="ignore")
        result = text[:max_chars]

        logger.info(
            "Text file decoded",
            extra={"filename": filename, "size_bytes": len(data), "chars_extracted": len(result)},
        )

        return result

    except Exception as e:
        logger.error(
            "Text extraction failed",
            extra={"filename": filename, "error": str(e)},
            exc_info=True,
        )
        return f"Unable to extract text from file: {str(e)}"
