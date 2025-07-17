#!/usr/bin/env python3
"""Simple test script to verify the application can start."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from finisher import ApplicationController
    print("✓ Successfully imported ApplicationController")
    
    from finisher.api import Auto1111Client
    print("✓ Successfully imported Auto1111Client")
    
    from finisher.core import ImageProcessor
    print("✓ Successfully imported ImageProcessor")
    
    from finisher.gui import MainWindow
    print("✓ Successfully imported MainWindow")
    
    from finisher.config import ApplicationSettings
    print("✓ Successfully imported ApplicationSettings")
    
    # Test basic initialization (without GUI)
    settings = ApplicationSettings()
    print("✓ Successfully created ApplicationSettings")
    
    client = Auto1111Client("http://test.local:7860")
    print("✓ Successfully created Auto1111Client")
    
    processor = ImageProcessor()
    print("✓ Successfully created ImageProcessor")
    
    print("\n🎉 All core components imported and initialized successfully!")
    print("\nTo run the full application, use:")
    print("  python -m finisher.main")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
