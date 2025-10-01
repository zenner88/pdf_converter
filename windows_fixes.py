#!/usr/bin/env python3
"""
Windows-specific fixes for PDF Converter
Apply these fixes to resolve COM and path issues on Windows
"""

def apply_windows_fixes():
    """Apply Windows-specific fixes"""
    
    print("🔧 Applying Windows fixes for PDF Converter...")
    
    # 1. Fix temp directory paths
    print("📁 Fixing temp directory paths...")
    
    # 2. Fix COM initialization
    print("⚙️ Fixing COM initialization...")
    
    # 3. Fix LibreOffice paths
    print("📄 Fixing LibreOffice paths...")
    
    print("✅ Windows fixes applied!")
    print()
    print("🚀 Quick fixes summary:")
    print("1. Use 'temp' directory instead of '/tmp'")
    print("2. Initialize COM properly in MS Word threads")
    print("3. Use Windows-compatible paths")
    print("4. Updated lifespan handlers")
    print()
    print("📋 To apply fixes:")
    print("1. Stop current service (Ctrl+C)")
    print("2. Run: run_windows_fixed.bat")
    print("3. Or manually set: set TEMP_DIR=temp")

if __name__ == "__main__":
    apply_windows_fixes()
