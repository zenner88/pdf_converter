import os
import tempfile
import subprocess
import asyncio
import shutil
import uuid
import platform
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

import psutil
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import aiofiles
import httpx
# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    # python-dotenv not installed, use environment variables only
    pass

# Configuration from environment variables or .env file
SERVICE_HOST = os.getenv('SERVICE_HOST', '0.0.0.0')
SERVICE_PORT = int(os.getenv('SERVICE_PORT', '8000'))
CONVERSION_TIMEOUT = int(os.getenv('CONVERSION_TIMEOUT', '45'))  # Reduced for high volume
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))  # Configurable via environment
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', str(50 * 1024 * 1024)))  # 50MB default

# Windows-compatible temp directory
default_temp = tempfile.gettempdir()
if platform.system() == 'Windows':
    # Use relative temp directory on Windows to avoid path issues
    default_temp = 'temp'
TEMP_DIR = os.getenv('TEMP_DIR', default_temp)

LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '600'))  # 10 minutes
MAX_FILE_AGE = int(os.getenv('MAX_FILE_AGE', '3600'))  # 1 hour

# Create directories if they don't exist
Path(LOG_DIR).mkdir(exist_ok=True)
Path(TEMP_DIR).mkdir(exist_ok=True)

# High-volume deployment recommendations:
# Target: 20-60 conversions/minute
# - For 20/min: 8-12 workers (avg 25s per conversion)
# - For 40/min: 15-20 workers (avg 20s per conversion) 
# - For 60/min: 25-30 workers (avg 15s per conversion)
# 
# System requirements for high volume:
# - CPU: 16+ cores (2 cores per 3-4 workers)
# - RAM: 32+ GB (1-2GB per worker)
# - SSD storage for temp files
# - LibreOffice limit: Max 15-20 concurrent instances
# - Consider multiple service instances with load balancer

# Setup logging with configurable level
log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'pdf_converter.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log configuration on startup
logger.info(f"PDF Converter starting with configuration:")
logger.info(f"  Service: {SERVICE_HOST}:{SERVICE_PORT}")
logger.info(f"  Workers: {MAX_WORKERS}, Timeout: {CONVERSION_TIMEOUT}s")
logger.info(f"  Max file size: {MAX_FILE_SIZE / (1024*1024):.1f}MB")
logger.info(f"  Temp dir: {TEMP_DIR}")
logger.info(f"  Log dir: {LOG_DIR}")

app = FastAPI(title="Simple PDF Converter", version="1.0.0")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

# Thread pool for conversion tasks
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Global conversion status tracking
conversion_status: Dict[str, Dict[str, Any]] = {}
conversion_semaphore: Optional[asyncio.Semaphore] = None
http_client: Optional[httpx.AsyncClient] = None

# Windows-safe file operations
def safe_remove_file(file_path: str, max_retries: int = 3) -> bool:
    """Safely remove file with retry logic for Windows file locking"""
    if not os.path.exists(file_path):
        return True
    
    for attempt in range(max_retries):
        try:
            # Set file permissions before removal
            os.chmod(file_path, 0o666)
            os.remove(file_path)
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                logger.warning(f"File locked, retrying removal of {file_path} (attempt {attempt + 1})")
                time.sleep(0.5 * (attempt + 1))  # Increasing delay
            else:
                logger.error(f"Failed to remove {file_path} after {max_retries} attempts")
                return False
        except Exception as e:
            logger.error(f"Error removing {file_path}: {e}")
            return False
    return False


