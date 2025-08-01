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

## Development Commands

```bash
# Setup virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (includes testing and linting tools)
pip install -r requirements.dev.txt

# Local development server
functions-framework --target=process_invoice --debug

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
```

[... rest of the existing content remains the same ...]

## Progress Notes

- Left off working on multi-tier invoice processing strategy, focusing on improving Gemini AI integration and fallback mechanisms
- Continuing to refine vendor-specific processing for Creative-Coop, HarperCollins, and OneHundred80 invoices
- Next steps involve enhancing error handling and improving extraction accuracy across different invoice formats