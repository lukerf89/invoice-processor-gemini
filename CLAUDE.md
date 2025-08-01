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

- **Runtime**: Python 3.12+ (originally 3.12.11)
- **Framework**: Google Cloud Functions with functions-framework
- **Cloud Services**: Google Cloud Document AI, Google Sheets API, Google Gemini AI
- **Key Dependencies**: google-cloud-documentai, google-generativeai, google-auth, google-api-python-client, requests, flask

## Project Setup (New Multi-Device Configuration System)

**IMPORTANT**: This project now uses an enhanced configuration management system for multi-device development.

### Initial Setup (Run Once Per Machine)
```bash
# 1. Run automated setup to create configuration files
python setup.py

# 2. Configure your environment (edit the created files):
#    - config/credentials.json (add your service account JSON)
#    - .env (add your API keys and project settings)
#    - config/app_config.json (customize application settings)

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements.dev.txt  # For development tools

# 4. Validate your setup
python setup.py --validate

# 5. Test environment
python test_scripts/test_environment.py
```

## Development Commands

```bash
# Setup virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Local development server (using new configuration system)
functions-framework --target=process_invoice --debug --source=src/main_updated.py

# Alternative: Run main file directly
cd src && python main_updated.py

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

# Debug Document AI output (requires environment variables)
python document_ai_explorer.py <pdf_file_path> [--save-json]

# Test with local sample invoice
python document_ai_explorer.py new_invoice.pdf --save-json

# Test Gemini AI processing
python test_gemini.py  # Test Gemini processing with sample PDF

# Run specific test scripts
python test_scripts/test_invoice_processing.py
python test_scripts/test_creative_coop.py
python test_scripts/test_integrated_main.py

# Test vendor-specific processing
python test_scripts/perfect_processing.py  # HarperCollins processing
python test_scripts/test_final_creative_coop.py  # Creative-Coop final testing
python test_scripts/test_onehundred80.py  # OneHundred80 testing

# Run all vendor-specific tests
python test_scripts/test_final_creative_coop.py && python test_scripts/perfect_processing.py && python test_scripts/test_onehundred80.py

# Run linting and formatting (with dev dependencies installed)
black .  # Format code to Black style
isort .  # Sort imports

# Run unit tests
pytest  # Run all tests
pytest test_scripts/test_invoice_processing.py  # Run specific test file
pytest-watch  # Watch mode for continuous testing during development

# Deploy to Google Cloud Functions
./deploy.sh  # Deploy the Cloud Function with Gemini support

# Test invoice processing workflow (requires test_invoices/ directory)
./test_invoice.sh <InvoiceName>  # e.g., ./test_invoice.sh Rifle_Paper_INV_J7XM9XQ3HB
```

## New Project Structure

The project now uses a modular, configuration-driven architecture:

```
invoice-processor-gemini/
├── src/
│   ├── main.py                         # Original main file (preserved)
│   ├── main_updated.py                 # New main with config system
│   ├── processors/                     # Modular processing engines
│   │   ├── gemini_processor.py         # Gemini AI processing
│   │   └── document_ai_processor.py    # Document AI processing
│   └── utils/                          # Configuration and utilities
│       ├── config_loader.py            # Hierarchical configuration loader
│       ├── validation.py               # Environment validation
│       └── document_ai_explorer.py     # Document AI debugging tool
├── config/                             # Configuration files (gitignored)
│   ├── *.template.json                 # Template files (safe to commit)
│   ├── credentials.json                # Service account (from template)
│   ├── app_config.json                 # App settings (from template)
│   └── sheets_config.json              # Sheets config (from template)
├── test_scripts/                       # Testing and validation
│   ├── test_environment.py             # Environment validation tests
│   ├── test_configuration.py           # Configuration system tests
│   └── [existing test files]           # Your existing test scripts
├── docs/
│   └── SETUP.md                        # Comprehensive setup guide
├── setup.py                            # Automated project setup
├── Dockerfile                          # Docker development environment
├── docker-compose.yml                  # Full development stack
└── .env                                # Environment variables (from template)
```

## Architecture Overview

The invoice processor follows a multi-tier AI processing approach with enhanced configuration management:

1. **Configuration System**:
   - **Hierarchical loading**: Defaults → File configs → Environment variables
   - **Multi-device support**: Easy setup across different machines
   - **Security-focused**: Sensitive files properly gitignored and protected

2. **Primary Processing - Gemini AI**: 
   - Uses `google-generativeai` library with configurable model (default: Gemini 1.5 Pro)
   - Processes PDFs directly with structured prompt for JSON output
   - Function: `GeminiProcessor.process_document()` in `src/processors/gemini_processor.py`

3. **Fallback Processing - Document AI**:
   - Google Cloud Document AI for OCR and entity extraction
   - Activated when Gemini fails or returns no line items
   - Function: `DocumentAIProcessor.process_document()` in `src/processors/document_ai_processor.py`

4. **Data Flow**:
   ```
   Webhook (Zapier/Trello) → Cloud Function → Config Loader → Gemini AI → Document AI (fallback) → Google Sheets
   ```

5. **Key Components**:
   - `InvoiceProcessor`: Main orchestrator class with multi-tier processing
   - `ConfigLoader`: Hierarchical configuration management
   - `EnvironmentValidator`: Validates setup before processing
   - `process_invoice()`: Cloud Function entry point
   - `write_to_google_sheets()`: Sheets API integration with configuration

## Testing Approach

### 1. **Environment and Configuration Testing** (New)
   ```bash
   # Test environment setup and configuration loading
   python test_scripts/test_environment.py
   python test_scripts/test_configuration.py
   
   # Validate complete environment
   python setup.py --validate
   ```