class ConversionEngine:
    """Base class for conversion engines"""
    
    def __init__(self):
        self.name = "base"
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert DOCX to PDF. Returns True if successful."""
        raise NotImplementedError
    
    def is_available(self) -> bool:
        """Check if this engine is available on the system"""
        raise NotImplementedError


class LibreOfficeEngine(ConversionEngine):
    """LibreOffice headless conversion engine"""
    
    def __init__(self):
        super().__init__()
        self.name = "LibreOffice"
        self.executable = self._find_executable()
    
    def _find_executable(self) -> Optional[str]:
        """Find LibreOffice executable"""
        # Check environment variable first
        if os.environ.get('LIBREOFFICE_PATH'):
            return os.environ.get('LIBREOFFICE_PATH')
        
        # Common paths for different OS
        if platform.system() == "Windows":
            paths = [
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        else:
            # Linux/macOS
            paths = [
                "/usr/bin/libreoffice",
                "/usr/local/bin/libreoffice",
                "/opt/libreoffice/program/soffice",
                "/Applications/LibreOffice.app/Contents/MacOS/soffice"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
        
        # Try system PATH
        try:
            result = subprocess.run(['which', 'libreoffice'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        return None
    
    def is_available(self) -> bool:
        """Check if LibreOffice is available"""
        return self.executable is not None
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert using LibreOffice headless with isolated user profile for maximum parallel concurrency"""
        if not self.executable:
            return False
        
        output_dir = os.path.dirname(output_path)
        profile_dir = tempfile.mkdtemp(prefix="lo_profile_", dir=TEMP_DIR)
        profile_uri = Path(profile_dir).as_uri()
        
        try:
            # LibreOffice command dengan UserInstallation terisolasi
            cmd = [
                self.executable,
                f'-env:UserInstallation={profile_uri}',
                '--headless',
                '--invisible',
                '--nodefault',
                '--nolockcheck',
                '--nologo',
                '--norestore',
                '--convert-to', 'pdf:writer_pdf_Export',
                '--outdir', output_dir,
                input_path
            ]
            
            logger.info(f"Running LibreOffice: {' '.join(cmd)}")
            
            # Run with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=CONVERSION_TIMEOUT
                )
                
                if process.returncode == 0:
                    # LibreOffice creates filename.pdf, we might need to rename
                    input_name = Path(input_path).stem
                    expected_pdf = os.path.join(output_dir, f"{input_name}.pdf")
                    
                    if os.path.exists(expected_pdf) and os.path.getsize(expected_pdf) > 0:
                        if expected_pdf != output_path:
                            shutil.move(expected_pdf, output_path)
                        return True
                
                logger.error(f"LibreOffice failed: {stderr.decode()}")
                return False
                
            except asyncio.TimeoutError:
                logger.error(f"LibreOffice conversion timed out after {CONVERSION_TIMEOUT}s")
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"LibreOffice conversion error: {e}")
            return False
        finally:
            # Cleanup temporary LibreOffice user profile
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
            except Exception:
                pass



class MSWordEngine(ConversionEngine):
    """MS Word COM automation engine (Windows only)"""
    
    def __init__(self):
        super().__init__()
        self.name = "MS Word"
    
    def is_available(self) -> bool:
        """Check if MS Word is available (Windows only)"""
        if platform.system() != "Windows":
            return False
        
        try:
            import win32com.client
            word = win32com.client.Dispatch("Word.Application")
            word.Quit()
            return True
        except:
            return False
    
    async def convert(self, input_path: str, output_path: str) -> bool:
        """Convert using MS Word COM automation with proper COM initialization"""
        if platform.system() != "Windows":
            return False
        
        def _convert_with_com():
            """Convert with proper COM initialization in thread"""
            import sys
            com_initialized = False
            
            try:
                # Initialize COM for this thread
                if sys.platform == "win32":
                    import pythoncom
                    pythoncom.CoInitialize()
                    com_initialized = True
                
                from docx2pdf import convert
                convert(input_path, output_path)
                
                return os.path.exists(output_path) and os.path.getsize(output_path) > 0
                
            except Exception as e:
                logger.error(f"MS Word conversion error: {e}")
                return False
            finally:
                # Cleanup COM
                if com_initialized and sys.platform == "win32":
                    try:
                        import pythoncom
                        pythoncom.CoUninitialize()
                    except:
                        pass
        
        try:
            # Run in thread pool with proper COM initialization
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(executor, _convert_with_com)
            return result
            
        except Exception as e:
            logger.error(f"MS Word executor error: {e}")
            return False


