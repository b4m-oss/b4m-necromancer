import json
import os
import subprocess
import datetime
import time
import shutil
from pathlib import Path
from PIL import Image, ImageStat
import threading

from .upload_adapter import get_uploader_from_config


def is_blank_page(image_path, white_threshold=187, white_ratio_threshold=0.995):
    """
    Helper to decide whether the page is almost blank (mostly white).
    - white_threshold: pixels at or above this value are treated as \"white\"
    - white_ratio_threshold: if the ratio of white pixels is above this value, treat as blank
    """
    try:
        img = Image.open(image_path).convert("L")
        # Downscale for performance if needed
        max_size = 512
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size))

        hist = img.histogram()
        total_pixels = sum(hist)
        if total_pixels == 0:
            return False

        # Count pixels above the white_threshold
        start_index = int(white_threshold)
        white_pixels = sum(hist[start_index:])
        white_ratio = white_pixels / total_pixels

        print(
            f"Blank page check: {os.path.basename(image_path)} "
            f"pixels={total_pixels}, white_pixels={white_pixels}, "
            f"white_ratio={white_ratio:.4f}"
        )

        return white_ratio >= white_ratio_threshold
    except Exception as e:
        print(f"Error while checking blank page: {e} (file={image_path})")
        return False

def create_timestamp_dir():
    """Create a temporary directory named with a timestamp and return its path."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    tmp_dir = Path(__file__).resolve().parent.parent / 'tmp' / timestamp
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir, timestamp

def convert_images_to_pdf(image_dir, output_pdf):
    """Convert all images in the given directory into a single PDF."""
    # Only take image files directly under the directory (no subdirectories)
    image_files = []
    for f in os.listdir(image_dir):
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and os.path.isfile(os.path.join(image_dir, f)):
            image_files.append(f)
    
    image_files = sorted(image_files)  # sort by filename
    
    if not image_files:
        print("No image files found to convert into PDF")
        return False
    
    print(f"PDF conversion target: {len(image_files)} images")
    print(f"Image file list: {image_files}")
    
    try:
        if len(image_files) == 1:
            # Single-page case
            print(f"Creating single-page PDF from: {image_files[0]}")
            img = Image.open(os.path.join(image_dir, image_files[0]))
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(output_pdf)
            print(f"Single-page PDF created successfully: {output_pdf}")
            return True
        
        # Multi-page case
        print(f"Creating multi-page PDF ({len(image_files)} pages)")
        images = []
        first_image = Image.open(os.path.join(image_dir, image_files[0]))
        print(f"Loading first image: {image_files[0]}")
        
        for img_file in image_files[1:]:
            img_path = os.path.join(image_dir, img_file)
            print(f"Loading additional image: {img_file}")
            img = Image.open(img_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        
        if first_image.mode != 'RGB':
            first_image = first_image.convert('RGB')
        
        first_image.save(output_pdf, save_all=True, append_images=images)
        print(f"PDF created successfully: {output_pdf} (pages: {len(image_files)})")
        
        # Sanity check for the PDF file
        if os.path.exists(output_pdf):
            pdf_size = os.path.getsize(output_pdf)
            print(f"PDF file size: {pdf_size / 1024:.1f} KB")
            if pdf_size == 0:
                print("Warning: PDF file size is 0 bytes")
                return False
        else:
            print(f"Error: PDF file {output_pdf} does not exist")
            return False
            
        return True
    except Exception as e:
        print(f"Error while converting images to PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_scan_configs(config_path: str = str(Path(__file__).resolve().parent.parent / 'config' / 'mode.json')):
    """Load scan configuration from mode.json."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_scanner_config(config_path: str = str(Path(__file__).resolve().parent.parent / 'config' / 'scanner.json')):
    """
    Load scanner configuration from scanner.json.
    If the file is missing or invalid, return iX500 defaults.
    """
    default_cfg = {
        "device_name": "fujitsu:ScanSnap iX500:17872",
        "backend": "fujitsu",
        "default_source": "ADF Duplex",
        "test_timeout_sec": 10,
    }
    try:
        if not os.path.isfile(config_path):
            return default_cfg
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults (fill missing keys)
        merged = {**default_cfg, **data}
        return merged
    except Exception as e:
        print(f"Error while reading scanner.json: {e}")
        return default_cfg

