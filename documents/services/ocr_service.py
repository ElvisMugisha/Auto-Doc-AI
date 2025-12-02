"""
OCR Service using Tesseract OCR.

Provides text extraction from images and PDFs.
"""
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Optional
from utils import loggings

logger = loggings.setup_logging()


class OCRService:
    """
    Service for extracting text from documents using Tesseract OCR.
    """

    def __init__(self, tesseract_cmd: Optional[str] = None):
        """
        Initialize OCR service.

        Args:
            tesseract_cmd: Path to tesseract executable
        """
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        logger.info("OCR Service initialized")

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from an image file.

        Args:
            image_path: Path to image file

        Returns:
            Extracted text
        """
        try:
            logger.info(f"Extracting text from image: {image_path}")
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            logger.info(f"Extracted {len(text)} characters from image")
            return text.strip()

        except Exception as e:
            logger.exception(f"Error extracting text from image: {str(e)}")
            raise

    def extract_text_from_pdf(self, pdf_path: str) -> Dict[str, any]:
        """
        Extract text from PDF file.

        First tries direct text extraction (for digital PDFs),
        then falls back to OCR for scanned PDFs.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dictionary containing:
                - text: Extracted text
                - pages: Number of pages
                - method: Extraction method used ('direct' or 'ocr')
        """
        try:
            logger.info(f"Extracting text from PDF: {pdf_path}")

            # Try direct text extraction first (faster for digital PDFs)
            text, pages = self._extract_text_direct(pdf_path)

            # If no text found, use OCR
            if not text or len(text.strip()) < 50:
                logger.info("Direct extraction yielded little text, using OCR")
                text, pages = self._extract_text_ocr(pdf_path)
                method = 'ocr'
            else:
                method = 'direct'

            logger.info(f"Extracted {len(text)} characters from {pages} pages using {method}")

            return {
                'text': text.strip(),
                'pages': pages,
                'method': method
            }

        except Exception as e:
            logger.exception(f"Error extracting text from PDF: {str(e)}")
            raise

    def _extract_text_direct(self, pdf_path: str) -> tuple:
        """
        Extract text directly from PDF (for digital PDFs).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (text, page_count)
        """
        try:
            doc = fitz.open(pdf_path)
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text_parts.append(page.get_text())

            doc.close()

            return '\n\n'.join(text_parts), len(doc)

        except Exception as e:
            logger.error(f"Direct text extraction failed: {str(e)}")
            return '', 0

    def _extract_text_ocr(self, pdf_path: str) -> tuple:
        """
        Extract text from PDF using OCR (for scanned PDFs).

        Args:
            pdf_path: Path to PDF file

        Returns:
            Tuple of (text, page_count)
        """
        try:
            # Convert PDF to images
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info("Converting PDF to images for OCR")
                images = convert_from_path(pdf_path, dpi=300)

                text_parts = []
                for i, image in enumerate(images):
                    logger.debug(f"OCR processing page {i+1}/{len(images)}")
                    text = pytesseract.image_to_string(image)
                    text_parts.append(text)

                return '\n\n'.join(text_parts), len(images)

        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            raise

    def extract_text(self, file_path: str) -> Dict[str, any]:
        """
        Extract text from any supported file type.

        Args:
            file_path: Path to file

        Returns:
            Dictionary containing extracted text and metadata
        """
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            text = self.extract_text_from_image(file_path)
            return {
                'text': text,
                'pages': 1,
                'method': 'ocr'
            }
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
