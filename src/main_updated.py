import os
import re
import json
import logging
from datetime import datetime
import traceback

import functions_framework
import requests
from flask import Request, jsonify

# Import our new configuration system
from utils.config_loader import ConfigLoader
from utils.validation import EnvironmentValidator
from processors.gemini_processor import GeminiProcessor
from processors.document_ai_processor import DocumentAIProcessor

# Initialize configuration
config = ConfigLoader()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG if config.get('debug_mode') else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import existing helper functions
from google.auth import default
from google.cloud import documentai_v1 as documentai
from googleapiclient.discovery import build


class InvoiceProcessor:
    """Main invoice processing orchestrator"""

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader
        self.gemini_processor = None
        self.document_ai_processor = None
        self._initialize_processors()

    def _initialize_processors(self):
        """Initialize processing engines"""
        try:
            # Initialize Gemini processor if configured
            if self.config.get('gemini_api_key') and self.config.get('use_gemini_first'):
                self.gemini_processor = GeminiProcessor(self.config)
                logger.info("✅ Gemini processor initialized")

            # Initialize Document AI processor
            if all([self.config.get('project_id'), self.config.get('processor_id')]):
                self.document_ai_processor = DocumentAIProcessor(self.config)
                logger.info("✅ Document AI processor initialized")

            if not self.gemini_processor and not self.document_ai_processor:
                raise ValueError("No processors could be initialized")

        except Exception as e:
            logger.error(f"❌ Processor initialization failed: {e}")
            raise

    def process_invoice_content(self, pdf_content: bytes, filename: str = "invoice.pdf"):
        """Process invoice using multi-tier approach"""
        logger.info(f"🔄 Processing invoice: {filename}")

        # Try Gemini first if available and configured
        if self.gemini_processor and self.config.get('use_gemini_first'):
            logger.info("🎯 Attempting Gemini processing...")
            try:
                gemini_result = self.gemini_processor.process_document(pdf_content, filename)
                
                # Convert to rows format for compatibility
                if gemini_result and gemini_result.get('line_items'):
                    rows = self._convert_to_row_format(gemini_result)
                    if rows:
                        logger.info(f"✅ Gemini successfully extracted {len(rows)} line items")
                        return rows, gemini_result.get('invoice_date'), gemini_result.get('supplier_name'), gemini_result.get('invoice_id')
                    
                logger.warning("⚠️  Gemini extraction incomplete, trying Document AI...")

            except Exception as e:
                logger.warning(f"⚠️  Gemini processing failed: {e}")

        # Fallback to Document AI
        if self.document_ai_processor:
            logger.info("🤖 Attempting Document AI processing...")
            try:
                # Process with Document AI using existing logic
                doc_ai_result = process_with_document_ai(
                    pdf_content, 
                    filename,
                    self.config.get('project_id'),
                    self.config.get('processor_id'),
                    self.config.get('processor_location', 'us')
                )
                
                if doc_ai_result:
                    logger.info("✅ Document AI processing successful")
                    return doc_ai_result
                    
            except Exception as e:
                logger.error(f"❌ Document AI processing failed: {e}")

        # If we get here, both methods failed
        logger.error("❌ All processing methods failed")
        return None

    def _convert_to_row_format(self, result):
        """Convert standard result format to row format for compatibility"""
        rows = []
        
        invoice_date = result.get('invoice_date', '')
        vendor = result.get('supplier_name', '')
        invoice_number = result.get('invoice_id', '')
        
        for item in result.get('line_items', []):
            # Build item description
            item_desc = item.get('description', '')
            
            # Extract wholesale price
            wholesale = str(item.get('unit_price', ''))
            if wholesale:
                wholesale = wholesale.replace('$', '').replace(',', '')
            
            # Extract quantity
            qty = str(item.get('quantity', ''))
            
            rows.append([
                "",  # Column A placeholder
                invoice_date,
                vendor,
                invoice_number,
                item_desc,
                wholesale,
                qty
            ])
        
        return rows


# Initialize processor
processor = InvoiceProcessor(config)


