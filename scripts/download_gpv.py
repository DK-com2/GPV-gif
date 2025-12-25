"""
GPV Weather Data Downloader
Downloads MSM NetCDF files from Kyoto University database
"""
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import yaml
import requests
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    ensure_directory,
    get_file_size_mb,
    parse_filename,
    cleanup_old_files,
    get_utc_now,
    get_forecast_times,
    get_nearest_forecast_time,
    format_datetime_for_filename,
    get_local_datetime_str,
    check_disk_space
)


def load_config(config_path='config/config.yaml'):
    """
    Load configuration from YAML file

    Args:
        config_path: Path to config file

    Returns:
        dict: Configuration dictionary
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config file: {e}")
        sys.exit(1)


def generate_candidate_urls(config, hours_back=6):
    """
    Generate candidate URLs from current time going back hours_back hours

    Args:
        config: Configuration dictionary
        hours_back: Number of hours to search back

    Returns:
        list: List of candidate URLs (newest first)
    """
    base_url = config['gpv_database']['base_url']
    forecast_hours = config['gpv_database']['forecast_hours']
    delay_hours = config['gpv_database']['data_delay_hours']

    urls = []
    current_time = get_utc_now()

    # Generate candidates for each 3-hour interval going back
    num_intervals = (hours_back // 3) + 2

    for i in range(num_intervals):
        check_time = current_time - timedelta(hours=i * 3 + delay_hours)

        # Round to nearest forecast hour
        for fh in reversed(forecast_hours):
            if fh <= check_time.hour:
                forecast_time = check_time.replace(hour=fh, minute=0, second=0, microsecond=0)
                break
        else:
            # If before 00:00, use previous day's 21:00
            forecast_time = (check_time - timedelta(days=1)).replace(hour=21, minute=0, second=0, microsecond=0)

        date_str, hour_str = format_datetime_for_filename(forecast_time)

        url = f"{base_url}{date_str}/MSM{date_str}{hour_str}S.nc"

        if url not in urls:
            urls.append(url)

    return urls


def check_file_exists(url, config):
    """
    Check if file exists at URL using HEAD request

    Args:
        url: URL to check
        config: Configuration dictionary

    Returns:
        tuple: (exists: bool, file_size: int or None)
    """
    try:
        headers = {'User-Agent': config['download']['user_agent']}
        timeout = config['download']['timeout']

        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)

        if response.status_code == 200:
            file_size = int(response.headers.get('Content-Length', 0))
            return True, file_size
        else:
            return False, None

    except requests.RequestException:
        return False, None


def find_latest_file(config):
    """
    Find the latest available NetCDF file

    Args:
        config: Configuration dictionary

    Returns:
        tuple: (url: str or None, file_size: int or None)
    """
    print("Searching for latest available GPV data...")

    urls = generate_candidate_urls(config, hours_back=12)
    request_interval = config['download']['request_interval']

    for i, url in enumerate(urls):
        filename = url.split('/')[-1]
        print(f"Checking: {filename}...", end=' ')

        exists, file_size = check_file_exists(url, config)

        if exists:
            print(f"Found! ({get_file_size_mb(file_size)})")
            return url, file_size
        else:
            print("Not found")

        # Respect request interval (except for last check)
        if i < len(urls) - 1:
            time.sleep(request_interval)

    return None, None


def download_file(url, save_path, config):
    """
    Download file from URL with progress bar and retry logic

    Args:
        url: Download URL
        save_path: Destination file path
        config: Configuration dictionary

    Returns:
        bool: True if successful, False otherwise
    """
    timeout = config['download']['timeout']
    max_retries = config['download']['max_retries']
    retry_delay = config['download']['retry_delay']
    headers = {'User-Agent': config['download']['user_agent']}

    for attempt in range(1, max_retries + 1):
        try:
            print(f"\nDownload attempt {attempt}/{max_retries}")
            print(f"URL: {url}")
            print(f"Saving to: {save_path}")

            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('Content-Length', 0))

            # Check disk space
            if not check_disk_space(os.path.dirname(save_path), total_size * 1.1):
                print("Error: Insufficient disk space")
                return False

            # Download with progress bar
            with open(save_path, 'wb') as f, tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="Downloading"
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            # Verify file size
            downloaded_size = os.path.getsize(save_path)
            if total_size > 0 and downloaded_size != total_size:
                print(f"Warning: Size mismatch (expected {total_size}, got {downloaded_size})")
                if attempt < max_retries:
                    os.remove(save_path)
                    continue
                return False

            print(f"Download completed: {get_file_size_mb(downloaded_size)}")
            return True

        except requests.exceptions.Timeout:
            print(f"Error: Download timeout after {timeout} seconds")
        except requests.exceptions.HTTPError as e:
            print(f"HTTP Error: {e}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Network error: {e}")
        except OSError as e:
            print(f"File system error: {e}")
            return False

        # Retry logic
        if attempt < max_retries:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("Max retries reached. Download failed.")
            if os.path.exists(save_path):
                os.remove(save_path)
            return False

    return False


def log_download(log_path, url, success, file_size=None, error=None):
    """
    Log download result to file

    Args:
        log_path: Path to log file
        url: Downloaded URL
        success: Whether download succeeded
        file_size: File size in bytes
        error: Error message if failed
    """
    ensure_directory(os.path.dirname(log_path))

    filename = url.split('/')[-1]
    timestamp = get_local_datetime_str()
    status = "SUCCESS" if success else "FAILED"

    if success:
        size_str = get_file_size_mb(file_size)
        log_line = f"{timestamp} | {status} | {filename} | {size_str}\n"
    else:
        error_msg = error or "Unknown error"
        log_line = f"{timestamp} | {status} | {filename} | {error_msg}\n"

    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except OSError as e:
        print(f"Warning: Could not write to log file: {e}")


def download_auto(config):
    """
    Auto mode: Find and download latest available file

    Args:
        config: Configuration dictionary

    Returns:
        bool: Success status
    """
    # Find latest file
    url, file_size = find_latest_file(config)

    if not url:
        print("\nNo available files found.")
        return False

    filename = url.split('/')[-1]

    # Create save path (simple structure: data/raw/MSM*.nc)
    raw_data_dir = config['storage']['raw_data_dir']
    ensure_directory(raw_data_dir)

    save_path = os.path.join(raw_data_dir, filename)

    # Check if file already exists
    if os.path.exists(save_path):
        existing_size = os.path.getsize(save_path)
        if existing_size == file_size:
            print(f"\nFile already exists with correct size: {save_path}")
            print(f"Size: {get_file_size_mb(existing_size)}")
            # Clean up old files, keeping only this one
            print("\nCleaning up old files...")
            deleted_count, freed_bytes = cleanup_old_files(raw_data_dir, keep_latest=True)
            if deleted_count > 0:
                print(f"Removed {deleted_count} old file(s), freed {get_file_size_mb(freed_bytes)}")
            return True
        else:
            print(f"File exists but size mismatch. Re-downloading...")

    # Clean up old files before downloading new one
    print("\nCleaning up old files...")
    deleted_count, freed_bytes = cleanup_old_files(raw_data_dir, keep_latest=False)
    if deleted_count > 0:
        print(f"Removed {deleted_count} old file(s), freed {get_file_size_mb(freed_bytes)}")

    # Download file
    success = download_file(url, save_path, config)

    # After successful download, clean up again to ensure only latest file remains
    if success:
        print("\nFinal cleanup to keep only latest file...")
        deleted_count, freed_bytes = cleanup_old_files(raw_data_dir, keep_latest=True)
        if deleted_count > 0:
            print(f"Removed {deleted_count} old file(s), freed {get_file_size_mb(freed_bytes)}")

    # Log result
    log_path = os.path.join(config['storage']['log_dir'], 'download.log')
    if success:
        downloaded_size = os.path.getsize(save_path)
        log_download(log_path, url, True, downloaded_size)
    else:
        log_download(log_path, url, False, error="Download failed")

    return success


def download_manual(config, date_str, hour):
    """
    Manual mode: Download specific date/time file

    Args:
        config: Configuration dictionary
        date_str: Date string (YYYYMMDD)
        hour: Forecast hour (0-21)

    Returns:
        bool: Success status
    """
    try:
        # Validate date
        dt = datetime.strptime(date_str, '%Y%m%d')
        dt = dt.replace(hour=int(hour))

        # Validate hour
        forecast_hours = config['gpv_database']['forecast_hours']
        if int(hour) not in forecast_hours:
            print(f"Error: Hour must be one of {forecast_hours}")
            return False

    except ValueError as e:
        print(f"Error: Invalid date/hour format: {e}")
        return False

    # Construct URL
    base_url = config['gpv_database']['base_url']
    hour_str = f"{int(hour):02d}"
    filename = f"MSM{date_str}{hour_str}S.nc"
    url = f"{base_url}{date_str}/{filename}"

    print(f"Checking file: {filename}")

    # Check if file exists
    exists, file_size = check_file_exists(url, config)
    if not exists:
        print(f"Error: File not found at {url}")
        return False

    print(f"File found: {get_file_size_mb(file_size)}")

    # Create save path (simple structure: data/raw/MSM*.nc)
    raw_data_dir = config['storage']['raw_data_dir']
    ensure_directory(raw_data_dir)

    save_path = os.path.join(raw_data_dir, filename)

    # Check if already downloaded
    if os.path.exists(save_path):
        existing_size = os.path.getsize(save_path)
        if existing_size == file_size:
            print(f"File already exists: {save_path}")
            return True

    # Clean up old files before downloading new one
    print("\nCleaning up old files...")
    deleted_count, freed_bytes = cleanup_old_files(raw_data_dir, keep_latest=False)
    if deleted_count > 0:
        print(f"Removed {deleted_count} old file(s), freed {get_file_size_mb(freed_bytes)}")

    # Download
    success = download_file(url, save_path, config)

    # Log
    log_path = os.path.join(config['storage']['log_dir'], 'download.log')
    if success:
        downloaded_size = os.path.getsize(save_path)
        log_download(log_path, url, True, downloaded_size)
    else:
        log_download(log_path, url, False, error="Download failed")

    return success


def run_cleanup(config):
    """
    Clean up old files, keeping only the latest

    Args:
        config: Configuration dictionary
    """
    raw_data_dir = config['storage']['raw_data_dir']

    print(f"\nCleaning up old files (keeping only latest)...")

    deleted_count, freed_bytes = cleanup_old_files(raw_data_dir, keep_latest=True)

    print(f"Cleanup complete:")
    print(f"  Files deleted: {deleted_count}")
    print(f"  Space freed: {get_file_size_mb(freed_bytes)}")


def main():
    """
    Main execution function
    """
    parser = argparse.ArgumentParser(
        description='Download GPV weather forecast data from Kyoto University database'
    )

    parser.add_argument(
        '--mode',
        choices=['auto', 'manual'],
        default='auto',
        help='Download mode: auto (latest) or manual (specific date/time)'
    )

    parser.add_argument(
        '--date',
        help='Date in YYYYMMDD format (required for manual mode)'
    )

    parser.add_argument(
        '--hour',
        type=int,
        help='Forecast hour: 0, 3, 6, 9, 12, 15, 18, or 21 (required for manual mode)'
    )

    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Run cleanup to delete old files'
    )

    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to config file (default: config/config.yaml)'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    print("=" * 60)
    print("GPV Weather Data Downloader")
    print("=" * 60)

    # Run cleanup if requested
    if args.cleanup:
        run_cleanup(config)
        if args.mode == 'auto' and not args.date:
            return

    # Download data
    if args.mode == 'auto':
        success = download_auto(config)
    else:
        if not args.date or args.hour is None:
            print("Error: --date and --hour are required for manual mode")
            parser.print_help()
            sys.exit(1)

        success = download_manual(config, args.date, args.hour)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
