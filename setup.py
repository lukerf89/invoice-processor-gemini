#!/usr/bin/env python3
"""
Automated setup script for invoice processing project.
Creates configuration files from templates and validates environment.
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List

class ProjectSetup:
    """Handles project setup and configuration"""

    def __init__(self):
        self.project_root = Path.cwd()
        self.config_dir = self.project_root / "config"
        self.template_files = {
            'config/credentials.template.json': 'config/credentials.json',
            'config/app_config.template.json': 'config/app_config.json',
            'config/sheets_config.template.json': 'config/sheets_config.json',
            '.env.template': '.env'
        }

    def run_setup(self):
        """Run complete setup process"""
        print("🚀 Starting Invoice Processor Setup")
        print("=" * 50)

        try:
            self._create_directories()
            self._copy_template_files()
            self._setup_gitignore()
            self._check_dependencies()
            self._print_next_steps()

            print("\n✅ Setup completed successfully!")
            return True

        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            return False

    def _create_directories(self):
        """Create necessary directories"""
        print("\n📁 Creating directory structure...")

        directories = [
            'config',
            'src/processors/vendor_processors',
            'src/utils',
            'test_scripts',
            'docs',
            'test_invoices',
            'debug_output'
        ]

        for directory in directories:
            dir_path = self.project_root / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created: {directory}")

    def _copy_template_files(self):
        """Copy template files to actual configuration files"""
        print("\n📄 Setting up configuration files...")

        for template_path, target_path in self.template_files.items():
            template_file = self.project_root / template_path
            target_file = self.project_root / target_path

            if not template_file.exists():
                print(f"⚠️  Template not found: {template_path}")
                continue

            if target_file.exists():
                response = input(f"File {target_path} already exists. Overwrite? (y/N): ")
                if response.lower() != 'y':
                    print(f"⏭️  Skipped: {target_path}")
                    continue

            shutil.copy2(template_file, target_file)
            print(f"✅ Created: {target_path} (from template)")

            # Set appropriate permissions for sensitive files
            if 'credentials' in str(target_file) or target_file.name == '.env':
                os.chmod(target_file, 0o600)  # Read/write for owner only

    def _setup_gitignore(self):
        """Create or update .gitignore file"""
        print("\n🚫 Setting up .gitignore...")

        gitignore_content = """# Sensitive configuration files
config/credentials.json
config/app_config.json
config/sheets_config.json
.env
*.key
*.pem

# Development files
.vscode/settings.json
.idea/workspace.xml
*.log
debug_output/
temp_files/

# Python
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage
htmlcov/
.tox/
venv/
env/
.venv/

# OS files
.DS_Store
Thumbs.db
*.swp
*.swo

# Project-specific
test_invoices/processed/
output_debug/

# Keep templates
!config/*.template.*
!.env.template

# IDE files
.vscode/
.idea/
*.sublime-project
*.sublime-workspace

# Logs and databases
*.log
*.sqlite
*.db
"""

        gitignore_path = self.project_root / '.gitignore'

        if gitignore_path.exists():
            # Read existing content to avoid duplicates
            with open(gitignore_path, 'r') as f:
                existing_content = f.read()

            # Only add if not already present
            if 'config/credentials.json' not in existing_content:
                with open(gitignore_path, 'a') as f:
                    f.write('\n\n# Added by setup.py\n')
                    f.write(gitignore_content)
                print("✅ Updated .gitignore")
            else:
                print("ℹ️  .gitignore already configured")
        else:
            with open(gitignore_path, 'w') as f:
                f.write(gitignore_content)
            print("✅ Created .gitignore")

    def _check_dependencies(self):
        """Check if required Python packages are installed"""
        print("\n🐍 Checking Python dependencies...")

        required_packages = [
            'google-cloud-documentai',
            'google-generativeai',
            'google-auth',
            'google-api-python-client',
            'functions-framework',
            'requests',
            'flask'
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
            print(f"\n⚠️  Missing packages detected.")
            print(f"Install with: pip install {' '.join(missing_packages)}")

            if self._requirements_files_exist():
                print("Or install from requirements: pip install -r requirements.txt")

    def _requirements_files_exist(self) -> bool:
        """Check if requirements files exist"""
        return (self.project_root / 'requirements.txt').exists()

    def _print_next_steps(self):
        """Print next steps for user"""
        print("\n" + "="*50)
        print("📋 NEXT STEPS")
        print("="*50)

        print("\n1. Configure your API keys and credentials:")
        for template_path, target_path in self.template_files.items():
            target_file = self.project_root / target_path
            if target_file.exists():
                print(f"   - Edit: {target_path}")

        print("\n2. Required information you'll need:")
        print("   - Google Cloud Project ID")
        print("   - Document AI Processor ID")
        print("   - Google Sheets ID")
        print("   - Gemini API Key")
        print("   - Service Account JSON credentials")

        print("\n3. Install dependencies (if not already done):")
        print("   pip install -r requirements.txt")

        print("\n4. Validate your setup:")
        print("   python -c \"from src.utils.validation import validate_environment; validate_environment()\"")

        print("\n5. Test the setup:")
        print("   python test_scripts/test_environment.py")

        print("\n📚 Documentation:")
        print("   - Setup guide: docs/SETUP.md")
        print("   - Development workflow: README.md")

def main():
    """Main setup function"""
    setup = ProjectSetup()

    if len(sys.argv) > 1 and sys.argv[1] == '--validate':
        # Just run validation
        try:
            from src.utils.config_loader import ConfigLoader
            from src.utils.validation import validate_environment

            config = ConfigLoader()
            validate_environment(config)
        except ImportError as e:
            print(f"❌ Cannot import validation modules: {e}")
            print("Make sure you've run the basic setup first: python setup.py")
        return

    success = setup.run_setup()

    if success:
        print(f"\n🎉 Setup complete! Run 'python setup.py --validate' to test your configuration.")
    else:
        print(f"\n💥 Setup encountered errors. Please check the messages above.")
        sys.exit(1)

if __name__ == '__main__':
    main()