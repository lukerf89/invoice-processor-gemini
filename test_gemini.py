#!/usr/bin/env python3

import os
import sys
from main import process_with_gemini_first

def test_gemini_processing():
    """Test Gemini processing with a sample PDF"""
    
    # Set environment variable for testing
    os.environ['GEMINI_API_KEY'] = 'your-api-key-here'  # Replace with actual key
    
    # Test with a sample PDF file
    pdf_path = 'test_invoices/sample_invoice.pdf'  # Update path as needed
    
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return
    
    with open(pdf_path, 'rb') as f:
        pdf_content = f.read()
    
    print(f"📄 Testing Gemini processing with {pdf_path}")
    result = process_with_gemini_first(pdf_content)
    
    if result:
        rows, vendor, invoice_number, invoice_date = result
        print(f"✅ Success: {len(rows)} items extracted")
        print(f"📊 Vendor: {vendor}, Invoice: {invoice_number}, Date: {invoice_date}")
        for i, row in enumerate(rows, 1):
            print(f"  {i}. {row[4]} | {row[5]} | Qty: {row[6]}")
    else:
        print("❌ Gemini processing failed")

if __name__ == "__main__":
    test_gemini_processing()