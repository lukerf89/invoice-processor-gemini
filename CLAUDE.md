# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL CODING PRINCIPLE

**NEVER hard-code solutions in main.py. ALWAYS find a logic method that produces the correct output.**

When processing invoices, you may encounter edge cases or specific formatting issues. The correct approach is to:
- ✅ Use regex patterns and logical rules
- ✅ Extract information from document text using pattern matching
- ✅ Create reusable functions that work across different invoices
- ✅ Implement context-aware processing that adapts to document structure

❌ **DO NOT:** Create if/else statements that check for specific product codes and manually assign values
❌ **DO NOT:** Hard-code expected outputs for specific items
❌ **DO NOT:** Use product-specific logic that won't work for other invoices

The goal is maintainable, scalable code that can handle new invoices without modification.

## Project Overview

This is a Google Cloud Function that processes invoices using a multi-tier AI approach. It receives webhook requests from Zapier (or legacy Trello) with PDF files or URLs, processes invoices using Gemini AI first (with Document AI as fallback), then writes extracted data to Google Sheets.

## Tech Stack

- **Runtime**: Python 3.12+ 
- **Framework**: Google Cloud Functions with functions-framework
- **Cloud Services**: Google Cloud Document AI, Google Sheets API, Google Gemini AI, Secret Manager
- **Key Dependencies**: google-cloud-documentai, google-generativeai, google-auth, google-api-python-client, requests, flask

## Development Commands

```bash
# Setup virtual environment (required for dependencies)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (includes testing and linting tools)
pip install -r requirements.dev.txt

# Local development server
functions-framework --target=process_invoice --debug

# Linting and formatting
black .  # Format code to Black style
isort .  # Sort imports

# Run unit tests (from venv)
venv/bin/pytest  # Run all tests
venv/bin/pytest test_scripts/test_invoice_processing.py  # Run specific test file
venv/bin/pytest-watch  # Watch mode for continuous testing

# Deploy to Google Cloud
./deploy.sh  # Deploys function with proper environment variables and secrets
```

## Testing Commands

```bash
# Test with sample data (JSON method)
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"file_url": "https://example.com/invoice.pdf"}'

# Test with form data (Zapier method)
curl -X POST http://localhost:8080 \
  -F "file_url=https://example.com/invoice.pdf"

# Test with file upload (Zapier method)
curl -X POST http://localhost:8080 \
  -F "invoice_file=@/path/to/invoice.pdf"

# Debug Document AI output
python document_ai_explorer.py <pdf_file_path> [--save-json]

# Test Gemini AI processing
python test_gemini.py

# Automated invoice testing workflow
./test_invoice.sh InvoiceName  # Generates JSON and CSV from PDF

# Run vendor-specific test scripts
python test_scripts/test_final_creative_coop.py  # Creative-Coop testing
python test_scripts/perfect_processing.py  # HarperCollins processing
python test_scripts/test_onehundred80.py  # OneHundred80 testing

# Run all vendor tests
python test_scripts/test_final_creative_coop.py && python test_scripts/perfect_processing.py && python test_scripts/test_onehundred80.py
```

## Architecture Overview

### Processing Flow
1. **Request Handler** (`process_invoice`): Entry point that handles webhook requests from Zapier/Trello
2. **Multi-tier Processing**:
   - **Tier 1**: Gemini AI (`process_with_gemini_first`) - Primary method using Google's Gemini AI model
   - **Tier 2**: Document AI Entities (`extract_line_items_from_entities`) - Uses structured entity extraction
   - **Tier 3**: Document AI Tables (`extract_line_items`) - Processes table data from Document AI
   - **Tier 4**: Text Parsing (`extract_line_items_from_text`) - Fallback regex-based extraction

### Vendor-Specific Processing
The system includes specialized handling for different vendors in `main.py`:
- **HarperCollins**: Handles multi-line descriptions, ISBN extraction
- **Creative-Coop**: Processes split quantity formats, UPC/style code mapping
- **OneHundred80**: Handles compact table layouts
- **Rifle Paper**: Custom description cleaning and line item extraction

### Key Functions
- `format_date()`: Standardizes date formats across different invoice styles
- `process_vendor_specific()`: Routes to vendor-specific processing logic
- `write_to_sheet()`: Handles Google Sheets API integration with proper authentication
- `clean_and_validate_quantity()`: Ensures quantity values are properly formatted integers

### Environment Variables
Required for deployment (set in `deploy.sh`):
- `GOOGLE_CLOUD_PROJECT_ID`: GCP project ID
- `DOCUMENT_AI_PROCESSOR_ID`: Document AI processor ID
- `GOOGLE_CLOUD_LOCATION`: Processing location (usually "us")
- `GOOGLE_SHEETS_SPREADSHEET_ID`: Target spreadsheet ID
- `GOOGLE_SHEETS_SHEET_NAME`: Target sheet name
- `GEMINI_API_KEY`: Stored in Secret Manager

### Testing Infrastructure
- `test_invoices/`: Directory containing sample PDFs and expected outputs
- `test_scripts/`: Vendor-specific testing and debugging scripts
- `document_ai_explorer.py`: Standalone tool for analyzing Document AI output
- `test_invoice.sh`: Automated workflow for generating JSON and CSV from PDFs

## Important Notes

- Always activate the virtual environment before running tests or development server
- The function uses Application Default Credentials (ADC) for Google Cloud services
- Gemini API key is stored in Google Secret Manager for production
- Processing timeout is set to 540 seconds for large invoices
- Memory allocation is 1GB to handle PDF processing