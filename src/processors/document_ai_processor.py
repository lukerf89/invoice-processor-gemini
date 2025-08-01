import logging
from typing import Dict, Any, List, Optional
from google.cloud import documentai_v1 as documentai
from google.api_core.client_options import ClientOptions
import os

logger = logging.getLogger(__name__)

class DocumentAIProcessor:
    """Handles Document AI processing for invoices"""
    
    def __init__(self, config_loader):
        self.config = config_loader
        self.client = None
        self._initialize_document_ai()
    
    def _initialize_document_ai(self):
        """Initialize Document AI client"""
        # Set credentials if available
        creds_path = self.config.get_credentials_path()
        if creds_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
        
        # Initialize client with location
        location = self.config.get('processor_location', 'us')
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        logger.info(f"Document AI client initialized for location: {location}")
    
    def process_document(self, pdf_content: bytes, filename: str = "invoice.pdf") -> Dict[str, Any]:
        """Process invoice using Document AI"""
        
        project_id = self.config.get('project_id')
        processor_id = self.config.get('processor_id')
        location = self.config.get('processor_location', 'us')
        
        if not all([project_id, processor_id]):
            raise ValueError("Document AI configuration incomplete")
        
        logger.info(f"🤖 Processing {filename} with Document AI...")
        
        try:
            # Configure processor path
            processor_name = self.client.processor_path(project_id, location, processor_id)
            
            # Create request
            document = documentai.Document(
                content=pdf_content,
                mime_type="application/pdf"
            )
            
            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=documentai.RawDocument(
                    content=pdf_content,
                    mime_type="application/pdf"
                )
            )
            
            # Process document
            result = self.client.process_document(request=request)
            document = result.document
            
            # Extract entities
            entities = {entity.type_: entity.mention_text for entity in document.entities}
            
            logger.info(f"Document AI found {len(entities)} entities")
            
            # Extract line items using multiple methods
            line_items = self._extract_line_items(document, entities)
            
            # Build response
            return {
                'invoice_id': entities.get('invoice_id', entities.get('invoice_number', '')),
                'supplier_name': entities.get('supplier_name', ''),
                'invoice_date': self._format_date(entities.get('invoice_date', '')),
                'due_date': self._format_date(entities.get('due_date', '')),
                'total_amount': self._parse_currency(entities.get('total_amount', '0')),
                'line_items': line_items,
                'filename': filename,
                'processing_method': 'document_ai',
                'raw_entities': entities  # For debugging
            }
            
        except Exception as e:
            logger.error(f"Document AI processing failed: {e}")
            raise
    
    def _extract_line_items(self, document: documentai.Document, entities: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract line items using multiple methods"""
        line_items = []
        
        # Method 1: Extract from entities
        line_items_from_entities = self._extract_line_items_from_entities(document)
        if line_items_from_entities:
            line_items.extend(line_items_from_entities)
        
        # Method 2: Extract from tables
        line_items_from_tables = self._extract_line_items_from_tables(document)
        if line_items_from_tables:
            line_items.extend(line_items_from_tables)
        
        # Method 3: Extract from text (fallback)
        if not line_items:
            line_items_from_text = self._extract_line_items_from_text(document.text, entities)
            if line_items_from_text:
                line_items.extend(line_items_from_text)
        
        # Deduplicate
        seen = set()
        unique_items = []
        for item in line_items:
            key = (item.get('description', ''), item.get('quantity', 0), item.get('unit_price', 0))
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        
        return unique_items
    
    def _extract_line_items_from_entities(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract line items from Document AI entities"""
        line_items = []
        
        for entity in document.entities:
            if entity.type_ == 'line_item':
                item_data = {
                    'description': '',
                    'quantity': 0,
                    'unit_price': 0,
                    'amount': 0
                }
                
                # Extract properties
                for prop in entity.properties:
                    if prop.type_ == 'line_item/description':
                        item_data['description'] = prop.mention_text
                    elif prop.type_ == 'line_item/quantity':
                        item_data['quantity'] = self._parse_quantity(prop.mention_text)
                    elif prop.type_ == 'line_item/unit_price':
                        item_data['unit_price'] = self._parse_currency(prop.mention_text)
                    elif prop.type_ == 'line_item/amount':
                        item_data['amount'] = self._parse_currency(prop.mention_text)
                
                if item_data['description']:
                    line_items.append(item_data)
        
        return line_items
    
    def _extract_line_items_from_tables(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract line items from tables in the document"""
        line_items = []
        
        for page in document.pages:
            for table in page.tables:
                # Skip if no header row
                if not table.header_rows:
                    continue
                
                # Find column indices
                col_indices = self._identify_table_columns(table)
                
                # Extract data rows
                for row_idx in range(len(table.header_rows), len(table.body_rows)):
                    row_data = self._extract_table_row(table, row_idx, col_indices)
                    if row_data and row_data.get('description'):
                        line_items.append(row_data)
        
        return line_items
    
    def _extract_line_items_from_text(self, text: str, entities: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract line items using regex patterns (fallback)"""
        import re
        
        line_items = []
        
        # Common patterns for line items
        patterns = [
            # Pattern: SKU/Code Description Qty Price Total
            r'([A-Z0-9\-]+)\s+(.+?)\s+(\d+)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)',
            # Pattern: Description Qty @ Price = Total
            r'(.+?)\s+(\d+)\s*@\s*\$?([\d,]+\.?\d*)\s*=?\s*\$?([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 4:
                    line_items.append({
                        'description': groups[0] + ' ' + groups[1] if len(groups) > 4 else groups[0],
                        'quantity': self._parse_quantity(groups[2] if len(groups) > 4 else groups[1]),
                        'unit_price': self._parse_currency(groups[3] if len(groups) > 4 else groups[2]),
                        'amount': self._parse_currency(groups[4] if len(groups) > 4 else groups[3])
                    })
        
        return line_items
    
    def _identify_table_columns(self, table) -> Dict[str, int]:
        """Identify column indices for relevant fields"""
        col_indices = {}
        
        if not table.header_rows:
            return col_indices
        
        header_row = table.header_rows[0]
        for idx, cell in enumerate(header_row.cells):
            cell_text = self._get_cell_text(cell).lower()
            
            if any(keyword in cell_text for keyword in ['description', 'item', 'product']):
                col_indices['description'] = idx
            elif any(keyword in cell_text for keyword in ['qty', 'quantity', 'shipped']):
                col_indices['quantity'] = idx
            elif any(keyword in cell_text for keyword in ['price', 'unit', 'each']):
                col_indices['unit_price'] = idx
            elif any(keyword in cell_text for keyword in ['total', 'amount', 'extended']):
                col_indices['amount'] = idx
        
        return col_indices
    
    def _extract_table_row(self, table, row_idx: int, col_indices: Dict[str, int]) -> Optional[Dict[str, Any]]:
        """Extract data from a table row"""
        if row_idx >= len(table.body_rows):
            return None
        
        row = table.body_rows[row_idx]
        row_data = {
            'description': '',
            'quantity': 0,
            'unit_price': 0,
            'amount': 0
        }
        
        for field, col_idx in col_indices.items():
            if col_idx < len(row.cells):
                cell_text = self._get_cell_text(row.cells[col_idx])
                
                if field == 'description':
                    row_data[field] = cell_text
                elif field == 'quantity':
                    row_data[field] = self._parse_quantity(cell_text)
                elif field in ['unit_price', 'amount']:
                    row_data[field] = self._parse_currency(cell_text)
        
        return row_data
    
    def _get_cell_text(self, cell) -> str:
        """Extract text from a table cell"""
        if hasattr(cell, 'layout') and hasattr(cell.layout, 'text_anchor'):
            return cell.layout.text_anchor.content
        return ''
    
    def _format_date(self, date_str: str) -> str:
        """Format date to MM/DD/YYYY"""
        if not date_str:
            return ''
        
        from datetime import datetime
        
        # Try various date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%B %d, %Y',
            '%b %d, %Y'
        ]
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime('%m/%d/%Y')
            except ValueError:
                continue
        
        # Return original if no format matches
        return date_str
    
    def _parse_currency(self, value: str) -> float:
        """Parse currency string to float"""
        if not value:
            return 0.0
        
        # Remove currency symbols and commas
        cleaned = value.replace('$', '').replace(',', '').strip()
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    def _parse_quantity(self, value: str) -> int:
        """Parse quantity string to int"""
        if not value:
            return 0
        
        # Extract numeric part
        import re
        match = re.search(r'\d+', value)
        if match:
            try:
                return int(match.group())
            except ValueError:
                return 0
        
        return 0