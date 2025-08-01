# Invoice Processor Setup Guide

This guide will help you set up the invoice processing project on any development machine.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd invoice-processor-gemini
   ```

2. **Run automated setup**
   ```bash
   python setup.py
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements.dev.txt  # For development
   ```

4. **Configure your environment** (see Configuration section below)

5. **Validate setup**
   ```bash
   python setup.py --validate
   ```

6. **Test the setup**
   ```bash
   python test_scripts/test_environment.py
   ```

## Configuration

After running `python setup.py`, you'll need to configure these files:

### 1. Service Account Credentials (`config/credentials.json`)

Get this from Google Cloud Console:
- Go to IAM & Admin → Service Accounts
- Create or select your service account
- Click "Keys" → "Add Key" → "Create New Key" → JSON
- Download and replace the template content

### 2. Environment Variables (`.env`)

```
# Required
GOOGLE_CLOUD_PROJECT_ID=freckled-hen-analytics
DOCUMENT_AI_PROCESSOR_ID=be53c6e3a199a473
GOOGLE_CLOUD_LOCATION=us
GOOGLE_SHEETS_SPREADSHEET_ID=1PdnZGPZwAV6AHXEeByhOlaEeGObxYWppwLcq0gdvs0E
GOOGLE_SHEETS_SHEET_NAME=Update 20230525
GEMINI_API_KEY=your-gemini-api-key

# Optional
USE_GEMINI_FIRST=true
DEBUG_MODE=false
ENVIRONMENT=development
```

### 3. Application Configuration (`config/app_config.json`)

Customize processing behavior:
```json
{
  "gemini_model": "gemini-1.5-pro",
  "max_retries": 3,
  "timeout": 30,
  "use_gemini_first": true,
  "debug_mode": false
}
```

## Development Workflow

### Local Development Server

```bash
# Using functions-framework
functions-framework --target=process_invoice --debug

# Or run the main file directly
cd src
python main.py
```

### Testing

```bash
# Test environment setup
python test_scripts/test_environment.py

# Test configuration loading
python test_scripts/test_configuration.py

# Test invoice processing with existing test scripts
python test_scripts/test_invoice.py
python test_scripts/test_gemini.py

# Test with specific invoice
./test_invoice.sh InvoiceName
```

### Debugging

```bash
# Debug Document AI responses
python src/utils/document_ai_explorer.py invoice.pdf --save-json

# Test Gemini processing
python test_scripts/test_gemini.py
```

## Docker Development (Optional)

```bash
# Build and run with Docker
docker-compose up --build

# Test with Docker
curl -X POST http://localhost:8080 \
  -F "file_url=https://example.com/invoice.pdf"
```

## Deployment

### Google Cloud Functions

```bash
# Deploy using the existing deploy.sh script
./deploy.sh

# Or manually with gcloud
gcloud functions deploy process-invoice-gemini \
  --gen2 \
  --runtime python312 \
  --trigger-http \
  --allow-unauthenticated \
  --memory=1GiB \
  --timeout=540s \
  --region=us-central1 \
  --entry-point=process_invoice \
  --source=src \
  --set-env-vars GOOGLE_CLOUD_PROJECT_ID=freckled-hen-analytics,DOCUMENT_AI_PROCESSOR_ID=be53c6e3a199a473,GOOGLE_CLOUD_LOCATION=us,GOOGLE_SHEETS_SPREADSHEET_ID=1PdnZGPZwAV6AHXEeByhOlaEeGObxYWppwLcq0gdvs0E,GOOGLE_SHEETS_SHEET_NAME="Update 20230525" \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

### Environment Variables for Production

Set these in your deployment environment:
- `GOOGLE_CLOUD_PROJECT_ID`
- `DOCUMENT_AI_PROCESSOR_ID`
- `GOOGLE_CLOUD_LOCATION`
- `GOOGLE_SHEETS_SPREADSHEET_ID`
- `GOOGLE_SHEETS_SHEET_NAME`
- `GEMINI_API_KEY`
- `ENVIRONMENT=production`

## Troubleshooting

### Common Issues

1. **"Missing required configuration"**
   - Run `python setup.py` to create template files
   - Fill in all required values in the created files

2. **"Service account credentials file not found"**
   - Ensure `config/credentials.json` exists and is valid
   - Check file permissions (should be 600 for security)

3. **"Document AI connection failed"**
   - Verify processor ID and location are correct
   - Ensure Document AI API is enabled in Google Cloud
   - Check service account has Document AI API User role

4. **"Gemini AI setup failed"**
   - Verify Gemini API key is correct
   - Check if you have access to the Gemini API

5. **"Google Sheets access failed"**
   - Verify sheets ID is correct
   - Ensure service account has edit access to the sheet
   - Check that Google Sheets API is enabled

### Getting Help

1. Check the logs - enable debug mode in `.env`
2. Run validation: `python setup.py --validate`
3. Check individual components with test scripts
4. Review the configuration summary in debug mode

## File Structure

```
invoice-processor-gemini/
├── src/
│   ├── main.py                      # Main Cloud Function
│   ├── main_updated.py              # Updated main with new config system
│   ├── processors/                  # Processing engines
│   │   ├── gemini_processor.py
│   │   └── document_ai_processor.py
│   └── utils/                       # Configuration and validation
│       ├── config_loader.py
│       ├── validation.py
│       └── document_ai_explorer.py
├── config/                          # Configuration files (gitignored)
│   ├── *.template.json             # Template files
│   ├── credentials.json            # Service account (create from template)
│   └── app_config.json             # App config (create from template)
├── test_scripts/                    # Testing and validation
├── docs/                           # Documentation
├── requirements.txt                # Dependencies
├── setup.py                       # Automated setup
└── deploy.sh                      # Deployment script
```

## Security Notes

- Configuration files with sensitive data are gitignored
- Service account credentials have restricted permissions (600)
- Never commit actual API keys or credentials
- Use environment variables for production deployments
- Regularly rotate API keys and service account keys

## Migrating from Old Structure

If you have an existing setup:

1. Your existing `main.py` is preserved in `src/main.py`
2. The new `src/main_updated.py` integrates the configuration system
3. To use the new system, replace `src/main.py` with `src/main_updated.py`
4. All existing functionality is preserved
5. Configuration now supports multiple environments easily