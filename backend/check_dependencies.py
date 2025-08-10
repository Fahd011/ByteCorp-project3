#!/usr/bin/env python3
"""
Check if all required dependencies are properly installed
"""

import sys
import importlib

def check_dependency(module_name, package_name=None):
    """Check if a dependency is installed"""
    if package_name is None:
        package_name = module_name
    
    try:
        importlib.import_module(module_name)
        print(f"[OK] {package_name} is installed")
        return True
    except ImportError as e:
        print(f"[ERROR] {package_name} is NOT installed: {e}")
        return False

def main():
    """Check all required dependencies"""
    print("=== CHECKING DEPENDENCIES ===")
    
    dependencies = [
        ("browser_use", "browser-use"),
        ("openai", "openai"),
        ("playwright", "playwright"),
        ("pandas", "pandas"),
        ("supabase", "supabase"),
        ("flask", "flask"),
        ("flask_cors", "flask-cors"),
        ("flask_jwt_extended", "flask-jwt-extended"),
        ("sqlalchemy", "sqlalchemy"),
        ("psycopg2", "psycopg2-binary"),
        ("dotenv", "python-dotenv"),
        ("requests", "requests"),
        ("flask_sqlalchemy", "flask-sqlalchemy"),
    ]
    
    all_installed = True
    for module_name, package_name in dependencies:
        if not check_dependency(module_name, package_name):
            all_installed = False
    
    print("\n=== SUMMARY ===")
    if all_installed:
        print("[OK] All dependencies are installed!")
        return True
    else:
        print("[ERROR] Some dependencies are missing!")
        print("\nTo install missing dependencies, run:")
        print("pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
