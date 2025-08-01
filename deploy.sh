#!/bin/bash

# Deploy the enhanced Cloud Function with Gemini support
gcloud functions deploy process-invoice-gemini \
  --gen2 \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --memory=1GiB \
  --timeout=540s \
  --region=us-central1 \
  --entry-point=process_invoice \
  --set-env-vars GOOGLE_CLOUD_PROJECT_ID=freckled-hen-analytics,DOCUMENT_AI_PROCESSOR_ID=be53c6e3a199a473,GOOGLE_CLOUD_LOCATION=us,GOOGLE_SHEETS_SPREADSHEET_ID=1PdnZGPZwAV6AHXEeByhOlaEeGObxYWppwLcq0gdvs0E,GOOGLE_SHEETS_SHEET_NAME="Update 20230525",GEMINI_API_KEY=AIzaSyBuT4OLwbmjuZriu7Nh9rkTO2LKaSebFO4

echo "🚀 Deployed process-invoice-gemini function"
echo "✅ Gemini AI integration active"