# Initialize engines
libre_engine = LibreOfficeEngine()
word_engine = MSWordEngine()

# Available engines in priority order
engines = [libre_engine, word_engine]
available_engines = [engine for engine in engines if engine.is_available()]

logger.info(f"Available engines: {[engine.name for engine in available_engines]}")
logger.info(f"Configuration: {MAX_WORKERS} workers, {CONVERSION_TIMEOUT}s timeout")

# Calculate theoretical capacity
if available_engines:
    theoretical_max = (MAX_WORKERS * 60) / CONVERSION_TIMEOUT
    realistic_throughput = theoretical_max * 0.7  # Account for overhead
    logger.info(f"Theoretical capacity: {theoretical_max:.1f} conversions/minute")
    logger.info(f"Realistic throughput: {realistic_throughput:.1f} conversions/minute")
    
    if realistic_throughput < 20:
        logger.warning(f"Current config may not handle high volume (20+ conversions/min)")
        logger.warning(f"Consider increasing MAX_WORKERS or reducing CONVERSION_TIMEOUT")
else:
    logger.error("No conversion engines available!")

# Cleanup old conversions periodically
async def cleanup_old_conversions():
    """Clean up old conversion files and status"""
    while True:
        try:
            current_time = datetime.now()
            expired_conversions = []
            
            for conv_id, status in conversion_status.items():
                # Remove conversions older than configured age
                if (current_time - status["created_time"]).total_seconds() > MAX_FILE_AGE:
                    expired_conversions.append(conv_id)
            
            for conv_id in expired_conversions:
                status = conversion_status[conv_id]
                # Clean up files
                for path in [status.get("input_path"), status.get("output_path")]:
                    if path and os.path.exists(path):
                        safe_remove_file(path)
                
                # Remove from status
                del conversion_status[conv_id]
                logger.info(f"Cleaned up expired conversion: {conv_id}")
            
            # Sleep for configured interval before next cleanup
            await asyncio.sleep(CLEANUP_INTERVAL)
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            await asyncio.sleep(600)

# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    global conversion_semaphore, http_client
    conversion_semaphore = asyncio.Semaphore(MAX_WORKERS)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(90.0, connect=15.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )
    
    # Startup
    asyncio.create_task(cleanup_old_conversions())
    logger.info("PDF Converter service started")
    logger.info(f"Available conversion engines: {[engine.name for engine in available_engines]}")
    logger.info(f"Worker concurrency active: max {MAX_WORKERS} simultaneous conversions")
    
    yield
    
    # Shutdown
    logger.info("PDF Converter service shutting down")
    if http_client and not http_client.is_closed:
        await http_client.aclose()
    # Clean up any remaining files
    for status in conversion_status.values():
        for path in [status.get("input_path"), status.get("output_path")]:
            if path and os.path.exists(path):
                safe_remove_file(path)

# Set lifespan after engines are initialized
app.router.lifespan_context = lifespan


