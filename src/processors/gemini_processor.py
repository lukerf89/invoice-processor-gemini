import json
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiProcessor:
    """Handles Gemini AI processing for invoices"""
    
    def __init__(self, config_loader):
        self.config = config_loader
        self.model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini AI with API key"""
        api_key = self.config.get('gemini_api_key')
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.config.get('gemini_model', 'gemini-1.5-pro'))
        logger.info(f"Gemini initialized with model: {self.config.get('gemini_model')}")
    
    def process_document(self, pdf_content: bytes, filename: str = "invoice.pdf") -> Dict[str, Any]:
        """Process invoice using Gemini AI"""
        
        # Luke's exact prompt for invoice parsing
        prompt = """You are an invoice parser. Your job is to extract product information from this invoice that will go into a Google Sheet.

Here is the information I need you to pull from the invoices:
* Order date (Format as MM/DD/YYYY)
* Vendor (Extract the vendor's business name from the invoice header or footer)
* INV (this is the Invoice number or order number)
* Item (Combine all identifying information (SKU, ISBN, item name, etc.) into a single cell. Separate different values using a dash and a space.)
* Wholesale (Per-unit price. Look for terms such as "Your Price", "Unit Price", or "Price". Remove currency symbols.)
* Qty ordered (Quantity shipped. Leave blank if not available or if item is on backorder)

IMPORTANT RULES:
1. Extract ONLY actual products/merchandise - ignore taxes, shipping fees, discounts, subtotals, and totals
2. If multiple quantities are shown (ordered vs shipped), use the shipped quantity
3. For backorders or out-of-stock items, leave Qty ordered blank
4. Remove all currency symbols ($, etc.) from the Wholesale field
5. If unit price is not explicitly shown, calculate it from line total ÷ quantity
6. If no date is found, leave Order date blank
7. Return results in JSON format with this exact structure:

{
  "order_date": "MM/DD/YYYY",
  "vendor": "Vendor Business Name", 
  "invoice_number": "Invoice/Order Number",
  "line_items": [
    {
      "item": "SKU - Item Name - Additional Info",
      "wholesale": "0.00",
      "qty_ordered": "1"
    }
  ]
}

8. Return ONLY the JSON object - no additional text, formatting, or explanations
9. If you cannot find any products, return: {"order_date": "", "vendor": "", "invoice_number": "", "line_items": []}

Extract from this invoice:"""

        logger.info(f"🤖 Processing {filename} with Gemini...")
        
        try:
            # Send PDF to Gemini
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "application/pdf",
                    "data": pdf_content
                }
            ])
            
            # Parse response
            result_text = response.text.strip()
            
            # Clean JSON response
            result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            # Remove any markdown formatting
            if result_text.startswith('```'):
                result_text = result_text.split('\n', 1)[1]
            if result_text.endswith('```'):
                result_text = result_text.rsplit('\n', 1)[0]
            
            logger.debug(f"Gemini raw response (first 200 chars): {result_text[:200]}...")
            
            # Parse JSON
            gemini_result = json.loads(result_text)
            
            # Transform to standard format
            return self._transform_gemini_response(gemini_result, filename)
            
        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            raise
    
    def _transform_gemini_response(self, gemini_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Transform Gemini response to standard format"""
        
        # Calculate total from line items
        total_amount = 0
        line_items = []
        
        for item in gemini_data.get('line_items', []):
            try:
                wholesale = float(item.get('wholesale', '0').replace('$', '').replace(',', ''))
                qty = int(item.get('qty_ordered', '0') or '0')
                line_total = wholesale * qty
                total_amount += line_total
                
                line_items.append({
                    'description': item.get('item', ''),
                    'quantity': qty,
                    'unit_price': wholesale,
                    'amount': line_total
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing line item: {e}")
                continue
        
        return {
            'invoice_id': gemini_data.get('invoice_number', ''),
            'supplier_name': gemini_data.get('vendor', ''),
            'invoice_date': gemini_data.get('order_date', ''),
            'due_date': '',  # Not extracted by default prompt
            'total_amount': total_amount,
            'line_items': line_items,
            'filename': filename,
            'processing_method': 'gemini'
        }