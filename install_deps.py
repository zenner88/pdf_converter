#!/usr/bin/env python3
"""
Dependency installer for PDF Converter
Automatically installs required packages for testing and running the service
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True
        else:
            print(f"❌ {description} failed:")
            print(f"   Error: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out")
        return False
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print(f"❌ Python 3.7+ required, found {version.major}.{version.minor}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def check_pip():
    """Check if pip is available"""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        print("✅ pip is available")
        return True
    except:
        print("❌ pip not found")
        return False

def install_requirements():
    """Install requirements from requirements.txt"""
    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt not found")
        return False
    
    cmd = f"{sys.executable} -m pip install -r requirements.txt"
    return run_command(cmd, "Installing requirements from requirements.txt")

def install_basic_deps():
    """Install basic dependencies manually"""
    packages = [
        "requests>=2.25.0",
        "python-docx>=0.8.11",
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "psutil>=5.8.0"
    ]
    
    for package in packages:
        cmd = f"{sys.executable} -m pip install '{package}'"
        if not run_command(cmd, f"Installing {package}"):
            return False
    return True

def check_installation():
    """Verify that key packages are installed"""
    packages_to_check = [
        ('requests', 'HTTP client for testing'),
        ('docx', 'python-docx for DOCX creation'),
        ('fastapi', 'FastAPI web framework'),
        ('uvicorn', 'ASGI server'),
        ('psutil', 'System monitoring')
    ]
    
    print("\n🔍 Verifying installation...")
    all_good = True
    
    for package, description in packages_to_check:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"❌ {package} - {description} (NOT FOUND)")
            all_good = False
    
    return all_good

def main():
    """Main installation process"""
    print("🚀 PDF Converter Dependency Installer")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Please upgrade Python to 3.7 or higher")
        return 1
    
    # Check pip
    if not check_pip():
        print("\n❌ Please install pip")
        return 1
    
    print("\n📦 Installing dependencies...")
    
    # Try to install from requirements.txt first
    success = install_requirements()
    
    # If that fails, try manual installation
    if not success:
        print("\n⚠️  requirements.txt installation failed, trying manual installation...")
        success = install_basic_deps()
    
    if not success:
        print("\n❌ Installation failed")
        return 1
    
    # Verify installation
    if check_installation():
        print("\n🎉 All dependencies installed successfully!")
        print("\n📋 You can now run:")
        print("   python app.py                    # Start the service")
        print("   python test_integration.py       # Run integration tests")
        print("   python test_workers.py           # Run performance tests")
        print("   ./test_multiple_workers.sh       # Run comprehensive tests")
        return 0
    else:
        print("\n❌ Some packages are still missing")
        print("\n🔧 Try manual installation:")
        print("   pip install requests python-docx fastapi uvicorn psutil")
        return 1

if __name__ == "__main__":
    exit(main())