async def upload_pdf_to_target(conversion_id: str, pdf_path: str) -> bool:
    """Upload PDF file to target URL using shared connection pool"""
    try:
        if conversion_id not in conversion_status:
            logger.error(f"Conversion status not found for {conversion_id}")
            return False
            
        status = conversion_status[conversion_id]
        target_url = status.get("target_url")
        nomor_urut = status.get("nomor_urut")
        
        if not target_url:
            logger.error(f"No target_url found for {conversion_id}")
            return False
            
        # Determine endpoint based on original request
        endpoint_type = status.get("endpoint_type", "convert")  # default to convert
        
        if endpoint_type == "convertDua":
            post_url = f"{target_url.rstrip('/')}/check/responseBalikConvertDua"
        else:
            post_url = f"{target_url.rstrip('/')}/check/responseBalikConvert"
            
        logger.info(f"Uploading PDF for {conversion_id} to {post_url}")
        
        # Upload with retry logic
        max_retries = 3
        retry_delay = 1
        resp = None
        
        for attempt in range(max_retries + 1):
            try:
                timeout_config = httpx.Timeout(90.0, connect=15.0)
                file_size = os.path.getsize(pdf_path)
                logger.info(f"Attempt {attempt + 1}/{max_retries + 1} - Uploading PDF size: {file_size} bytes")
                
                with open(pdf_path, "rb") as fpdf:
                    files = {"docupload": (os.path.basename(pdf_path), fpdf, "application/pdf")}
                    headers = {"User-Agent": "FastAPI-PDF-Converter/1.0"}
                    data = {"overwrite": "true", "force_replace": "1"}
                    
                    if http_client and not http_client.is_closed:
                        resp = await http_client.post(post_url, files=files, headers=headers, data=data)
                    else:
                        async with httpx.AsyncClient(timeout=timeout_config) as client:
                            resp = await client.post(post_url, files=files, headers=headers, data=data)
                    
                    # If success or not server error, break from retry loop
                    if resp.status_code < 500:
                        break
                            
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < max_retries:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    logger.error(f"Upload failed after {max_retries + 1} attempts: {e}")
                    return False
        
        if resp is None:
            logger.error("No response received from target server")
            return False
            
        logger.info(f"Upload response status: {resp.status_code}")
        
        # Check if upload was successful
        if 200 <= resp.status_code < 300:
            try:
                resp_json = resp.json()
                if "upload_data" in resp_json:
                    logger.info(f"Upload successful for {conversion_id}")
                    return True
                else:
                    logger.warning(f"Upload response missing upload_data: {resp.text}")
                    return False
            except Exception as e:
                logger.warning(f"Failed to parse upload response: {e}")
                # Still consider it successful if status code is 2xx
                return True
        else:
            logger.error(f"Upload failed with status {resp.status_code}: {resp.text}")
            return False
            
    except Exception as e:
        logger.error(f"Upload error for {conversion_id}: {e}")
        return False


async def convert_file(input_path: str, output_path: str, conversion_id: str) -> bool:
    """Convert DOCX to PDF using available engines with worker concurrency throttling"""
    if conversion_semaphore is not None:
        async with conversion_semaphore:
            return await _exec_convert_file(input_path, output_path, conversion_id)
    else:
        return await _exec_convert_file(input_path, output_path, conversion_id)


async def _exec_convert_file(input_path: str, output_path: str, conversion_id: str) -> bool:
    """Internal conversion executor"""
    conversion_status[conversion_id]["status"] = "processing"
    conversion_status[conversion_id]["start_time"] = datetime.now()
    
    if not available_engines:
        conversion_status[conversion_id]["error"] = "No conversion engines available"
        conversion_status[conversion_id]["status"] = "failed"
        return False
    
    # Try each engine in order
    for engine in available_engines:
        try:
            logger.info(f"Trying {engine.name} for conversion {conversion_id}")
            conversion_status[conversion_id]["current_engine"] = engine.name
            
            success = await engine.convert(input_path, output_path)
            
            if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                conversion_status[conversion_id]["status"] = "uploading"
                conversion_status[conversion_id]["engine_used"] = engine.name
                logger.info(f"Conversion {conversion_id} completed with {engine.name}, starting upload...")
                
                # Upload file to target_url
                upload_success = await upload_pdf_to_target(conversion_id, output_path)
                
                if upload_success:
                    conversion_status[conversion_id]["status"] = "completed"
                    conversion_status[conversion_id]["end_time"] = datetime.now()
                    logger.info(f"Upload completed for {conversion_id}")
                    
                    # Cleanup files after successful upload
                    try:
                        safe_remove_file(input_path)
                        safe_remove_file(output_path)
                        logger.info(f"Deleted temp files for: {conversion_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup files for {conversion_id}: {e}")
                else:
                    conversion_status[conversion_id]["status"] = "upload_failed"
                    conversion_status[conversion_id]["error"] = "Failed to upload PDF to target"
                    conversion_status[conversion_id]["end_time"] = datetime.now()
                    logger.error(f"Upload failed for {conversion_id}")
                
                return upload_success
            else:
                logger.warning(f"{engine.name} failed for conversion {conversion_id}")
                
        except Exception as e:
            logger.error(f"{engine.name} error for conversion {conversion_id}: {e}")
            continue
    
    # All engines failed
    conversion_status[conversion_id]["status"] = "failed"
    conversion_status[conversion_id]["error"] = "All conversion engines failed"
    conversion_status[conversion_id]["end_time"] = datetime.now()
    return False


