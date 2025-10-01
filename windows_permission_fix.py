#!/usr/bin/env python3
"""
Windows Permission Fix for PDF Converter
Fixes file locking and permission issues on Windows
"""

import os
import time
import logging
import psutil
import platform

logger = logging.getLogger(__name__)

def safe_remove_file(file_path: str, max_retries: int = 5, delay: float = 0.5) -> bool:
    """Safely remove file with retry logic for Windows file locking"""
    if not os.path.exists(file_path):
        return True
    
    for attempt in range(max_retries):
        try:
            os.remove(file_path)
            logger.info(f"Successfully removed {file_path}")
            return True
        except PermissionError as e:
            if attempt < max_retries - 1:
                logger.warning(f"File locked, retrying removal of {file_path} (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
                delay *= 1.5  # Exponential backoff
            else:
                logger.error(f"Failed to remove {file_path} after {max_retries} attempts: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error removing {file_path}: {e}")
            return False
    return False

def safe_write_file(file_path: str, max_retries: int = 3) -> bool:
    """Check if file can be written safely"""
    for attempt in range(max_retries):
        try:
            # Try to open file for writing to check if it's locked
            with open(file_path, 'ab') as f:
                pass
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                logger.warning(f"File locked for writing, waiting... (attempt {attempt + 1}/{max_retries})")
                time.sleep(0.5)
            else:
                logger.error(f"File {file_path} is locked and cannot be written")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking file {file_path}: {e}")
            return False
    return False

def cleanup_libreoffice_processes():
    """Kill hanging LibreOffice processes on Windows"""
    if platform.system() != "Windows":
        return
    
    killed_count = 0
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and 'soffice' in proc.info['name'].lower():
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                    logger.info(f"Terminated LibreOffice process {proc.info['pid']}")
                    killed_count += 1
                except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                    try:
                        proc.kill()
                        logger.info(f"Force killed LibreOffice process {proc.info['pid']}")
                        killed_count += 1
                    except psutil.NoSuchProcess:
                        pass
    except Exception as e:
        logger.error(f"Error cleaning up LibreOffice processes: {e}")
    
    if killed_count > 0:
        logger.info(f"Cleaned up {killed_count} LibreOffice processes")
        time.sleep(1)  # Wait for cleanup

def generate_unique_filename(base_name: str, extension: str = ".docx") -> str:
    """Generate unique filename to avoid conflicts"""
    import uuid
    timestamp = int(time.time())
    unique_id = str(uuid.uuid4())[:8]
    return f"{base_name}_{timestamp}_{unique_id}{extension}"

def ensure_file_permissions(file_path: str) -> bool:
    """Ensure file has proper permissions for deletion"""
    try:
        if os.path.exists(file_path):
            os.chmod(file_path, 0o666)  # Read/write for all
        return True
    except Exception as e:
        logger.error(f"Failed to set permissions for {file_path}: {e}")
        return False

# Patch functions for app.py
def patch_convertdua_cleanup():
    """
    Instructions to patch convertDua endpoint in app.py:
    
    Replace the cleanup section at the end of convert_dua function with:
    
    finally:
        # Enhanced cleanup with retry logic
        cleanup_paths = []
        if 'temp_input' in locals() and temp_input:
            cleanup_paths.append(temp_input)
        if 'temp_output' in locals() and temp_output:
            cleanup_paths.append(temp_output)
        
        # Cleanup LibreOffice processes first
        cleanup_libreoffice_processes()
        
        # Wait a bit for file handles to be released
        time.sleep(0.5)
        
        # Remove files with retry logic
        for path in cleanup_paths:
            if path and os.path.exists(path):
                ensure_file_permissions(path)
                safe_remove_file(path)
    """
    pass

if __name__ == "__main__":
    print("🔧 Windows Permission Fix Utility")
    print("=" * 40)
    print()
    print("This utility provides functions to fix Windows permission issues:")
    print("1. safe_remove_file() - Retry logic for locked files")
    print("2. cleanup_libreoffice_processes() - Kill hanging processes")
    print("3. safe_write_file() - Check file write permissions")
    print("4. ensure_file_permissions() - Set proper file permissions")
    print()
    print("To apply fixes:")
    print("1. Import these functions in app.py")
    print("2. Replace file operations with safe_* versions")
    print("3. Add cleanup_libreoffice_processes() before conversions")
    print("4. Use ensure_file_permissions() before deletions")
    print()
    
    # Test cleanup
    print("🧹 Testing LibreOffice process cleanup...")
    cleanup_libreoffice_processes()
    print("✅ Cleanup test completed")
