import os
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
from google.oauth2 import service_account
from google.cloud import documentai
import google.generativeai as genai

class EnvironmentValidator:
    """Validates development environment setup"""

    def __init__(self, config_loader):
        self.config = config_loader
        self.validation_results = []

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print("🔍 Validating environment setup...")

        checks = [
            self._check_configuration_files,
            self._check_service_account_credentials,
            self._check_document_ai_connection,
            self._check_gemini_ai_setup,
            self._check_sheets_access,
            self._check_python_dependencies
        ]

        all_passed = True
        for check in checks:
            try:
                result = check()
                self.validation_results.append(result)
                if not result:
                    all_passed = False
            except Exception as e:
                print(f"❌ Validation error: {e}")
                self.validation_results.append(False)
                all_passed = False

        self._print_validation_summary()
        return all_passed

    def _check_configuration_files(self) -> bool:
        """Check that required configuration files exist"""
        print("\n📁 Checking configuration files...")

        required_files = [
            'config/credentials.json',
            '.env'
        ]

        optional_files = [
            'config/app_config.json',
            'config/sheets_config.json'
        ]

        missing_required = []
        for file_path in required_files:
            if not Path(file_path).exists():
                missing_required.append(file_path)
                print(f"❌ Missing required file: {file_path}")
            else:
                print(f"✅ Found: {file_path}")

        for file_path in optional_files:
            if Path(file_path).exists():
                print(f"✅ Found optional: {file_path}")
            else:
                print(f"ℹ️  Optional file not found: {file_path}")

        if missing_required:
            print(f"⚠️  Run 'python setup.py' to create missing files from templates")
            return False

        return True

    def _check_service_account_credentials(self) -> bool:
        """Validate service account credentials"""
        print("\n🔑 Checking service account credentials...")

        creds_path = self.config.get_credentials_path()
        if not creds_path or not Path(creds_path).exists():
            print("❌ Service account credentials file not found")
            return False

        try:
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            project_id = credentials.project_id
            print(f"✅ Valid credentials for project: {project_id}")

            # Check if project_id matches configuration
            config_project = self.config.get('project_id')
            if config_project and config_project != project_id:
                print(f"⚠️  Project ID mismatch: config={config_project}, credentials={project_id}")

            return True
        except Exception as e:
            print(f"❌ Invalid service account credentials: {e}")
            return False

    def _check_document_ai_connection(self) -> bool:
        """Test Document AI connection"""
        print("\n🤖 Checking Document AI connection...")

        try:
            project_id = self.config.get('project_id')
            processor_id = self.config.get('processor_id')
            location = self.config.get('processor_location')

            if not all([project_id, processor_id, location]):
                print("❌ Missing Document AI configuration")
                return False

            # Set credentials if available
            creds_path = self.config.get_credentials_path()
            if creds_path:
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path

            client = documentai.DocumentProcessorServiceClient()
            processor_name = client.processor_path(project_id, location, processor_id)

            # Try to get processor info
            processor = client.get_processor(name=processor_name)
            print(f"✅ Document AI processor found: {processor.display_name}")
            return True

        except Exception as e:
            print(f"❌ Document AI connection failed: {e}")
            return False

    def _check_gemini_ai_setup(self) -> bool:
        """Check Gemini AI setup"""
        print("\n✨ Checking Gemini AI setup...")

        api_key = self.config.get('gemini_api_key')
        if not api_key:
            print("❌ Gemini API key not configured")
            return False

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(self.config.get('gemini_model'))
            print(f"✅ Gemini AI configured with model: {self.config.get('gemini_model')}")
            return True
        except Exception as e:
            print(f"❌ Gemini AI setup failed: {e}")
            return False

    def _check_sheets_access(self) -> bool:
        """Check Google Sheets access"""
        print("\n📊 Checking Google Sheets access...")

        sheets_id = self.config.get('sheets_id')
        if not sheets_id:
            print("❌ Google Sheets ID not configured")
            return False

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds_path = self.config.get_credentials_path()
            if not creds_path:
                print("❌ Service account credentials not found for Sheets access")
                return False

            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )

            service = build('sheets', 'v4', credentials=credentials)

            # Try to get spreadsheet metadata
            sheet = service.spreadsheets().get(spreadsheetId=sheets_id).execute()
            print(f"✅ Google Sheets access confirmed: {sheet.get('properties', {}).get('title', 'Unknown')}")
            return True

        except Exception as e:
            print(f"❌ Google Sheets access failed: {e}")
            return False

    def _check_python_dependencies(self) -> bool:
        """Check Python dependencies"""
        print("\n🐍 Checking Python dependencies...")

        required_packages = [
            'google-cloud-documentai',
            'google-generativeai',
            'google-auth',
            'google-api-python-client',
            'functions-framework',
            'requests'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                print(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"❌ Missing: {package}")

        if missing_packages:
            print(f"⚠️  Install missing packages: pip install {' '.join(missing_packages)}")
            return False

        return True

    def _print_validation_summary(self):
        """Print validation summary"""
        print("\n" + "="*50)
        print("🏁 VALIDATION SUMMARY")
        print("="*50)

        if all(self.validation_results):
            print("✅ All validations passed! Environment is ready.")
        else:
            print("❌ Some validations failed. Check the issues above.")
            print("\n💡 Quick fixes:")
            print("1. Run 'python setup.py' to create template files")
            print("2. Configure the created files with your actual values")
            print("3. Install missing dependencies: pip install -r requirements.txt")

def validate_environment(config_loader=None) -> bool:
    """Main validation function"""
    if not config_loader:
        from .config_loader import ConfigLoader
        config_loader = ConfigLoader()

    validator = EnvironmentValidator(config_loader)
    return validator.validate_all()