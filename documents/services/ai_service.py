"""
AI Extraction Service using Ollama (Free Local LLM).

Provides intelligent data extraction from document text.
"""
import json
import ollama
from typing import Dict, Optional
from utils import loggings

logger = loggings.setup_logging()


class AIExtractionService:
    """
    Service for extracting structured data from text using AI.

    Uses Ollama with Llama 3.2 (free, runs locally).
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        """
        Initialize AI extraction service.

        Args:
            base_url: Ollama server URL
            model: Model to use for extraction
        """
        self.base_url = base_url
        self.model = model
        self.client = ollama.Client(host=base_url)
        logger.info(f"AI Extraction Service initialized with model: {model}")

    def extract_invoice_data(self, text: str) -> Dict:
        """
        Extract structured data from invoice text.

        Args:
            text: OCR extracted text from invoice

        Returns:
            Dictionary containing extracted invoice data
        """
        prompt = f"""
            You are an expert at extracting structured data from invoices.

            Extract the following information from this invoice text and return ONLY a valid JSON object:

            Required fields:
            - vendor (company name)
            - invoice_number
            - date (YYYY-MM-DD format)
            - due_date (YYYY-MM-DD format if available)
            - subtotal (number)
            - tax (number)
            - total (number)
            - currency (USD, EUR, etc.)
            - items (array of objects with: description, quantity, unit_price, amount)

            Invoice Text:
            {text}

            Return ONLY the JSON object, no explanations or markdown formatting.
        """

        try:
            logger.info("Extracting invoice data using AI")
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,  # Low temperature for consistent extraction
                    'top_p': 0.9,
                }
            )

            # Parse the response
            result_text = response['response'].strip()

            # Try to extract JSON from response
            data = self._extract_json(result_text)

            logger.info("Successfully extracted invoice data")
            return data

        except Exception as e:
            logger.exception(f"Error extracting invoice data: {str(e)}")
            return self._get_fallback_invoice_data()

    def extract_receipt_data(self, text: str) -> Dict:
        """
        Extract structured data from receipt text.

        Args:
            text: OCR extracted text from receipt

        Returns:
            Dictionary containing extracted receipt data
        """
        prompt = f"""
            You are an expert at extracting structured data from receipts. You must extract EXACT values from the text, not make up or guess values.

            IMPORTANT RULES:
            1. Extract ONLY what you see in the text
            2. For dates: Use YYYY-MM-DD format (e.g., 2025-01-02 not 01/02/7025)
            3. For prices: Extract exact numbers (e.g., 50000 not 245.5)
            4. For store names: Extract the exact name as written
            5. If you cannot find a field, use null (not "Unknown")

            Extract these fields from the receipt text below:

            Required fields:
            - store_name: The exact store/business name
            - date: Transaction date in YYYY-MM-DD format
            - time: Transaction time in HH:MM:SS format (or null if not found)
            - total: The TOTAL amount paid (look for "Total", "Total Paid", "Amount")
            - payment_method: How it was paid (Cash, Card, Mobile Money, etc.)
            - items: Array of items purchased with name and price

            Receipt Text:
            {text}

            CRITICAL: Return ONLY a valid JSON object. No explanations, no markdown, no code blocks.
            Example format:
            {{
            "store_name": "Store Name Here",
            "date": "2025-01-02",
            "time": "10:23:56",
            "total": 50000,
            "payment_method": "Cash",
            "items": [
                {{"name": "Item 1", "price": 1000}},
                {{"name": "Item 2", "price": 2000}}
            ]
            }}
        """

        try:
            logger.info("Extracting receipt data using AI")
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                }
            )

            result_text = response['response'].strip()
            data = self._extract_json(result_text)

            logger.info("Successfully extracted receipt data")
            return data

        except Exception as e:
            logger.exception(f"Error extracting receipt data: {str(e)}")
            return self._get_fallback_receipt_data()

    def extract_contract_data(self, text: str) -> Dict:
        """
        Extract structured data from contract text.

        Args:
            text: OCR extracted text from contract

        Returns:
            Dictionary containing extracted contract data
        """
        prompt = f"""
            You are an expert at extracting structured data from contracts.

            Extract the following information from this contract text and return ONLY a valid JSON object:

            Required fields:
            - title (contract title)
            - parties (array of party names)
            - start_date (YYYY-MM-DD format)
            - end_date (YYYY-MM-DD format if available)
            - value (number, if monetary value mentioned)
            - key_terms (array of important terms/clauses)

            Contract Text:
            {text}

            Return ONLY the JSON object, no explanations or markdown formatting.
        """

        try:
            logger.info("Extracting contract data using AI")
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                }
            )

            result_text = response['response'].strip()
            data = self._extract_json(result_text)

            logger.info("Successfully extracted contract data")
            return data

        except Exception as e:
            logger.exception(f"Error extracting contract data: {str(e)}")
            return self._get_fallback_contract_data()

    def extract_data(self, text: str, document_type: str) -> Dict:
        """
        Extract structured data based on document type.

        Args:
            text: OCR extracted text
            document_type: Type of document (invoice, receipt, contract, etc.)

        Returns:
            Dictionary containing extracted data
        """
        extraction_methods = {
            'invoice': self.extract_invoice_data,
            'receipt': self.extract_receipt_data,
            'contract': self.extract_contract_data,
        }

        method = extraction_methods.get(document_type)

        if method:
            return method(text)
        else:
            logger.warning(f"No specific extraction method for {document_type}, using generic extraction")
            return self._extract_generic_data(text, document_type)

    def _extract_generic_data(self, text: str, document_type: str) -> Dict:
        """
        Generic data extraction for unsupported document types.

        Args:
            text: Document text
            document_type: Type of document

        Returns:
            Dictionary with basic extracted information
        """
        return {
            'document_type': document_type,
            'text_preview': text[:500] if len(text) > 500 else text,
            'text_length': len(text),
            'message': f'Generic extraction for {document_type}'
        }

    def _extract_json(self, text: str) -> Dict:
        """
        Extract JSON from AI response text.

        Args:
            text: Response text that may contain JSON

        Returns:
            Parsed JSON dictionary
        """
        # Remove markdown code blocks if present
        text = text.replace('```json', '').replace('```', '').strip()

        # Try to find JSON object in text
        start = text.find('{')
        end = text.rfind('}') + 1

        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        else:
            # If no JSON found, try parsing the whole text
            return json.loads(text)

    def _get_fallback_invoice_data(self) -> Dict:
        """Return fallback data structure for invoices."""
        return {
            'vendor': 'Unknown',
            'invoice_number': 'N/A',
            'date': None,
            'due_date': None,
            'subtotal': 0.0,
            'tax': 0.0,
            'total': 0.0,
            'currency': 'USD',
            'items': [],
            'extraction_status': 'failed'
        }

    def _get_fallback_receipt_data(self) -> Dict:
        """Return fallback data structure for receipts."""
        return {
            'store_name': 'Unknown',
            'date': None,
            'time': None,
            'total': 0.0,
            'payment_method': 'Unknown',
            'items': [],
            'extraction_status': 'failed'
        }

    def _get_fallback_contract_data(self) -> Dict:
        """Return fallback data structure for contracts."""
        return {
            'title': 'Unknown',
            'parties': [],
            'start_date': None,
            'end_date': None,
            'value': None,
            'key_terms': [],
            'extraction_status': 'failed'
        }
