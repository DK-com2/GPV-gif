"""
Utility functions for GPV weather data downloader
"""
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


def ensure_directory(path):
    """
    Create directory if it doesn't exist

    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_size_mb(size_bytes):
    """
    Convert bytes to MB string

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string (e.g., "189.2MB")
    """
    if size_bytes is None:
        return "Unknown"
    return f"{size_bytes / (1024 * 1024):.1f}MB"


def parse_filename(filename):
    """
    Extract datetime information from MSM filename

    Args:
        filename: MSM filename (e.g., "MSM2025122403S.nc")

    Returns:
        datetime or None: Parsed datetime object, or None if parsing fails

    Example:
        >>> parse_filename("MSM2025122403S.nc")
        datetime.datetime(2025, 12, 24, 3, 0)
    """
    try:
        if not filename.startswith("MSM") or not filename.endswith("S.nc"):
            return None

        # Extract YYYYMMDDHH from MSM{YYYYMMDDHH}S.nc
        datetime_str = filename[3:13]

        year = int(datetime_str[0:4])
        month = int(datetime_str[4:6])
        day = int(datetime_str[6:8])
        hour = int(datetime_str[8:10])

        return datetime(year, month, day, hour)
    except (ValueError, IndexError):
        return None


def cleanup_old_files(directory, keep_latest=True):
    """
    Delete old NetCDF files, keeping only the latest one if keep_latest=True

    Args:
        directory: Directory to clean up
        keep_latest: If True, keep only the most recent file

    Returns:
        tuple: (deleted_count, freed_bytes)
    """
    if not os.path.exists(directory):
        return 0, 0

    deleted_count = 0
    freed_bytes = 0

    # Collect all .nc files with their timestamps
    nc_files = []
    for filename in os.listdir(directory):
        if not filename.endswith('.nc'):
            continue

        file_path = os.path.join(directory, filename)
        if not os.path.isfile(file_path):
            continue

        file_datetime = parse_filename(filename)
        if file_datetime:
            nc_files.append((file_datetime, filename, file_path))

    if not nc_files:
        return 0, 0

    # Sort by datetime (newest first)
    nc_files.sort(reverse=True, key=lambda x: x[0])

    # Delete all except the latest
    files_to_delete = nc_files[1:] if keep_latest else nc_files

    for _, filename, file_path in files_to_delete:
        try:
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            deleted_count += 1
            freed_bytes += file_size
            print(f"Deleted old file: {filename}")
        except OSError as e:
            print(f"Failed to delete {filename}: {e}")

    return deleted_count, freed_bytes


def get_utc_now():
    """
    Get current UTC time

    Returns:
        datetime: Current UTC datetime
    """
    return datetime.utcnow()


def get_forecast_times():
    """
    Get list of forecast hours (3-hour intervals)

    Returns:
        list: [0, 3, 6, 9, 12, 15, 18, 21]
    """
    return [0, 3, 6, 9, 12, 15, 18, 21]


def get_nearest_forecast_time(dt, delay_hours=2):
    """
    Get the most recent forecast time considering data delay

    Args:
        dt: Target datetime
        delay_hours: Expected delay in data publication

    Returns:
        datetime: Nearest available forecast datetime
    """
    forecast_hours = get_forecast_times()

    # Subtract delay to account for publication lag
    adjusted_dt = dt - timedelta(hours=delay_hours)

    # Find the most recent 3-hour mark
    current_hour = adjusted_dt.hour

    # Find largest forecast hour <= current_hour
    forecast_hour = 0
    for fh in reversed(forecast_hours):
        if fh <= current_hour:
            forecast_hour = fh
            break

    return adjusted_dt.replace(hour=forecast_hour, minute=0, second=0, microsecond=0)


def format_datetime_for_filename(dt):
    """
    Format datetime for MSM filename

    Args:
        dt: datetime object

    Returns:
        tuple: (YYYYMMDD, HH) for filename construction

    Example:
        >>> dt = datetime(2025, 12, 24, 3)
        >>> format_datetime_for_filename(dt)
        ('20251224', '03')
    """
    date_str = dt.strftime('%Y%m%d')
    hour_str = f"{dt.hour:02d}"
    return date_str, hour_str


def get_local_datetime_str():
    """
    Get current local datetime as formatted string

    Returns:
        str: Formatted datetime string (YYYY-MM-DD HH:MM:SS)
    """
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def check_disk_space(path, required_bytes):
    """
    Check if sufficient disk space is available

    Args:
        path: Directory path to check
        required_bytes: Required space in bytes

    Returns:
        bool: True if sufficient space available
    """
    try:
        stat = shutil.disk_usage(path)
        return stat.free >= required_bytes
    except OSError:
        return False
