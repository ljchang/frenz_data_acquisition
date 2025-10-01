#!/usr/bin/env python3
"""
Quick Start Script for FRENZ Data Collection System
Run this to verify all modules are working correctly
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_imports():
    """Verify all required modules can be imported"""
    modules_to_check = [
        ('device_manager', 'DeviceManager'),
        ('data_storage', 'DataStorage'),
        ('event_logger', 'EventLogger'),
        ('frenz_collector', 'FrenzCollector'),
        ('config', 'config'),
    ]

    print("🔍 Checking module imports...")
    all_good = True

    for module_name, class_name in modules_to_check:
        try:
            module = __import__(module_name)
            if hasattr(module, class_name):
                print(f"✅ {module_name}.{class_name} imported successfully")
            else:
                print(f"⚠️  {module_name} imported but {class_name} not found")
                all_good = False
        except ImportError as e:
            print(f"❌ Failed to import {module_name}: {e}")
            all_good = False

    return all_good

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\n🔍 Checking environment configuration...")

    env_path = Path('.env')
    if not env_path.exists():
        print("⚠️  .env file not found. Creating template...")
        with open('.env', 'w') as f:
            f.write("# FRENZ Device Credentials\n")
            f.write("FRENZ_ID=your_device_id_here\n")
            f.write("FRENZ_KEY=your_product_key_here\n")
        print("📝 Created .env template. Please update with your credentials.")
        return False

    # Check for required variables
    from dotenv import dotenv_values
    env_vars = dotenv_values('.env')

    required = ['FRENZ_ID', 'FRENZ_KEY']
    missing = []

    for var in required:
        if var not in env_vars or env_vars[var] in ['', 'your_device_id_here', 'your_product_key_here']:
            missing.append(var)

    if missing:
        print(f"⚠️  Missing or placeholder values for: {', '.join(missing)}")
        print("📝 Please update .env file with actual credentials")
        return False

    print("✅ Environment variables configured")
    return True

def check_directories():
    """Ensure required directories exist"""
    print("\n🔍 Checking directory structure...")

    required_dirs = ['data', 'logs']
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created {dir_name}/ directory")
        else:
            print(f"✅ {dir_name}/ directory exists")

    return True

def test_basic_functionality():
    """Test basic functionality of core modules"""
    print("\n🧪 Testing basic functionality...")

    try:
        # Test config
        from config import config as cfg
        print("✅ Configuration loaded successfully")

        # Test device manager initialization
        from device_manager import DeviceManager
        dm = DeviceManager()
        print("✅ DeviceManager initialized")

        # Test data storage initialization
        from data_storage import DataStorage
        print("✅ DataStorage module ready")

        # Test event logger
        from event_logger import EventLogger
        logger = EventLogger()
        print("✅ EventLogger initialized")

        # Test collector initialization
        from frenz_collector import FrenzCollector
        collector = FrenzCollector()
        print("✅ FrenzCollector initialized")

        return True
    except Exception as e:
        print(f"❌ Error during functionality test: {e}")
        return False

def main():
    """Main quick start verification"""
    print("=" * 60)
    print("🧠 FRENZ Data Collection System - Quick Start")
    print("=" * 60)

    # Run checks
    imports_ok = check_imports()
    env_ok = check_env_file()
    dirs_ok = check_directories()

    if imports_ok and dirs_ok:
        functional_ok = test_basic_functionality()
    else:
        functional_ok = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 System Check Summary:")
    print("=" * 60)

    all_ready = imports_ok and env_ok and dirs_ok and functional_ok

    if all_ready:
        print("✅ System is ready to use!")
        print("\n🚀 To start the dashboard, run:")
        print("   marimo run dashboard.py")
        print("\n📚 For programmatic usage, see README.md")
    else:
        print("⚠️  Some issues need to be resolved:")
        if not imports_ok:
            print("   - Fix import errors")
        if not env_ok:
            print("   - Update .env file with credentials")
        if not functional_ok:
            print("   - Check error messages above")
        print("\n📚 See README.md for detailed setup instructions")

    return 0 if all_ready else 1

if __name__ == "__main__":
    sys.exit(main())