# Keep all existing helper functions
def format_date(raw_date):
    """Format date string to MM/DD/YYYY format"""
    if not raw_date:
        return ""
    
    # Handle already formatted dates
    if re.match(r'^\d{2}/\d{2}/\d{4}$', raw_date):
        return raw_date
    
    # Common date patterns
    date_patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', '{1}/{2}/{0}'),  # YYYY-MM-DD
        (r'(\d{2})-(\d{2})-(\d{4})', '{0}/{1}/{2}'),  # MM-DD-YYYY
        (r'(\d{2})/(\d{2})/(\d{2})$', '{0}/{1}/20{2}'),  # MM/DD/YY
        (r'(\w+)\s+(\d{1,2}),?\s+(\d{4})', None),  # Month DD, YYYY
        (r'(\d{1,2})\s+(\w+)\s+(\d{4})', None),  # DD Month YYYY
    ]
    
    for pattern, format_str in date_patterns:
        match = re.search(pattern, raw_date)
        if match:
            if format_str:
                return format_str.format(*match.groups())
            else:
                # Handle month name formats
                month_map = {
                    'january': '01', 'jan': '01', 'february': '02', 'feb': '02',
                    'march': '03', 'mar': '03', 'april': '04', 'apr': '04',
                    'may': '05', 'june': '06', 'jun': '06', 'july': '07', 'jul': '07',
                    'august': '08', 'aug': '08', 'september': '09', 'sep': '09', 'sept': '09',
                    'october': '10', 'oct': '10', 'november': '11', 'nov': '11',
                    'december': '12', 'dec': '12'
                }
                
                groups = match.groups()
                if pattern.startswith(r'(\w+)'):  # Month DD, YYYY
                    month = month_map.get(groups[0].lower(), groups[0])
                    return f"{month}/{groups[1].zfill(2)}/{groups[2]}"
                else:  # DD Month YYYY
                    month = month_map.get(groups[1].lower(), groups[1])
                    return f"{month}/{groups[0].zfill(2)}/{groups[2]}"
    
    # Try datetime parsing as last resort
    try:
        from datetime import datetime
        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y']:
            try:
                dt = datetime.strptime(raw_date.strip(), fmt)
                return dt.strftime('%m/%d/%Y')
            except ValueError:
                continue
    except:
        pass
    
    return raw_date


def process_with_document_ai(pdf_content, filename, project_id, processor_id, location='us'):
    """Process document using Document AI (existing logic preserved)"""
    try:
        # Set credentials if available
        creds_path = config.get_credentials_path()
        if creds_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
        
        # Create Document AI client
        client = documentai.DocumentProcessorServiceClient()
        
        # Configure processor
        name = client.processor_path(project_id, location, processor_id)
        
        # Configure the process request
        request = documentai.ProcessRequest(
            name=name,
            raw_document=documentai.RawDocument(
                content=pdf_content,
                mime_type="application/pdf"
            )
        )
        
        # Process the document
        result = client.process_document(request=request)
        document = result.document
        
        # Extract entities
        entities = {}
        for entity in document.entities:
            entities[entity.type_] = entity.mention_text
        
        # Extract metadata
        supplier_name = entities.get('supplier_name', 'Unknown Vendor')
        raw_invoice_date = entities.get('invoice_date', '')
        invoice_date = format_date(raw_invoice_date) if raw_invoice_date else datetime.now().strftime("%m/%d/%Y")
        
        # Extract invoice number
        invoice_number = entities.get('invoice_id', entities.get('invoice_number', ''))
        if not invoice_number and filename:
            # Try to extract from filename
            invoice_match = re.search(r'INV[_-]?([A-Z0-9]+)', filename)
            if invoice_match:
                invoice_number = invoice_match.group(1)
        
        logger.info(f"Extracted metadata - Vendor: {supplier_name}, Date: {invoice_date}, Invoice: {invoice_number}")
        
        # Try multiple extraction methods
        rows = extract_line_items_from_entities(document, invoice_date, supplier_name, invoice_number)
        
        if not rows:
            logger.info("No line items from entities, trying table extraction...")
            rows = extract_line_items(document, invoice_date, supplier_name, invoice_number)
        
        if not rows:
            logger.info("No line items from tables, trying text extraction...")
            rows = extract_line_items_from_text(document.text, invoice_date, supplier_name, invoice_number)
        
        return rows, invoice_date, supplier_name, invoice_number
        
    except Exception as e:
        logger.error(f"Document AI processing error: {e}")
        raise


# Include all the existing extraction functions
def extract_line_items_from_entities(document, invoice_date, vendor, invoice_number):
    """Extract line items from Document AI entities (existing implementation)"""
    rows = []
    
    for entity in document.entities:
        if entity.type_ == "line_item":
            line_item_data = {
                'product_code': '',
                'description': '',
                'quantity': '',
                'unit_price': ''
            }
            
            # Extract line item properties
            for prop in entity.properties:
                if prop.type_ == "line_item/product_code":
                    line_item_data['product_code'] = prop.mention_text
                elif prop.type_ == "line_item/description":
                    line_item_data['description'] = prop.mention_text
                elif prop.type_ == "line_item/quantity":
                    line_item_data['quantity'] = prop.mention_text
                elif prop.type_ == "line_item/unit_price":
                    price_text = prop.mention_text.replace('$', '').replace(',', '').strip()
                    line_item_data['unit_price'] = price_text
            
            # Build consolidated item description
            item_parts = []
            if line_item_data['product_code']:
                item_parts.append(line_item_data['product_code'])
            if line_item_data['description']:
                item_parts.append(line_item_data['description'])
            
            if item_parts:
                rows.append([
                    "",  # Column A placeholder
                    invoice_date,
                    vendor,
                    invoice_number,
                    " - ".join(item_parts),
                    line_item_data['unit_price'],
                    line_item_data['quantity']
                ])
    
    return rows


