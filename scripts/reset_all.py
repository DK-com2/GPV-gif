"""
Reset all data - Delete NetCDF files and GIF animations
"""
import os
import glob
import shutil

def get_file_size_mb(size_bytes):
    """Convert bytes to MB string"""
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def reset_all_data():
    """
    Delete all NetCDF files and GIF animations
    """
    print("="*60)
    print("Reset All Data - Clean Start")
    print("="*60)

    # Find NetCDF files
    nc_files = glob.glob('data/raw/*.nc')
    # Find GIF files
    gif_files = glob.glob('static/images/*.gif')
    # Find temporary directories
    temp_dirs = glob.glob('cloud_temp_*')

    print("\nFiles to be deleted:")
    print(f"\n  NetCDF files ({len(nc_files)}):")
    total_nc_size = 0
    for nc_file in nc_files:
        size = os.path.getsize(nc_file)
        total_nc_size += size
        print(f"    - {os.path.basename(nc_file)} ({get_file_size_mb(size)})")

    print(f"\n  GIF files ({len(gif_files)}):")
    total_gif_size = 0
    for gif_file in gif_files:
        size = os.path.getsize(gif_file)
        total_gif_size += size
        print(f"    - {os.path.basename(gif_file)} ({get_file_size_mb(size)})")

    if temp_dirs:
        print(f"\n  Temporary directories ({len(temp_dirs)}):")
        for temp_dir in temp_dirs:
            print(f"    - {temp_dir}")

    total_size = total_nc_size + total_gif_size
    print(f"\n  Total size: {get_file_size_mb(total_size)}")

    if not nc_files and not gif_files and not temp_dirs:
        print("\nNo files to delete. Already clean!")
        return

    print("\n" + "="*60)
    confirm = input("Delete all files and start fresh? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("Operation cancelled.")
        return

    # Delete NetCDF files
    deleted_nc = 0
    for nc_file in nc_files:
        try:
            os.remove(nc_file)
            deleted_nc += 1
            print(f"Deleted: {os.path.basename(nc_file)}")
        except OSError as e:
            print(f"Failed to delete {os.path.basename(nc_file)}: {e}")

    # Delete GIF files
    deleted_gif = 0
    for gif_file in gif_files:
        try:
            os.remove(gif_file)
            deleted_gif += 1
            print(f"Deleted: {os.path.basename(gif_file)}")
        except OSError as e:
            print(f"Failed to delete {os.path.basename(gif_file)}: {e}")

    # Delete temporary directories
    deleted_temp = 0
    for temp_dir in temp_dirs:
        try:
            shutil.rmtree(temp_dir)
            deleted_temp += 1
            print(f"Deleted directory: {temp_dir}")
        except OSError as e:
            print(f"Failed to delete {temp_dir}: {e}")

    print("\n" + "="*60)
    print("Reset complete!")
    print(f"  NetCDF files deleted: {deleted_nc}")
    print(f"  GIF files deleted: {deleted_gif}")
    print(f"  Temp directories deleted: {deleted_temp}")
    print(f"  Space freed: {get_file_size_mb(total_size)}")
    print("="*60)
    print("\nRun 'python app.py' to download fresh data and regenerate GIFs.")


if __name__ == '__main__':
    import sys

    # Check if running from project root
    if not os.path.exists('data/raw') or not os.path.exists('static/images'):
        print("Error: Must run from project root directory")
        print("Usage: python scripts/reset_all.py")
        sys.exit(1)

    reset_all_data()