@app.get("/")
async def root():
    """Health check endpoint"""
    active_conversions = len([s for s in conversion_status.values() if s["status"] in ["queued", "processing"]])
    
    return {
        "service": "Simple PDF Converter",
        "status": "running",
        "available_engines": [engine.name for engine in available_engines],
        "max_workers": MAX_WORKERS,
        "active_conversions": active_conversions,
        "worker_utilization": f"{(active_conversions / MAX_WORKERS * 100):.1f}%" if MAX_WORKERS > 0 else "0%"
    }


@app.post("/convert")
async def convert_docx(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    nomor_urut: str = Form(...),
    target_url: str = Form(...)
):
    """Convert DOCX to PDF"""
    
    # Validate file
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only DOCX files are supported")
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: {MAX_FILE_SIZE} bytes")
    
    # Use nomor_urut as conversion ID
    conversion_id = nomor_urut
    
    # Create files with nomor_urut naming
    temp_input = os.path.join(TEMP_DIR, f"{conversion_id}.docx")
    temp_output = os.path.join(TEMP_DIR, f"{conversion_id}.pdf")
    
    try:
        # Save uploaded file
        async with aiofiles.open(temp_input, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Initialize conversion status
        conversion_status[conversion_id] = {
            "id": conversion_id,
            "filename": file.filename,
            "nomor_urut": nomor_urut,
            "target_url": target_url,
            "endpoint_type": "convert",
            "status": "queued",
            "created_time": datetime.now(),
            "input_path": temp_input,
            "output_path": temp_output
        }
        
        # Start conversion in background
        background_tasks.add_task(convert_file, temp_input, temp_output, conversion_id)
        
        return JSONResponse({
            "conversion_id": conversion_id,
            "status": "queued",
            "message": "Conversion started",
            "nomor_urut": nomor_urut
        })
        
    except Exception as e:
        # Cleanup on error
        for path in [temp_input, temp_output]:
            if os.path.exists(path):
                safe_remove_file(path)
        
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process upload")


@app.post("/convertDua")
async def convert_dua(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    nomor_urut: str = Form(None),
    target_url: str = Form(None)
):
    """Convert DOCX to PDF - Enhanced API endpoint"""
    
    # Validate file
    if not file.filename.lower().endswith('.docx'):
        return JSONResponse(
            status_code=400,
            content={"error": "Only DOCX files are supported"}
        )
    
    if file.size and file.size > MAX_FILE_SIZE:
        return JSONResponse(
            status_code=400,
            content={"error": f"File too large. Max size: {MAX_FILE_SIZE} bytes"}
        )
    
    # Generate conversion ID using nomor_urut if provided
    if nomor_urut:
        conversion_id = nomor_urut
    else:
        conversion_id = str(uuid.uuid4())
    
    # Create temp files with specific naming
    temp_input = os.path.join(TEMP_DIR, f"{conversion_id}.docx")
    temp_output = os.path.join(TEMP_DIR, f"{conversion_id}.pdf")
    
    try:
        # Save uploaded file
        async with aiofiles.open(temp_input, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"ConvertDua: Processing file {file.filename} -> {conversion_id}")
        
        # Initialize conversion status
        conversion_status[conversion_id] = {
            "id": conversion_id,
            "filename": file.filename,
            "nomor_urut": nomor_urut,
            "target_url": target_url,
            "endpoint_type": "convertDua",
            "status": "queued",
            "created_time": datetime.now(),
            "input_path": temp_input,
            "output_path": temp_output
        }
        
        # Start conversion in background
        background_tasks.add_task(convert_file, temp_input, temp_output, conversion_id)
        
        # Return enhanced response format
        return JSONResponse({
            "success": True,
            "message": "Conversion request received",
            "nomor_urut": nomor_urut,
            "status": "queued",
            "conversion_id": conversion_id
        })
        
    except Exception as e:
        # Cleanup on error
        for path in [temp_input, temp_output]:
            if os.path.exists(path):
                safe_remove_file(path)
        
        logger.error(f"ConvertDua error: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Failed to process conversion request",
                "message": str(e)
            }
        )