def get_scanner_list():
    """Get a list of available scanners via scanimage -L."""
    try:
        result = subprocess.run(['scanimage', '-L'], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error while listing scanners: {e}")
        return ""

def scanimage_scan(output_path, device_name, resolution=300, mode='Color', source='ADF Duplex', format='jpeg'):
    """
    Run a scan using scanimage.
    :param output_path: output file path
    :param device_name: scanner device name
    :param resolution: resolution
    :param mode: scan mode (Color, Gray, Lineart)
    :param source: scan source (Flatbed, ADF Duplex)
    :param format: output format (jpeg, png, tiff, pnm)
    :return: True on success, False otherwise
    """
    try:
        # Build scanimage command
        cmd = [
            'scanimage',
            f'--device-name="{device_name}" ',
            f'--resolution={resolution}',
            f'--mode={mode}',
            f'--source={source}',
            f'--format={format}',
            '-o', output_path
        ]
        
        print(f"Executing command: {' '.join(cmd)}")
        
        # Run command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Scan error: {result.stderr}")
            return False
        
        print(f"Scan succeeded: {output_path}")
        return True
    
    except Exception as e:
        print(f"Exception while running scan: {e}")
        return False

def process_scanned_image(image_path):
    """Placeholder for post-processing the scanned image."""
    print(f"Post-processing image: {image_path}")

def monitor_scan_directory(directory, callback):
    """Monitor a scan directory and call the callback when new files appear."""
    processed_files = set()
    last_check_time = time.time()
    last_new_file_time = time.time()
    start_time = time.time()
    max_idle_time = 20  # maximum idle time (seconds) before we consider the scan finished
    min_monitoring_time = 10  # minimum monitoring time from start
    check_interval = 0.5  # polling interval (seconds)
    
    print(f"Start monitoring scan directory: {directory}")
    print(f"Monitor settings: max_idle={max_idle_time}s, min_time={min_monitoring_time}s")
    
    while True:
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        # Get all JPG files currently in the directory
        try:
            current_files = set([f for f in os.listdir(directory) 
                               if f.lower().endswith('.jpg') and 
                               os.path.isfile(os.path.join(directory, f))])
        except Exception as e:
            print(f"Directory read error: {e}")
            current_files = set()
        
        new_files = current_files - processed_files
        
        if new_files:
            print(f"Detected new files: {len(new_files)} ({', '.join(sorted(new_files))})")
            last_new_file_time = current_time  # reset when new files appear
            
            for file_name in sorted(new_files):
                file_path = os.path.join(directory, file_name)
                try:
                    # Check file size (to ensure writing has finished)
                    file_size = os.path.getsize(file_path)
                    print(f"Found file: {file_name} ({file_size / 1024:.1f} KB)")
                    
                    # Call the callback
                    callback(file_path)
                except Exception as e:
                    print(f"Error while processing file: {e}")
                processed_files.add(file_name)
        
        # Periodically print status
        if len(processed_files) > 0 and (current_time - last_check_time > 2):
            last_check_time = current_time
            idle_time = current_time - last_new_file_time
            print(f"Monitor status: processed={len(processed_files)}, idle={idle_time:.1f}s, elapsed={elapsed_time:.1f}s")
        
        # Exit conditions:
        # 1. No new files for a while
        # 2. At least one file has been processed
        # 3. Minimum monitoring time has passed
        if (current_time - last_new_file_time > max_idle_time and 
            len(processed_files) > 0 and 
            elapsed_time > min_monitoring_time):
            
            print(f"Scan-finished candidate: idle={current_time - last_new_file_time:.1f}s > {max_idle_time}s")
            
            # Final check (ensure no new files appeared)
            time.sleep(3)
            try:
                final_files = set([f for f in os.listdir(directory) 
                                 if f.lower().endswith('.jpg') and 
                                 os.path.isfile(os.path.join(directory, f))])
            except Exception as e:
                print(f"Error during final directory check: {e}")
                final_files = current_files
                
            if final_files == processed_files:
                print(f"Stopping scan directory monitor: processed {len(processed_files)} files")
                file_list_str = ", ".join(sorted(list(processed_files)))
                print(f"Processed files: {file_list_str}")
                return len(processed_files)
            else:
                # There are still new files
                new_count = len(final_files - processed_files)
                new_files_list = sorted(list(final_files - processed_files))
                print(f"Additional files detected ({new_count}): {', '.join(new_files_list)}")
                print("Continue monitoring")
                last_new_file_time = current_time
        
        # Short sleep before the next poll
        time.sleep(check_interval)

def batch_scan_with_scanimage(config_name: str, upload_to_nextcloud=True):
    """
    Run a batch scan with scanimage based on mode.json configuration.
    :param config_name: profile name defined in mode.json
    :param upload_to_nextcloud: whether to upload to the cloud
    :return: temporary directory path on success, None on failure
    """
    configs = load_scan_configs()
    if config_name not in configs:
        print(f"Error: configuration '{config_name}' is not defined in mode.json")
        return None
    
    cfg = configs[config_name]
    tmp_dir, timestamp = create_timestamp_dir()
    print(f"Created temporary scan directory: {tmp_dir}")
    
    # Scan settings
    scanner_cfg = load_scanner_config()
    device_name = scanner_cfg.get("device_name", "fujitsu:ScanSnap iX500:17872")
    resolution = cfg.get('resolution', 200)
    mode = cfg.get('mode', 'Color')
    # scanimage is usually case-insensitive, but normalize for clarity
    if isinstance(mode, str) and mode:
        mode = mode[0].upper() + mode[1:].lower()
    else:
        mode = "Color"
    # Prefer source from mode.json, fall back to scanner.json default_source
    source = cfg.get('source', scanner_cfg.get('default_source', 'ADF Duplex'))
    format = cfg.get('file_format', 'jpeg').lower()
    if format == 'jpg':
        format = 'jpeg'  # scanimage expects 'jpeg'
    
    # Output pattern (extension fixed to .jpg for intermediate images)
    output_pattern = str(tmp_dir / f"{config_name}-%d.jpg")
    
    print(f"Starting batch scan with config: {config_name}")
    print(f"Scanner settings: device={device_name}, resolution={resolution}, mode={mode}")
    print(f"Output pattern: {output_pattern}")
    print("All pages in the feeder will be scanned...")
    
    # Use ScannerManager
    scanner = ScannerManager.get_instance()
    
    # Warm up the scanner to make sure it is ready
    scanner_ready = scanner.warm_up_scanner()
    if not scanner_ready:
        print("Warning: scanner warm-up reported an issue, but will try scanning anyway")
    
    # Execute batch scan
    print("Starting batch scan...")
    success = False
    
    # Run batch scan command
    try:
        # Build extra options from mode.json
        extra_opts = []
        if cfg.get('swdeskew'):
            extra_opts.append('--swdeskew=yes')
        if cfg.get('swcrop'):
            extra_opts.append('--swcrop=yes')
        if cfg.get('ald'):
            extra_opts.append('--ald=yes')
        # Fixed size and max height are mutually exclusive
        page_width_mm = cfg.get('page_width_mm')
        page_height_mm = cfg.get('page_height_mm')
        max_page_height_mm = cfg.get('max_page_height_mm')
        if page_width_mm:
            extra_opts.append(f'--page-width={page_width_mm}')
        if page_height_mm:
            extra_opts.append(f'--page-height={page_height_mm}')
        elif max_page_height_mm:
            extra_opts.append(f'--page-height={max_page_height_mm}')

        extra_str = ""
        if extra_opts:
            extra_str = " " + " ".join(extra_opts)

        batch_cmd = (
            f'scanimage --device="{device_name}" '
            f'--resolution={resolution} '
            f'--mode={mode} '
            f'--format=jpeg '
            f'--source="{source}" '
            f'--batch={output_pattern} '
            f'--batch-count=-1 '       # scan all pages
            f'--batch-start=1 '        # start numbering at 1
            f'--progress'
            f'{extra_str} '
        )
        
        print(f"Executing batch command: {batch_cmd}")
        result = subprocess.run(batch_cmd, shell=True, capture_output=True, text=True, timeout=180)
        
        # Log scan output
        print("scanimage stdout:")
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("scanimage stderr (errors/warnings):")
            print(result.stderr)
            
            # Inspect stderr to infer success
            if "scanned" in result.stderr and "pages scanned" in result.stderr:
                # Extract the number of pages scanned
                import re
                matches = re.search(r'(\d+) pages scanned', result.stderr)
                if matches and int(matches.group(1)) > 0:
                    print(f"Scan succeeded: {matches.group(1)} pages scanned")
                    success = True
                elif "0 pages scanned" in result.stderr:
                    print("Scan error: 0 pages scanned")
                    success = False
                else:
                    # No explicit page count but also no clear error
                    print("Treating scan as success (page count unknown)")
                    success = True
            elif "error" in result.stderr.lower():
                print("Error detected in scan stderr")
                success = False
            else:
                # No explicit error in stderr, treat as success
                print("No error message found, treating scan as success")
                success = True
        
        # Also check return code
        if result.returncode != 0:
            print(f"Warning: scanimage exited with non-zero status {result.returncode}")
            # We may still treat as success if files exist
        else:
            print("scanimage finished with status code 0")
            success = True
            
    except subprocess.TimeoutExpired:
        print("Scan process timed out. Partial files may still exist.")
        # Treat as potentially successful and verify files later
        success = True
    except Exception as e:
        print(f"Exception during batch scan: {e}")
        success = False
    
    # Always verify files after the scan
    print("\nChecking scan results...")
    time.sleep(2)  # give the filesystem a moment to flush
    
    # Inspect directory contents
    try:
        all_files = os.listdir(tmp_dir)
        jpg_files = [f for f in all_files if f.lower().endswith('.jpg')]
        jpg_files.sort()
        
        print(f"Total files in directory: {len(all_files)}")
        print(f"JPEG files: {len(jpg_files)}")
        
        if jpg_files:
            print("Scanned files:")
            for idx, file_name in enumerate(jpg_files):
                file_path = os.path.join(tmp_dir, file_name)
                file_size = os.path.getsize(file_path)
                print(f"  {idx+1}. {file_name} ({file_size / 1024:.1f} KB)")
            success = True
        else:
            print("Warning: no scanned JPEG files found")
            if success:
                print("scanimage reported success, but no files were created")
                success = False
    except Exception as e:
        print(f"Error while checking output files: {e}")
    
    # Automatic blank page removal
    # Applied only when mode.json has blank_filter=true.
    # For backward compatibility, default to diary/flyer when setting is missing.
    if jpg_files and cfg.get('blank_filter', config_name in ('diary', 'flyer')):
        print("\nDetecting and removing blank pages...")
        kept_files = []
        removed_files = []
        for file_name in jpg_files:
            file_path = os.path.join(tmp_dir, file_name)
            if is_blank_page(file_path):
                print(f"Detected blank page, removing: {file_name}")
                removed_files.append(file_name)
                try:
                    os.remove(file_path)
                    print(f"Deleted blank image file: {file_name}")
                except Exception as e:
                    print(f"Error while deleting blank file: {e}")
            else:
                kept_files.append(file_name)
        jpg_files = kept_files
        print(f"Pages remaining after blank removal: {len(jpg_files)} (removed: {len(removed_files)})")

    # If we have no results, treat as failure
    if not success or not jpg_files:
        print("Scan failed; removing temporary directory.")
        try:
            shutil.rmtree(tmp_dir)
        except:
            pass
        return None
    
    print(f"\nScan completed: {len(jpg_files)} pages")
    
    # PDF conversion (only when file_format is PDF)
    pdf_created = False
    pdf_path = None
    
    if cfg.get('file_format', '').upper() == 'PDF':
        app_tmp_dir = Path(__file__).resolve().parent.parent / 'tmp'
        pdf_path = app_tmp_dir / f"{config_name}-{timestamp}.pdf"
        print(f"Starting PDF conversion for {len(jpg_files)} page images...")
        if convert_images_to_pdf(tmp_dir, pdf_path):
            # Verify that the PDF was created correctly
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                print(f"Created PDF: {pdf_path}")
                pdf_created = True
                
                pdf_size = os.path.getsize(pdf_path) / 1024
                print(f"Created PDF file: {pdf_path.name} ({pdf_size:.1f} KB)")
            else:
                print(f"Error: PDF file not created or has size 0: {pdf_path}")
        else:
            print("PDF conversion failed")
    
    # Upload to cloud (unless --no-upload was specified)
    if upload_to_nextcloud and success:
        uploader = get_uploader_from_config()
        if pdf_created and pdf_path:
            print("\nUploading PDF to cloud...")
            upload_success = uploader.upload_pdf(str(pdf_path))
            if upload_success:
                print("Upload to cloud completed")
                # After successful upload, we can safely delete the temp directory
                try:
                    shutil.rmtree(tmp_dir)
                    print(f"Deleted temporary directory: {tmp_dir}")
                except Exception as e:
                    print(f"Error while deleting temporary directory: {e}")
        else:
            # No PDF, upload the JPEG files instead
            print("\nUploading image files to cloud...")
            upload_success = uploader.upload_directory(str(tmp_dir))
            if upload_success:
                print("Upload to cloud completed")
    else:
        print("\nUpload to cloud was skipped")
    
    if success:
        return tmp_dir
    else:
        return None

def single_scan_with_scanimage(output_path: str, config_name: str, upload_to_nextcloud=True):
    """
    Run a single-page scan with scanimage.
    :param output_path: output file path
    :param config_name: configuration name in mode.json
    :param upload_to_nextcloud: whether to upload to the cloud
    :return: True on success, False otherwise
    """
    configs = load_scan_configs()
    if config_name not in configs:
        print(f"Error: configuration '{config_name}' is not defined in mode.json")
        return False
    
    cfg = configs[config_name]
    
    # Scan settings
    scanner_cfg = load_scanner_config()
    device_name = scanner_cfg.get("device_name", "fujitsu:ScanSnap iX500:17872")
    resolution = cfg.get('resolution', 200)
    mode = cfg.get('mode', 'Color').lower()
    
    # Determine output format (only supported formats)
    format_map = {
        'jpg': 'jpeg',
        'jpeg': 'jpeg',
        'png': 'png',
        'tiff': 'tiff',
        'pnm': 'pnm'
    }
    
    ext = output_path.split('.')[-1].lower()
    format = format_map.get(ext, 'jpeg')  # default to jpeg for unsupported extensions
    
    print(f"Starting single-page scan with config: {config_name}")
    print(f"Output format: {format}")
    
    # Use ScannerManager
    scanner = ScannerManager.get_instance()
    
    # Warm up the scanner
    if not scanner.warm_up_scanner():
        print("Error: failed to warm up the scanner")
        return False
    
    scan_success = False
    try:
        # Build and run scanimage command via shell
        # source is taken from mode.json, with scanner.json default as fallback
        source = cfg.get('source', scanner_cfg.get('default_source', 'ADF Duplex'))

        cmd_parts = [
            f'scanimage --device="{device_name}"',
            f'--resolution={resolution}',
            f'--mode={mode}',
            f'--format={format}',
            f'--swdeskew=yes',
            f'--swcrop=yes',
            f'--source="{source}"'
        ]

        # For A4-fixed single-page scans, use page_width_mm/page_height_mm in mode.json
        page_width_mm = cfg.get('page_width_mm')
        page_height_mm = cfg.get('page_height_mm')
        if page_width_mm:
            cmd_parts.append(f'--page-width={page_width_mm}')
        if page_height_mm:
            cmd_parts.append(f'--page-height={page_height_mm}')
        else:
            # Default height for non-long-paper single scans
            cmd_parts.append('--page-height=512')

        cmd_parts.append(f'-o {output_path}')
        cmd_str = " ".join(cmd_parts)
        
        print(f"Executing command: {cmd_str}")
        
        # Run via shell (30-second timeout)
        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            print(f"Scan error: {result.stderr}")
            return False
        
        print(f"Scan succeeded: {output_path}")
        scan_success = True
        
        # Upload to cloud (unless --no-upload was specified)
        if upload_to_nextcloud and scan_success:
            uploader = get_uploader_from_config()
            print("\nUploading file to cloud...")
            upload_success = uploader.upload_file(output_path)
            if upload_success:
                print("Upload to cloud completed")
        else:
            print("\nUpload to cloud was skipped")
        
        return scan_success
    
    except subprocess.TimeoutExpired:
        print("Scan process timed out; it may still have succeeded.")
        # Check whether the file was actually created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"Scan output file exists: {output_path}")
            return True
        return False
    except Exception as e:
        print(f"Exception while running single-page scan: {e}")
        return False

def find_scanner():
    import sane
    sane.init()
    # Search for devices whose model name contains ix500 and usb
    devices = [dev for dev in sane.get_devices() 
               if 'ix500' in dev[1].lower() and 'usb' in dev[1].lower()]
    if devices:
        return devices[0][0]
    return None

class ScannerManager:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ScannerManager()
        return cls._instance
    
    def __init__(self):
        scanner_cfg = load_scanner_config()
        self.device_name = scanner_cfg.get("device_name", "fujitsu:ScanSnap iX500:17872")
        self.initialized = False
        self.scanner_process = None
        self.available = True
        
    def check_scanner_available(self):
        """
        Check whether the scanner is available.
        """
        try:
            # Use `scanimage -L` to detect scanners
            list_cmd = "scanimage -L"
            result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and self.device_name in result.stdout:
                print(f"Scanner found: {self.device_name}")
                return True
            else:
                print("Scanner not found. Available scanners:")
                print(result.stdout)
                
                # Try to find a partial match for the device name
                if "fujitsu" in result.stdout.lower() and "ix500" in result.stdout.lower():
                    print("Detected ScanSnap iX500; updating device name")
                    # Update device_name
                    import re
                    device_match = re.search(r'(fujitsu:ScanSnap iX500:[^\s`\'\"]+)', result.stdout)
                    if device_match:
                        self.device_name = device_match.group(1)
                        print(f"New device name: {self.device_name}")
                        return True
                
                # Fall back to the configured device name
                print(f"Falling back to configured device name: {self.device_name}")
                return True
        except Exception as e:
            print(f"Error while detecting scanner: {e}")
            print(f"Using configured scanner: {self.device_name}")
            return True
        
    def warm_up_scanner(self):
        """Warm up the scanner so it is ready to use."""
        try:
            print("Warming up scanner...")
            
            # First check that the scanner exists
            has_scanner = self.check_scanner_available()
            if not has_scanner:
                print("Scanner not found.")
                return False
            
            # Run a small test scan (no output) to wake up the device
            test_cmd = f'scanimage --device="{self.device_name}" -n'
            print(f"Scanner test command: {test_cmd}")
            
            try:
                test_result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=10)
                
                if test_result.returncode != 0:
                    print("Scanner self-test failed:")
                    print("stderr: " + test_result.stderr)
                    print("stdout: " + test_result.stdout)
                    print("There may be an issue with the scanner connection; continuing anyway...")
                else:
                    print("Scanner self-test succeeded. The scanner appears to be working.")
            except Exception as e:
                print(f"Error while running scanner self-test: {e}")
                print("Skipping self-test but continuing anyway...")
            
            print("Scanner warm-up completed")
            return True
        except Exception as e:
            print(f"Error while warming up scanner: {e}")
            print("The scanner may be disconnected or busy.")
            return False

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Scan documents with scanimage and save the result")
    parser.add_argument("config", nargs='?', help="Configuration name in mode.json (e.g. receipt)")
    parser.add_argument("--output", help="Output file path for single-page scan (e.g. output.png)")
    parser.add_argument("--list", action="store_true", help="List available scanners")
    parser.add_argument("--no-upload", action="store_true", help="Skip uploading to cloud")
    
    args = parser.parse_args()
    
    try:
        if args.list:
            # List scanners
            scanners = get_scanner_list()
            print(f"Available scanners:\n{scanners}")
            sys.exit(0)
        elif args.output and args.config:
            # Single-page mode
            success = single_scan_with_scanimage(args.output, args.config, not args.no_upload)
            sys.exit(0 if success else 1)
        elif args.config:
            # Batch scan mode
            result = batch_scan_with_scanimage(args.config, not args.no_upload)
            sys.exit(0 if result else 1)
        else:
            parser.print_help()
            sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
