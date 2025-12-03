"""
OpenAI Vision-based universal document extraction service.

This service uses GPT-4 Vision to analyze ANY document type and extract
ALL meaningful information with high accuracy.
"""
import base64
from pathlib import Path
from typing import Dict, Optional, List
import json
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image
import io
import mimetypes

from utils import loggings

logger = loggings.setup_logging()


class OpenAIExtractionService:
    """
    Universal document extraction service using OpenAI GPT-4 Vision.

    This service can process ANY document type and extract ALL meaningful
    information automatically, without requiring predefined templates.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", organization: Optional[str] = None, project: Optional[str] = None):
        """
        Initialize OpenAI extraction service.

        Args:
            api_key: OpenAI API key
            model: Model to use (default to gpt-4o-mini for cost efficiency)
            organization: OpenAI Organization ID (optional)
            project: OpenAI Project ID (optional)
        """
        self.client = OpenAI(
            api_key=api_key,
            organization=organization,
            project=project
        )
        self.model = model
        logger.info(f"OpenAI Universal Extraction Service initialized with model: {model}")

    def _image_to_base64(self, image_path: str) -> str:
        """
        Convert image file to base64 string.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string

        Raises:
            IOError: If file cannot be read
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                logger.debug(f"Successfully encoded image: {image_path}")
                return encoded
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {str(e)}")
            raise

    def _pdf_to_base64_images(self, pdf_path: str, max_pages: int = 10) -> List[str]:
        """
        Convert PDF pages to base64 encoded images.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum number of pages to process (default: 10)

        Returns:
            List of base64 encoded images (one per page)

        Raises:
            Exception: If PDF conversion fails
        """
        try:
            logger.info(f"Converting PDF to images: {pdf_path}")
            # Convert PDF to images with high DPI for better quality
            images = convert_from_path(pdf_path, dpi=300)

            # Limit pages to avoid excessive costs
            images = images[:max_pages]
            logger.info(f"Processing {len(images)} pages from PDF")

            base64_images = []
            for idx, image in enumerate(images):
                # Convert PIL Image to base64
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
                base64_images.append(img_str)
                logger.debug(f"Encoded page {idx + 1}/{len(images)}")

            return base64_images
        except Exception as e:
            logger.error(f"Failed to convert PDF {pdf_path}: {str(e)}")
            raise

    def extract_universal_data(self, file_path: str, document_type: Optional[str] = None) -> Dict:
        """
        Universal document extraction - analyzes ANY document and extracts ALL information.

        This method uses GPT-4 Vision to intelligently analyze the document,
        identify its type, and extract all meaningful information without
        requiring predefined templates.

        Args:
            file_path: Path to document file (PDF, image, etc.)
            document_type: Optional hint about document type (invoice, receipt, etc.)

        Returns:
            Dictionary containing:
                - document_type: Detected document type
                - extracted_fields: All extracted data fields
                - metadata: Document metadata
                - confidence: Extraction confidence score

        Raises:
            Exception: If extraction fails completely
        """
        try:
            logger.info(f"Starting universal extraction for: {file_path}")

            # Detect file type
            file_ext = Path(file_path).suffix.lower()
            mime_type = mimetypes.guess_type(file_path)[0]
            logger.info(f"File type: {file_ext}, MIME: {mime_type}")

            # Convert document to images
            base64_images = self._prepare_document_images(file_path, file_ext)

            if not base64_images:
                raise ValueError("No images could be extracted from document")

            logger.info(f"Prepared {len(base64_images)} image(s) for analysis")

            # Extract data from all pages
            all_extracted_data = []
            for page_num, base64_image in enumerate(base64_images, 1):
                logger.info(f"Analyzing page {page_num}/{len(base64_images)}")
                page_data = self._extract_from_image(
                    base64_image,
                    document_type,
                    page_num,
                    len(base64_images)
                )
                all_extracted_data.append(page_data)

            # Merge multi-page data
            final_data = self._merge_page_data(all_extracted_data)

            logger.info("Universal extraction completed successfully")
            return final_data

        except Exception as e:
            logger.exception(f"Universal extraction failed for {file_path}: {str(e)}")
            return self._get_fallback_data(str(e))

    def _prepare_document_images(self, file_path: str, file_ext: str) -> List[str]:
        """
        Prepare document images for analysis based on file type.

        Args:
            file_path: Path to document
            file_ext: File extension

        Returns:
            List of base64 encoded images
        """
        try:
            if file_ext == '.pdf':
                return self._pdf_to_base64_images(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']:
                return [self._image_to_base64(file_path)]
            else:
                # For unsupported formats, try to treat as image
                logger.warning(f"Unsupported format {file_ext}, attempting as image")
                return [self._image_to_base64(file_path)]
        except Exception as e:
            logger.error(f"Failed to prepare images: {str(e)}")
            raise

    def _extract_from_image(self, base64_image: str, document_type: Optional[str], page_num: int, total_pages: int) -> Dict:
        """
        Extract data from a single image using GPT-4 Vision.

        Args:
            base64_image: Base64 encoded image
            document_type: Optional document type hint
            page_num: Current page number
            total_pages: Total number of pages

        Returns:
            Extracted data dictionary
        """
        try:
            # Build the system prompt for universal extraction
            system_prompt = self._build_universal_prompt(document_type, page_num, total_pages)

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this document image and extract ALL information following the instructions."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]

            # Call OpenAI API
            logger.debug(f"Sending request to OpenAI (page {page_num})")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=2000,  # Increased for comprehensive extraction
                temperature=0.1   # Low temperature for accuracy
            )

            # Extract and parse response
            result_text = response.choices[0].message.content.strip()
            logger.debug(f"Received response (length: {len(result_text)})")

            # Parse JSON from response
            extracted_data = self._extract_json(result_text)

            return extracted_data

        except Exception as e:
            logger.error(f"Extraction failed for page {page_num}: {str(e)}")
            return {"error": str(e), "page": page_num}

    def _build_universal_prompt(self, document_type: Optional[str], page_num: int, total_pages: int) -> str:
        """
        Build a comprehensive prompt for universal document extraction.

        Args:
            document_type: Optional document type hint
            page_num: Current page number
            total_pages: Total pages

        Returns:
            System prompt string
        """
        type_hint = f"The document is likely a {document_type}." if document_type else "Identify the document type automatically."

        prompt = f"""
            ### CONTEXT ###
            You are an expert document analyst with the ability to extract ALL meaningful information from ANY type of document.
            {type_hint}
            This is page {page_num} of {total_pages}.

            ### INSTRUCTION ###
            Analyze the provided document image and extract ALL important information in a structured format.

            ### EXTRACTION RULES ###
            1. **Identify Document Type**: Determine what kind of document this is (invoice, receipt, contract, ID card, form, letter, etc.)
            2. **Extract ALL Fields**: Find and extract every piece of meaningful information
            3. **Be Accurate**: Extract EXACT values as they appear - do not guess or make up data
            4. **Use Proper Formats**:
            - Dates: YYYY-MM-DD format
            - Numbers: Numeric values without currency symbols
            - Currency: Separate field (USD, EUR, RWF, etc.)
            5. **Structure Data Logically**: Group related information together
            6. **Handle Missing Data**: Use null for fields not found in the document

            ### RESPONSE FORMAT ###
            Return a JSON object with this structure:
            {{
            "document_type": "Type of document (invoice, receipt, contract, id_card, form, letter, etc.)",
            "document_title": "Document title or name if visible",
            "document_number": "Document number/ID if present",
            "date_issued": "Issue date in YYYY-MM-DD format or null",
            "parties": {{
                "issuer": {{
                "name": "Company/person who issued the document",
                "address": "Full address if available",
                "contact": "Phone, email, website, etc."
                }},
                "recipient": {{
                "name": "Person/company receiving the document",
                "address": "Full address if available",
                "contact": "Contact information"
                }}
            }},
            "financial_data": {{
                "currency": "Currency code (USD, EUR, RWF, etc.) or null",
                "subtotal": "Subtotal amount as number or null",
                "tax": "Tax amount as number or null",
                "total": "Total amount as number or null",
                "payment_method": "How payment was made or null",
                "line_items": [
                {{
                    "description": "Item/service description",
                    "quantity": "Quantity as number",
                    "unit_price": "Price per unit",
                    "amount": "Total for this line"
                }}
                ]
            }},
            "dates": {{
                "issue_date": "When document was created",
                "due_date": "Payment/action due date",
                "valid_from": "Validity start date",
                "valid_until": "Validity end date"
            }},
            "extracted_fields": {{
                "field_name": "field_value"
            }},
            "text_content": "Any important text, terms, conditions, or notes",
            "metadata": {{
                "page_number": {page_num},
                "total_pages": {total_pages},
                "has_signature": "true/false",
                "has_stamp": "true/false",
                "language": "Detected language"
            }}
            }}

            ### IMPORTANT ###
            - Extract ONLY what you can see in the image
            - Be thorough - don't miss any important information
            - Return ONLY valid JSON - no explanations or markdown
            - If a section doesn't apply, use null or empty object
            - Prioritize accuracy over completeness
        """
        return prompt

    def _merge_page_data(self, page_data_list: List[Dict]) -> Dict:
        """
        Merge data from multiple pages into a single coherent result.

        Args:
            page_data_list: List of extracted data from each page

        Returns:
            Merged data dictionary
        """
        if not page_data_list:
            return self._get_fallback_data("No data extracted")

        if len(page_data_list) == 1:
            # Single page - return as is
            return page_data_list[0]

        try:
            logger.info(f"Merging data from {len(page_data_list)} pages")

            # Start with first page as base
            merged = page_data_list[0].copy()

            # Merge subsequent pages
            for page_data in page_data_list[1:]:
                # Merge line items if present
                if 'financial_data' in page_data and 'line_items' in page_data['financial_data']:
                    if 'financial_data' not in merged:
                        merged['financial_data'] = {}
                    if 'line_items' not in merged['financial_data']:
                        merged['financial_data']['line_items'] = []
                    merged['financial_data']['line_items'].extend(
                        page_data['financial_data']['line_items']
                    )

                # Merge extracted fields
                if 'extracted_fields' in page_data:
                    if 'extracted_fields' not in merged:
                        merged['extracted_fields'] = {}
                    merged['extracted_fields'].update(page_data['extracted_fields'])

                # Concatenate text content
                if 'text_content' in page_data and page_data['text_content']:
                    if 'text_content' not in merged:
                        merged['text_content'] = ""
                    merged['text_content'] += "\n\n" + page_data['text_content']

            # Update metadata
            if 'metadata' in merged:
                merged['metadata']['total_pages'] = len(page_data_list)

            logger.info("Successfully merged multi-page data")
            return merged

        except Exception as e:
            logger.error(f"Failed to merge page data: {str(e)}")
            # Return first page if merge fails
            return page_data_list[0]

    def _extract_json(self, text: str) -> Dict:
        """
        Extract and parse JSON from response text.

        Handles various formats including markdown code blocks.

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON parsing fails
        """
        try:
            # Remove markdown code blocks if present
            cleaned_text = text.replace('```json', '').replace('```', '').strip()

            # Try to find JSON object in text
            start = cleaned_text.find('{')
            end = cleaned_text.rfind('}') + 1

            if start != -1 and end > start:
                json_str = cleaned_text[start:end]
                parsed = json.loads(json_str)
                logger.debug("Successfully parsed JSON response")
                return parsed
            else:
                # If no braces found, try parsing the whole text
                parsed = json.loads(cleaned_text)
                logger.debug("Successfully parsed JSON response (full text)")
                return parsed

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            logger.debug(f"Problematic text: {text[:500]}")
            raise

    def _get_fallback_data(self, error_message: str) -> Dict:
        """
        Return fallback data structure when extraction fails.

        Args:
            error_message: Description of what went wrong

        Returns:
            Fallback data dictionary
        """
        logger.warning(f"Returning fallback data due to: {error_message}")
        return {
            'document_type': 'unknown',
            'extraction_status': 'failed',
            'error': error_message,
            'extracted_fields': {},
            'metadata': {
                'extraction_method': 'openai_vision',
                'model': self.model,
                'status': 'failed'
            }
        }

    # Legacy methods for backward compatibility
    def extract_data(self, file_path: str, document_type: str) -> Dict:
        """
        Legacy method - redirects to universal extraction.

        Args:
            file_path: Path to document
            document_type: Document type hint

        Returns:
            Extracted data
        """
        logger.info(f"Legacy extract_data called, redirecting to universal extraction")
        return self.extract_universal_data(file_path, document_type)