@app.get("/status/{conversion_id}")
async def get_status(conversion_id: str):
    """Get conversion status"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id].copy()
    
    # Remove file paths from response
    status.pop("input_path", None)
    status.pop("output_path", None)
    
    # Convert datetime to string
    for key in ["created_time", "start_time", "end_time"]:
        if key in status and status[key]:
            status[key] = status[key].isoformat()
    
    return status


@app.get("/download/{conversion_id}")
async def download_pdf(conversion_id: str):
    """Download converted PDF"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id]
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Conversion not completed")
    
    output_path = status["output_path"]
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Generate download filename
    original_name = Path(status["filename"]).stem
    pdf_filename = f"{original_name}.pdf"
    
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=pdf_filename
    )


@app.get("/pdf/{conversion_id}")
async def get_pdf_direct(conversion_id: str):
    """Direct PDF access - Enhanced endpoint"""
    if conversion_id not in conversion_status:
        # Try to find PDF file directly in temp directory
        pdf_path = os.path.join(TEMP_DIR, f"{conversion_id}.pdf")
        if os.path.exists(pdf_path):
            return FileResponse(
                pdf_path,
                media_type="application/pdf",
                filename=f"{conversion_id}.pdf"
            )
        raise HTTPException(status_code=404, detail="PDF not found")
    
    status = conversion_status[conversion_id]
    output_path = status["output_path"]
    
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=f"{conversion_id}.pdf"
    )


@app.delete("/cleanup/{conversion_id}")
async def cleanup_conversion(conversion_id: str):
    """Clean up conversion files"""
    if conversion_id not in conversion_status:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    status = conversion_status[conversion_id]
    
    # Remove files
    for path in [status.get("input_path"), status.get("output_path")]:
        if path and os.path.exists(path):
            safe_remove_file(path)
    
    # Remove from status tracking
    del conversion_status[conversion_id]
    
    return {"message": "Cleanup completed"}