def extract_line_items(document, invoice_date, vendor, invoice_number):
    """Extract line items from tables (existing implementation)"""
    rows = []
    
    for page in document.pages:
        for table in page.tables:
            # Identify column headers
            header_cols = {}
            if table.header_rows:
                for header_row in table.header_rows:
                    for idx, cell in enumerate(header_row.cells):
                        if hasattr(cell.layout, 'text_anchor'):
                            header_text = cell.layout.text_anchor.content.lower()
                            
                            # Map headers to column indices
                            if any(term in header_text for term in ['item', 'sku', 'product', 'code', 'isbn']):
                                header_cols['item'] = idx
                            elif any(term in header_text for term in ['description', 'title', 'name']):
                                header_cols['description'] = idx
                            elif any(term in header_text for term in ['qty', 'quantity', 'shipped']):
                                header_cols['quantity'] = idx
                            elif any(term in header_text for term in ['price', 'unit', 'each', 'wholesale']):
                                header_cols['price'] = idx
            
            # Process data rows
            for row in table.body_rows:
                row_data = {}
                
                for col_type, col_idx in header_cols.items():
                    if col_idx < len(row.cells):
                        cell = row.cells[col_idx]
                        if hasattr(cell.layout, 'text_anchor'):
                            row_data[col_type] = cell.layout.text_anchor.content.strip()
                
                # Build item description
                item_parts = []
                if row_data.get('item'):
                    item_parts.append(row_data['item'])
                if row_data.get('description'):
                    item_parts.append(row_data['description'])
                
                # Extract and clean price
                price = row_data.get('price', '')
                if price:
                    price = price.replace('$', '').replace(',', '').strip()
                
                # Add row if we have meaningful data
                if item_parts and (row_data.get('quantity') or price):
                    rows.append([
                        "",  # Column A placeholder
                        invoice_date,
                        vendor,
                        invoice_number,
                        " - ".join(item_parts),
                        price,
                        row_data.get('quantity', '')
                    ])
    
    return rows


def extract_line_items_from_text(text, invoice_date, vendor, invoice_number):
    """Extract line items using regex patterns (existing implementation)"""
    rows = []
    
    # Split into lines
    lines = text.split('\n')
    
    # Patterns for line items
    patterns = [
        # Pattern: SKU/Code Description Qty Price
        r'^([A-Z0-9\-\.]+)\s+(.+?)\s+(\d+)\s+\$?([\d,]+\.?\d*)$',
        # Pattern: Code | Description | Qty | Price
        r'^([A-Z0-9\-\.]+)\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*\$?([\d,]+\.?\d*)$',
        # Pattern: Description (with code) Qty @ Price
        r'^(.+?)\s+\(([A-Z0-9\-\.]+)\)\s+(\d+)\s*@\s*\$?([\d,]+\.?\d*)$',
    ]
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 4:
                    code = groups[0]
                    desc = groups[1]
                    qty = groups[2]
                    price = groups[3].replace(',', '')
                    
                    # Build item description
                    item = f"{code} - {desc}" if code != desc else desc
                    
                    rows.append([
                        "",  # Column A placeholder
                        invoice_date,
                        vendor,
                        invoice_number,
                        item,
                        price,
                        qty
                    ])
                    break
    
    return rows


def find_next_empty_row(service, spreadsheet_id, sheet_name, start_column='A', end_column='G'):
    """Find the next empty row in the sheet using smart detection - checks ALL columns A:G, places immediately after last used row"""
    try:
        # Get all values in the full range A:G to find the true last row with ANY data
        range_name = f"{sheet_name}!{start_column}:{end_column}"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        # If no data at all, start at row 2 (assuming row 1 has headers)
        if not values:
            return 2
        
        # Find the true last row with data by checking ALL columns A:G
        last_row_with_data = 0
        for i, row in enumerate(values):
            # Check if any cell in this row has data
            if row and any(cell.strip() for cell in row if cell):
                last_row_with_data = i + 1  # Convert to 1-based row number
        
        # If no data found in any row, start at row 2
        if last_row_with_data == 0:
            return 2
        
        # Return the row immediately after the last row with data (no gaps)
        next_available_row = last_row_with_data + 1
        
        logger.info(f"📍 Last row with data: {last_row_with_data}, next available row: {next_available_row}")
        return next_available_row
        
    except Exception as e:
        logger.warning(f"Could not determine next empty row, defaulting to append: {e}")
        # If there's an error, fall back to regular append behavior
        return None


