"""
GPV Cloud Animation Web Application
Flask + APScheduler for automated data updates
"""
import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import subprocess

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from generate_cloud_gif import generate_cloud_gifs, get_latest_nc_file

# Flask app initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = 'gpv-cloud-animation-secret-key'

# Global state
last_update_time = None
update_status = {
    'status': 'idle',
    'message': 'Application started',
    'last_update': None,
    'error': None
}


def update_data():
    """
    Scheduled task: Download latest data and generate GIFs
    This runs every 2 hours
    """
    global last_update_time, update_status

    print("\n" + "="*60)
    print(f"Starting scheduled update at {datetime.now()}")
    print("="*60)

    update_status['status'] = 'running'
    update_status['message'] = 'Downloading latest data...'

    try:
        # Step 1: Download latest GPV data
        print("Step 1: Downloading latest GPV data...")
        result = subprocess.run(
            [sys.executable, 'scripts/download_gpv.py', '--mode', 'auto'],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            error_msg = f"Download failed: {result.stderr}"
            print(error_msg)
            update_status['status'] = 'error'
            update_status['message'] = error_msg
            update_status['error'] = result.stderr
            return

        print("Download completed successfully!")

        # Step 2: Generate cloud GIFs
        print("Step 2: Generating cloud animation GIFs...")
        update_status['message'] = 'Generating GIF animations...'

        nc_file = get_latest_nc_file('./data/raw')

        if not nc_file:
            error_msg = "No NetCDF file found in data/raw directory"
            print(error_msg)
            update_status['status'] = 'error'
            update_status['message'] = error_msg
            update_status['error'] = error_msg
            return

        # Generate GIFs
        generated_files = generate_cloud_gifs(nc_file, output_dir='./static/images')

        print(f"Generated {len(generated_files)} GIF files:")
        for name, path in generated_files.items():
            print(f"  - {name}: {path}")

        # Update status
        last_update_time = datetime.now()
        update_status['status'] = 'success'
        update_status['message'] = f'Update completed at {last_update_time.strftime("%Y-%m-%d %H:%M:%S")}'
        update_status['last_update'] = last_update_time.strftime("%Y-%m-%d %H:%M:%S")
        update_status['error'] = None

        print("="*60)
        print("Update completed successfully!")
        print("="*60)

    except Exception as e:
        error_msg = f"Error during update: {str(e)}"
        print(error_msg)
        update_status['status'] = 'error'
        update_status['message'] = error_msg
        update_status['error'] = str(e)


# Create scheduler
scheduler = BackgroundScheduler()

# Schedule task to run every hour at 00 minutes (00:00, 01:00, 02:00, etc.)
from apscheduler.triggers.cron import CronTrigger
scheduler.add_job(
    func=update_data,
    trigger=CronTrigger(minute=0),  # Run at the top of every hour
    id='update_gpv_data',
    name='Update GPV data and generate GIFs',
    replace_existing=True
)

# Start scheduler
scheduler.start()

# Shut down scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())


@app.route('/')
def index():
    """
    Main page - Display cloud animation GIFs
    """
    gif_files = [
        {
            'name': 'all_layers',
            'title': '全層統合（赤: 上層雲、緑: 中層雲、青: 下層雲）',
            'filename': 'cloud_all_layers.gif'
        },
        {
            'name': 'low_only',
            'title': '下層雲のみ（青）',
            'filename': 'cloud_low_only.gif'
        },
        {
            'name': 'mid_only',
            'title': '中層雲のみ（緑）',
            'filename': 'cloud_mid_only.gif'
        },
        {
            'name': 'upper_only',
            'title': '上層雲のみ（赤）',
            'filename': 'cloud_upper_only.gif'
        }
    ]

    # Check if GIF files exist
    for gif in gif_files:
        gif_path = os.path.join('static', 'images', gif['filename'])
        gif['exists'] = os.path.exists(gif_path)

    return render_template('index.html',
                           gifs=gif_files,
                           last_update=update_status.get('last_update'),
                           status=update_status.get('status'))


@app.route('/status')
def status():
    """
    API endpoint - Get current update status
    """
    return jsonify(update_status)


if __name__ == '__main__':
    print("="*60)
    print("GPV Cloud Animation Web Application")
    print("="*60)
    print("Starting Flask server...")
    print("Access the app at: http://localhost:5000")
    print("Scheduled updates: Every hour at 00 minutes")
    print("="*60)

    # Run initial update if no GIFs exist
    if not os.path.exists('static/images/cloud_all_layers.gif'):
        print("\nNo existing GIFs found. Running initial update...")
        update_data()

    # Start Flask app
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