### 2. **Local Development Testing**:
   ```bash
   # Start local server with new configuration system
   functions-framework --target=process_invoice --debug --source=src/main_updated.py
   
   # Test with curl commands (JSON and form data methods)
   curl -X POST http://localhost:8080 -H "Content-Type: application/json" -d '{"file_url": "https://example.com/invoice.pdf"}'
   ```

### 3. **Component Testing**:
   - `test_gemini.py` for isolated Gemini AI testing
   - `test_invoice.sh` for full workflow testing with real PDFs
   - Docker testing: `docker-compose up --build`

### 4. **Vendor-Specific Testing**:
   - The codebase references test scripts in `test_scripts/` directory:
     - `test_creative_coop.py` - Creative-Coop invoices
     - `perfect_processing.py` - HarperCollins invoices
     - `test_onehundred80.py` - OneHundred80 invoices
   - Each vendor may have unique invoice formats requiring specific handling

### 5. **Pre-commit Hooks**:
   - Pytest runs automatically on commit
   - Black formatting enforced
   - Isort for import organization
   - Conventional commits check

## Configuration Management

The new system supports hierarchical configuration loading:

### Configuration Priority (Highest to Lowest):
1. **Environment Variables** (`.env` file or system environment)
2. **Configuration Files** (`config/*.json`)
3. **Default Values** (built into the system)

### Required Configuration:
- `GOOGLE_CLOUD_PROJECT_ID`: GCP project ID (freckled-hen-analytics)
- `DOCUMENT_AI_PROCESSOR_ID`: Document AI processor ID (be53c6e3a199a473)
- `GOOGLE_CLOUD_LOCATION`: GCP region (us)
- `GOOGLE_SHEETS_SPREADSHEET_ID`: Target spreadsheet ID (1PdnZGPZwAV6AHXEeByhOlaEeGObxYWppwLcq0gdvs0E)
- `GOOGLE_SHEETS_SHEET_NAME`: Target sheet name (Update 20230525)
- `GEMINI_API_KEY`: API key for Gemini AI

### Configuration Files Created by Setup:
- `config/credentials.json`: Service account JSON (from template)
- `config/app_config.json`: Application settings (from template)
- `config/sheets_config.json`: Google Sheets configuration (from template)
- `.env`: Environment variables (from template)

### Configuration Access:
```python
from utils.config_loader import ConfigLoader
config = ConfigLoader()
project_id = config.get('project_id')
debug_mode = config.get('debug_mode', False)
```

## Common Patterns

1. **Date Formatting**: Always convert to MM/DD/YYYY format using `format_date()`
2. **Price Extraction**: Remove currency symbols, handle various formats
3. **Quantity Handling**: Prefer shipped quantity over ordered quantity
4. **Item Description**: Combine SKU, name, and other identifiers with " - " separator
5. **Error Handling**: Multi-tier fallback approach ensures robustness
6. **Smart Google Sheets Integration**: Intelligent row detection prevents overwriting existing data

## Key Features

### Smart Google Sheets Row Detection (Updated - Bug Fixed)
Both `main.py` and `main_updated.py` now include intelligent row detection that:
- **Scans ALL columns A:G** to find the true last row with ANY data (fixes Column A blank issue)
- Prevents overwriting data in partially filled sheets
- Falls back to standard append if detection fails
- Uses `update` method for precise placement instead of always appending

### Key Bug Fixes:
1. **Column A Blank Issue Resolved**: Previously only checked column A for data, which caused overwriting when column A was blank but other columns (B-G) had data. Now checks ALL columns A:G to find the true last row with any data.

2. **10-Row Gap Issue Fixed**: Removed hardcoded buffer that created unnecessary 10-row gaps. New invoices are now placed immediately after the last used row with no gaps.

### Functions:
- `find_next_empty_row()`: Enhanced to check ALL columns A:G for true last row detection
- `write_to_google_sheets()`: Enhanced with smart row detection (main_updated.py)
- Inline smart detection in both Gemini and Document AI processing paths (main.py)

### How It Works:
1. **Full Range Scan**: Gets all values in range A:G instead of just column A
2. **True Last Row Detection**: Iterates through all rows checking if ANY cell has data
3. **Immediate Placement**: Places new data in the row immediately after the last used row (no gaps)
4. **Clean Organization**: Ensures consecutive data placement with no empty rows between invoices

## Progress Notes

### Recently Completed (August 1, 2025):
- ✅ **COMPLETED**: Fixed 10-row gap issue in smart row detection (immediate placement after last used row)
- ✅ **COMPLETED**: Fixed Column A blank issue in smart Google Sheets row detection (now checks ALL columns A:G)
- ✅ **COMPLETED**: Implemented smart Google Sheets row detection fix
- ✅ **COMPLETED**: Enhanced configuration management system for multi-device development
- ✅ **COMPLETED**: Multi-tier invoice processing strategy with Gemini AI integration and Document AI fallback

### Current Status:
The invoice processor is now production-ready with:
- ✅ Complete multi-device configuration system with hierarchical loading
- ✅ Automated setup and validation tools
- ✅ Robust Google Sheets integration with smart row detection (no gaps, no overwrites)
- ✅ Multi-tier AI processing (Gemini first, Document AI fallback)
- ✅ Comprehensive error handling and logging
- ✅ Docker development environment
- ✅ Full test suite and validation scripts

### Ongoing:
- Continuing to refine vendor-specific processing for Creative-Coop, HarperCollins, and OneHundred80 invoices
- Smart row detection with full A:G column checking and immediate placement ensures clean, consecutive data organization

### Next Steps for Production:
1. Test with real invoice workload using the enhanced system
2. Monitor Google Sheets data placement with the fixed smart row detection
3. Validate multi-device configuration sharing across team members