@app.get("/queue/status")
async def queue_status():
    """Get overall queue status - Enhanced endpoint"""
    total = len(conversion_status)
    completed = sum(1 for s in conversion_status.values() if s["status"] == "completed")
    processing = sum(1 for s in conversion_status.values() if s["status"] == "processing")
    failed = sum(1 for s in conversion_status.values() if s["status"] == "failed")
    queued = total - completed - processing - failed
    
    # Calculate estimated wait time (rough estimate)
    avg_processing_time = 30  # seconds per conversion
    estimated_wait_minutes = max(0, (queued + processing) * avg_processing_time // 60)
    
    # High volume status indicators
    current_throughput = (MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7
    is_high_volume_ready = current_throughput >= 20
    
    if (queued + processing) == 0:
        status_message = "Service siap digunakan"
    elif (queued + processing) < 5:
        status_message = "Antrian sedikit"
    elif (queued + processing) < 15:
        status_message = "Antrian sedang"
    elif (queued + processing) < 30:
        status_message = "Antrian panjang"
    else:
        status_message = "Antrian sangat panjang - pertimbangkan scaling"
    
    return {
        "success": True,
        "service_status": "online" if available_engines else "offline",
        "total_conversions": total,
        "queued": queued,
        "processing": processing,
        "completed": completed,
        "failed": failed,
        "queue_size": queued + processing,
        "estimated_wait_minutes": estimated_wait_minutes,
        "available_engines": [engine.name for engine in available_engines],
        "current_throughput_per_minute": round(current_throughput, 1),
        "high_volume_ready": is_high_volume_ready,
        "message": status_message
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    # Get system resource info
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    active_conversions = len([s for s in conversion_status.values() if s["status"] in ["queued", "processing"]])
    
    return {
        "status": "healthy",
        "service": "Simple PDF Converter",
        "engines_available": len(available_engines),
        "engines": [engine.name for engine in available_engines],
        "active_conversions": active_conversions,
        "max_workers": MAX_WORKERS,
        "worker_utilization": f"{(active_conversions / MAX_WORKERS * 100):.1f}%" if MAX_WORKERS > 0 else "0%",
        "system_resources": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "cpu_cores": psutil.cpu_count()
        },
        "performance_metrics": {
            "theoretical_max_per_minute": round((MAX_WORKERS * 60) / CONVERSION_TIMEOUT, 1),
            "realistic_throughput_per_minute": round((MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7, 1),
            "current_queue_wait_minutes": round(active_conversions * (CONVERSION_TIMEOUT / 60) / MAX_WORKERS, 1) if MAX_WORKERS > 0 else 0
        },
        "recommendations": {
            "current_load": "high" if active_conversions > MAX_WORKERS * 0.8 else "medium" if active_conversions > MAX_WORKERS * 0.5 else "low",
            "suggested_action": "Consider increasing workers" if active_conversions > MAX_WORKERS * 0.8 and cpu_percent < 80 and memory.percent < 80 else "Current workers sufficient",
            "high_volume_ready": "Yes" if (MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7 >= 20 else "No - increase workers"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/monitor/data")
async def get_monitor_data():
    """Provides combined data for the monitoring dashboard."""
    # From health_check()
    cpu_percent = psutil.cpu_percent(interval=None) # Non-blocking
    memory = psutil.virtual_memory()
    active_conversions = len([s for s in conversion_status.values() if s["status"] in ["queued", "processing"]])
    worker_utilization = (active_conversions / MAX_WORKERS * 100) if MAX_WORKERS > 0 else 0
    
    # From queue_status()
    total = len(conversion_status)
    completed = sum(1 for s in conversion_status.values() if s["status"] == "completed")
    processing = sum(1 for s in conversion_status.values() if s["status"] in ["processing", "uploading"])
    failed = sum(1 for s in conversion_status.values() if s["status"] in ["failed", "upload_failed"])
    queued = total - processing - completed - failed
    queue_size = queued + processing

    current_throughput = (MAX_WORKERS * 60) / CONVERSION_TIMEOUT * 0.7 if CONVERSION_TIMEOUT > 0 else 0
    is_high_volume_ready = current_throughput >= 20

    if queue_size == 0:
        status_message = "Service ready"
    elif queue_size < 5:
        status_message = "Low queue"
    elif queue_size < 15:
        status_message = "Medium queue"
    elif queue_size < 30:
        status_message = "High queue"
    else:
        status_message = "Very high queue - consider scaling"

    return {
        "service": {
            "status": "healthy" if available_engines else "degraded",
            "engines": [engine.name for engine in available_engines],
            "high_volume_ready": "Yes" if is_high_volume_ready else "No",
            "message": status_message,
        },
        "workers": {
            "active": active_conversions,
            "max": MAX_WORKERS,
            "utilization": f"{worker_utilization:.1f}%",
        },
        "system": {
            "cpu_percent": f"{cpu_percent:.1f}",
            "memory_percent": f"{memory.percent:.1f}",
            "cpu_cores": psutil.cpu_count(),
        },
        "performance": {
            "realistic_throughput_per_minute": round(current_throughput, 1),
            "current_queue_wait_minutes": round(queue_size * (CONVERSION_TIMEOUT / 60) / MAX_WORKERS, 1) if MAX_WORKERS > 0 else 0,
        },
        "queue": {
            "total": total,
            "size": queue_size,
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed,
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/monitor", response_class=HTMLResponse)
async def monitoring_dashboard():
    """Web-based monitoring dashboard"""
    try:
        with open("static/monitor.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Monitoring Dashboard Not Found</h1><p>Please ensure static/monitor.html exists</p>",
            status_code=404
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=SERVICE_HOST, port=SERVICE_PORT)