def write_to_google_sheets(rows, sheet_name=None):
    """Write processed data to Google Sheets with smart row detection"""
    try:
        # Get configuration
        spreadsheet_id = config.get('sheets_id')
        if not sheet_name:
            sheet_name = config.get('sheet_name', 'Update 20230525')
        
        # Set up credentials
        creds_path = config.get_credentials_path()
        if not creds_path:
            raise ValueError("No service account credentials found")
        
        from google.oauth2 import service_account
        
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Find the next empty row
        next_row = find_next_empty_row(service, spreadsheet_id, sheet_name)
        
        # Prepare the data
        values = rows
        
        body = {
            'values': values
        }
        
        if next_row:
            # Use specific range starting from the next empty row
            range_name = f"{sheet_name}!A{next_row}:G{next_row + len(rows) - 1}"
            logger.info(f"📍 Writing to specific range: {range_name}")
            
            # Use update instead of append for specific range
            result = service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        else:
            # Fall back to append if we couldn't determine the next row
            logger.info("📍 Using standard append method")
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:G",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        
        logger.info(f"✅ Successfully wrote {len(rows)} rows to Google Sheets")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to write to Google Sheets: {e}")
        raise


@functions_framework.http
def process_invoice(request: Request):
    """Google Cloud Function entry point"""
    
    # Log environment info (once)
    if config.get('debug_mode'):
        config.print_config_summary()
    
    # Check request method
    if request.method != "POST":
        return jsonify({"error": "Method Not Allowed"}), 405
    
    try:
        pdf_content = None
        filename = "invoice.pdf"
        
        # Handle file upload from Zapier form POST
        if request.files and "invoice_file" in request.files:
            file = request.files["invoice_file"]
            filename = file.filename
            
            if not filename:
                return jsonify({"error": "No filename provided"}), 400
            
            pdf_content = file.read()
            
            if not pdf_content:
                return jsonify({"error": "Empty file received"}), 400
            
            logger.info(f"Received file upload: {filename}")
        
        else:
            # Handle URL-based requests
            file_url = None
            
            # Try form data first
            if request.form:
                file_url = request.form.get("file_url") or request.form.get("invoice_file")
            
            # Fallback to JSON
            if not file_url:
                request_json = request.get_json(silent=True)
                file_url = request_json.get("file_url") if request_json else None
            
            if not file_url:
                return jsonify({"error": "Missing invoice_file or file_url"}), 400
            
            # Download the file
            pdf_content, filename = download_file(file_url)
        
        # Process the invoice
        result = processor.process_invoice_content(pdf_content, filename)
        
        if not result:
            return jsonify({"error": "Failed to extract invoice data"}), 500
        
        rows, invoice_date, vendor, invoice_number = result
        
        if not rows:
            return jsonify({
                "warning": "No line items found in invoice",
                "invoice_date": invoice_date,
                "vendor": vendor,
                "invoice_number": invoice_number
            }), 200
        
        # Write to Google Sheets
        sheets_result = write_to_google_sheets(rows)
        
        return jsonify({
            "success": True,
            "message": f"Successfully processed invoice with {len(rows)} line items",
            "invoice_date": invoice_date,
            "vendor": vendor,
            "invoice_number": invoice_number,
            "rows_added": len(rows),
            "sheets_update": sheets_result.get('updates', {})
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Request processing failed: {e}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            "error": "Processing failed",
            "message": str(e),
            "traceback": traceback.format_exc() if config.get('debug_mode') else None
        }), 500


def download_file(file_url):
    """Download file from URL (existing implementation)"""
    logger.info(f"📥 Downloading file from: {file_url}")
    
    # Extract filename from URL
    filename = file_url.split('/')[-1].split('?')[0] or "invoice.pdf"
    
    # Special handling for Trello URLs
    if "trello.com" in file_url:
        session = requests.Session()
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/pdf,application/octet-stream,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://trello.com/"
        })
        
        # Try to get the file
        response = session.get(file_url, timeout=30, allow_redirects=True)
        
        if response.status_code == 401:
            # Try without authentication
            response = requests.get(file_url, timeout=30)
    else:
        # Standard download
        response = requests.get(file_url, timeout=config.get('timeout', 30))
    
    response.raise_for_status()
    
    # Validate it's a PDF
    content_type = response.headers.get('Content-Type', '')
    if 'pdf' not in content_type.lower() and not response.content.startswith(b'%PDF'):
        raise ValueError(f"Downloaded file does not appear to be a PDF. Content-Type: {content_type}")
    
    return response.content, filename


# For local development
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.route('/', methods=['POST'])(process_invoice)
    app.run(host='0.0.0.0', port=8080, debug=config.get('debug_mode'))