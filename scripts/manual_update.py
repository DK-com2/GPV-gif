"""
Manual Update Script - Download latest data and regenerate GIFs
"""
import os
import sys
import subprocess

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from generate_cloud_gif import generate_cloud_gifs, get_latest_nc_file


def run_update():
    """
    Manually trigger data download and GIF generation
    """
    print("="*60)
    print("Manual Update - GPV Cloud Animation")
    print("="*60)

    # Step 1: Download latest GPV data
    print("\nStep 1/2: Downloading latest GPV data...")
    print("-"*60)

    try:
        result = subprocess.run(
            [sys.executable, 'scripts/download_gpv.py', '--mode', 'auto'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )

        print(result.stdout)

        if result.returncode != 0:
            print("Error during download:")
            print(result.stderr)
            print("\nUpdate failed at download step.")
            return False

        print("Download completed successfully!")

    except subprocess.TimeoutExpired:
        print("Error: Download timed out (exceeded 5 minutes)")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

    # Step 2: Generate cloud GIFs
    print("\n" + "="*60)
    print("Step 2/2: Generating cloud animation GIFs...")
    print("-"*60)

    try:
        # Find latest NetCDF file
        nc_file = get_latest_nc_file('./data/raw')

        if not nc_file:
            print("Error: No NetCDF file found in data/raw directory")
            print("Please ensure download was successful.")
            return False

        print(f"Using data file: {os.path.basename(nc_file)}")

        # Generate GIFs
        generated_files = generate_cloud_gifs(nc_file, output_dir='./static/images')

        print("\n" + "="*60)
        print("GIF Generation Complete!")
        print("-"*60)
        print(f"Generated {len(generated_files)} GIF files:")
        for name, path in generated_files.items():
            file_size = os.path.getsize(path) / (1024 * 1024)
            print(f"  - {os.path.basename(path)} ({file_size:.1f} MB)")

        print("="*60)
        print("Update completed successfully!")
        print("="*60)
        print("\nYou can now view the updated animations at:")
        print("  http://localhost:5000")
        print("\nOr open the GIF files directly from static/images/")

        return True

    except Exception as e:
        print(f"\nError during GIF generation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main execution
    """
    # Check if running from project root
    if not os.path.exists('scripts/download_gpv.py'):
        print("Error: Must run from project root directory")
        print("Usage: python scripts/manual_update.py")
        sys.exit(1)

    # Run update
    success = run_update()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
