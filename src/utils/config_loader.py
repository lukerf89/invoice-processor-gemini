import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigLoader:
    """Hierarchical configuration loader supporting multiple sources"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config = {}
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration from multiple sources in priority order"""
        # 1. Default values (always available)
        self.config.update(self._get_defaults())

        # 2. Configuration files (if present)
        self.config.update(self._load_file_config())

        # 3. Environment variables (highest priority)
        self.config.update(self._load_env_config())

        # 4. Validate required configuration
        self._validate_config()

    def _get_defaults(self) -> Dict[str, Any]:
        """Default configuration values"""
        return {
            'project_id': '',
            'processor_location': 'us',
            'processor_id': '',
            'sheets_id': '',
            'sheet_name': 'Update 20230525',
            'max_retries': 3,
            'timeout': 30,
            'gemini_model': 'gemini-1.5-pro',
            'use_gemini_first': True,
            'debug_mode': False
        }

    def _load_file_config(self) -> Dict[str, Any]:
        """Load configuration from JSON files"""
        configs = {}
        config_files = [
            self.config_dir / 'app_config.json',
            self.config_dir / 'sheets_config.json'
        ]

        for file_path in config_files:
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        file_config = json.load(f)
                        configs.update(file_config)
                        print(f"✅ Loaded configuration from {file_path}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not load {file_path}: {e}")

        return configs

    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_mapping = {
            'GOOGLE_CLOUD_PROJECT_ID': 'project_id',
            'DOCUMENT_AI_PROCESSOR_ID': 'processor_id',
            'GOOGLE_CLOUD_LOCATION': 'processor_location',
            'GOOGLE_SHEETS_SPREADSHEET_ID': 'sheets_id',
            'GOOGLE_SHEETS_SHEET_NAME': 'sheet_name',
            'GEMINI_API_KEY': 'gemini_api_key',
            'DEBUG_MODE': 'debug_mode',
            'USE_GEMINI_FIRST': 'use_gemini_first'
        }

        env_config = {}
        for env_key, config_key in env_mapping.items():
            value = os.getenv(env_key)
            if value:
                # Convert boolean strings
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                env_config[config_key] = value

        return env_config

    def _validate_config(self):
        """Validate that required configuration is present"""
        required_keys = ['project_id', 'processor_id', 'sheets_id']
        missing = [key for key in required_keys if not self.config.get(key)]

        if missing:
            print(f"❌ Missing required configuration: {missing}")
            print("Run 'python setup.py' to create template files and configure them")
            # Don't raise exception in development - allow partial setup
            if os.getenv('ENVIRONMENT') == 'production':
                raise ValueError(f"Missing required configuration: {missing}")

    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    def get_credentials_path(self) -> Optional[str]:
        """Get path to service account credentials file"""
        creds_path = self.config_dir / 'credentials.json'
        if creds_path.exists():
            return str(creds_path)

        # Fallback to environment variable
        return os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    def print_config_summary(self):
        """Print configuration summary for debugging"""
        print("\n📋 Configuration Summary:")
        print("-" * 40)
        sensitive_keys = ['gemini_api_key', 'credentials']

        for key, value in self.config.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                display_value = "[CONFIGURED]" if value else "[NOT SET]"
            else:
                display_value = value
            print(f"{key}: {display_value}")
        print("-" * 40)