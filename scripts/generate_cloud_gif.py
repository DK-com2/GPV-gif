"""
Cloud Animation GIF Generator
Refactored version for web app integration
"""
# Set matplotlib to non-GUI backend before importing pyplot
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for background processing

import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
import os
import glob
from PIL import Image
import shutil
from datetime import datetime
from matplotlib.patches import Polygon

# 日本語フォント設定
# Docker環境ではNoto Sans CJKを優先、Windows環境では従来のフォントを使用
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Noto Sans JP', 'MS Gothic', 'Yu Gothic', 'Meiryo', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def get_latest_nc_file(data_dir='./data/raw'):
    """
    Get the latest NetCDF file from data directory

    Args:
        data_dir: Directory containing NetCDF files

    Returns:
        str: Path to latest NetCDF file, or None if not found
    """
    nc_files = glob.glob(os.path.join(data_dir, 'MSM*.nc'))
    if not nc_files:
        return None

    # Sort by filename (contains datetime) and return latest
    return sorted(nc_files)[-1]


def format_time(time_value):
    """
    numpy.datetime64を日本時間(JST)の'YYYY-MM-DD HH:MM JST'形式にフォーマット
    GPVデータはUTC時刻で記録されているため、日本時間に変換して表示
    """
    import pandas as pd
    # UTCからJSTに変換
    dt_utc = pd.Timestamp(time_value).tz_localize('UTC')
    dt_jst = dt_utc.tz_convert('Asia/Tokyo')
    return dt_jst.strftime('%Y-%m-%d %H:%M JST')


def generate_cloud_gifs(nc_file_path, output_dir='./static/images'):
    """
    Generate cloud animation GIFs from NetCDF file

    Args:
        nc_file_path: Path to NetCDF file
        output_dir: Directory to save generated GIF files

    Returns:
        dict: Dictionary of generated GIF paths
    """
    print(f"Loading data from: {nc_file_path}")

    # データの読み込み
    ds = xr.open_dataset(nc_file_path)

    # 対象範囲を設定
    lat_min, lat_max = 33.5, 37.5
    lon_min, lon_max = 135.5, 140

    # データを範囲で切り出し
    print("Extracting target region...")
    region = ds.sel(lat=slice(lat_max, lat_min),
                    lon=slice(lon_min, lon_max))

    # 現在時刻未満のフレームを除外
    from datetime import datetime, timezone
    import pandas as pd
    import numpy as np

    # 現在時刻を日本時間(JST, UTC+9)で取得してからUTCに変換
    # ユーザーが見る時刻は日本時間なので、日本時間基準でフィルタリング
    jst_now = pd.Timestamp.now(tz='Asia/Tokyo')
    current_time_utc = jst_now.tz_convert('UTC').tz_localize(None)

    print(f"Current time (JST): {jst_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current time (UTC): {current_time_utc.strftime('%Y-%m-%d %H:%M:%S')}")

    # データのタイムスタンプを確認
    if len(region.time) > 0:
        first_time = pd.Timestamp(region.time.values[0])
        last_time = pd.Timestamp(region.time.values[-1])
        print(f"Data time range (UTC): {first_time} to {last_time}")

        # UTCからJSTに変換して表示
        first_time_jst = pd.Timestamp(first_time).tz_localize('UTC').tz_convert('Asia/Tokyo')
        last_time_jst = pd.Timestamp(last_time).tz_localize('UTC').tz_convert('Asia/Tokyo')
        print(f"Data time range (JST): {first_time_jst.strftime('%Y-%m-%d %H:%M')} to {last_time_jst.strftime('%Y-%m-%d %H:%M')}")

        # 現在時刻(UTC)以降のデータのみを残す
        time_values = pd.DatetimeIndex(region.time.values)
        future_mask = time_values >= current_time_utc

        if future_mask.sum() > 0:
            region = region.isel(time=future_mask)
            filtered_first = pd.Timestamp(region.time.values[0]).tz_localize('UTC').tz_convert('Asia/Tokyo')
            print(f"Filtered to {len(region.time)} future time steps")
            print(f"GIF will start from: {filtered_first.strftime('%Y-%m-%d %H:%M')} JST (past data excluded)")
        else:
            print("Warning: No future time steps found. Using all available data.")
    else:
        print("Warning: No time data available.")

    print(f"Time steps: {len(region.time)}")
    print(f"Region: Lat {lat_min}°-{lat_max}°, Lon {lon_min}°-{lon_max}°")

    # 主要な山の座標
    mountains = {
        # 北陸・信越
        '雨飾山': (36.9022, 137.9619),
        '焼山': (36.9200, 138.0361),
        '火打山': (36.9214, 138.0750),
        '妙高山': (36.8886, 138.1136),
        '高妻山': (36.7967, 138.0519),
        '白山': (36.1550, 136.7663),
        '荒島岳': (35.9250, 136.6014),

        # 北アルプス
        '白馬岳': (36.7586, 137.7580),
        '五竜岳': (36.6625, 137.7522),
        '鹿島槍ヶ岳': (36.6225, 137.7478),
        '剱岳': (36.6225, 137.6171),
        '立山': (36.5786, 137.6212),
        '薬師岳': (36.4689, 137.5450),
        '黒部五郎岳': (36.3917, 137.5403),
        '水晶岳': (36.4253, 137.6019),
        '鷲羽岳': (36.4022, 137.6033),
        '槍ヶ岳': (36.3421, 137.6477),
        '穂高岳': (36.2892, 137.6480),
        '常念岳': (36.3253, 137.7275),
        '笠ヶ岳': (36.3150, 137.5497),
        '焼岳': (36.2267, 137.5875),
        '乗鞍岳': (36.1064, 137.5539),

        # 中央・独立峰
        '御嶽山': (35.8939, 137.4803),
        '美ヶ原': (36.2256, 138.1072),
        '霧ヶ峰': (36.1033, 138.1983),
        '蓼科山': (36.1036, 138.2978),
        '八ヶ岳': (35.9708, 138.3685),
        '木曽駒ヶ岳': (35.7892, 137.8122),
        '空木岳': (35.7196, 137.8115),
        '恵那山': (35.4428, 137.5975),

        # 南アルプス
        '甲斐駒ヶ岳': (35.7522, 138.2367),
        '仙丈ヶ岳': (35.7214, 138.1831),
        '鳳凰山': (35.7022, 138.3039),
        '北岳': (35.6744, 138.2388),
        '間ノ岳': (35.6459, 138.2238),
        '塩見岳': (35.5739, 138.1831),
        '悪沢岳': (35.5011, 138.1828),
        '赤石岳': (35.4623, 138.1634),
        '聖岳': (35.4222, 138.1392),
        '光岳': (35.3375, 138.0831),

        # 東海・その他
        '富士山': (35.3606, 138.7274),
        '天城山': (34.8600, 138.9583),

        # 近畿
        '伊吹山': (35.4175, 136.4061),
        '武奈ヶ岳': (35.2608, 135.8953),
        '御在所岳': (35.0189, 136.4211),
        '藤原岳': (35.1742, 136.4442),
        '竜ヶ岳': (35.1436, 136.4258),
        '釈迦ヶ岳': (35.0864, 136.4331),
        '雨乞岳': (35.0319, 136.3881),
        '鎌ヶ岳': (35.0039, 136.4183),
        '入道ヶ岳': (34.9814, 136.4314),
        '大台ヶ原山': (34.1751, 136.1158),
        '大峰山': (34.2536, 135.9328),
    }

    # 山脈の範囲を定義
    mountain_ranges = {
        '北アルプス': {
            'coords': [
                (137.45, 36.8),  # 北西
                (137.85, 36.8),  # 北東
                (137.85, 36.0),  # 南東
                (137.45, 36.0),  # 南西
            ],
            'color': 'cyan',
            'alpha': 0.15
        },
        '中央アルプス': {
            'coords': [
                (137.70, 35.9),  # 北西
                (137.90, 35.9),  # 北東
                (137.90, 35.4),  # 南東
                (137.70, 35.4),  # 南西
            ],
            'color': 'magenta',
            'alpha': 0.15
        },
        '南アルプス': {
            'coords': [
                (138.00, 35.8),  # 北西
                (138.40, 35.8),  # 北東
                (138.40, 35.2),  # 南東
                (138.00, 35.2),  # 南西
            ],
            'color': 'yellow',
            'alpha': 0.15
        },
    }

    # 雲量レベル設定（0-100%を10段階に）
    levels = np.arange(10, 101, 10)

    # GIFの種類ごとの設定
    gif_configs = [
        {
            'name': 'all_layers',
            'title': '全層統合',
            'filename': 'cloud_all_layers.gif',
            'layers': ['low', 'mid', 'upper'],
            'legend': '赤: 上層雲（最上層）\n緑: 中層雲（中間層）\n青: 下層雲（最下層）\n△: 主要な山\n※上の層が優先表示'
        },
        {
            'name': 'low_only',
            'title': '下層雲のみ',
            'filename': 'cloud_low_only.gif',
            'layers': ['low'],
            'legend': '青: 下層雲\n（地表に近い雲）\n△: 主要な山'
        },
        {
            'name': 'mid_only',
            'title': '中層雲のみ',
            'filename': 'cloud_mid_only.gif',
            'layers': ['mid'],
            'legend': '緑: 中層雲\n（中高度の雲）\n△: 主要な山'
        },
        {
            'name': 'upper_only',
            'title': '上層雲のみ',
            'filename': 'cloud_upper_only.gif',
            'layers': ['upper'],
            'legend': '赤: 上層雲\n（高高度の雲）\n△: 主要な山'
        }
    ]

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    generated_files = {}

    # 各GIFタイプごとに処理
    for config in gif_configs:
        print(f"\n{'='*60}")
        print(f"Generating [{config['title']}] GIF...")
        print(f"{'='*60}")

        # 一時出力ディレクトリ作成
        temp_dir = f"cloud_temp_{config['name']}"
        os.makedirs(temp_dir, exist_ok=True)

        # 各時刻の画像を生成
        for t_idx in range(len(region.time)):
            print(f"  Creating frame {t_idx+1}/{len(region.time)}...")

            # 黒背景の図を作成
            fig = plt.figure(figsize=(14, 10), facecolor='black')
            ax = plt.axes(projection=ccrs.PlateCarree(), facecolor='black')

            # 地図設定
            ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

            # 山脈の範囲を表示（最下層）
            for range_name, range_data in mountain_ranges.items():
                coords = range_data['coords']
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]

                poly = Polygon(list(zip(lons, lats)),
                              facecolor=range_data['color'],
                              edgecolor=range_data['color'],
                              alpha=range_data['alpha'],
                              linewidth=2,
                              transform=ccrs.PlateCarree(),
                              zorder=1)
                ax.add_patch(poly)

                center_lon = sum(lons) / len(lons)
                center_lat = sum(lats) / len(lats)
                ax.text(center_lon, center_lat, range_name,
                       color=range_data['color'], fontsize=11, weight='bold',
                       ha='center', va='center', alpha=0.7,
                       transform=ccrs.PlateCarree(), zorder=2)

            # 経緯度線
            gl = ax.gridlines(draw_labels=True, linewidth=0.3, alpha=0.4, color='gray', zorder=3)
            gl.top_labels = False
            gl.right_labels = False
            gl.xlabel_style = {'color': 'white', 'size': 9}
            gl.ylabel_style = {'color': 'white', 'size': 9}

            # 各層の雲量データを取得
            upper_cloud = region['ncld_upper'].isel(time=t_idx).values
            mid_cloud = region['ncld_mid'].isel(time=t_idx).values
            low_cloud = region['ncld_low'].isel(time=t_idx).values

            # 選択された層を描画
            if 'low' in config['layers']:
                # 下層雲（青）
                cf_low = ax.contourf(region.lon, region.lat,
                                     low_cloud,
                                     levels=levels,
                                     colors=['#000033', '#000055', '#000077', '#0000AA', '#0000CC',
                                            '#0000EE', '#1111FF', '#3333FF', '#5555FF', '#7777FF'],
                                     alpha=0.8,
                                     transform=ccrs.PlateCarree(),
                                     zorder=4)

            if 'mid' in config['layers']:
                # 中層雲（緑）
                cf_mid = ax.contourf(region.lon, region.lat,
                                     mid_cloud,
                                     levels=levels,
                                     colors=['#003300', '#005500', '#007700', '#00AA00', '#00CC00',
                                            '#00EE00', '#11FF11', '#33FF33', '#55FF55', '#77FF77'],
                                     alpha=0.8,
                                     transform=ccrs.PlateCarree(),
                                     zorder=5)

            if 'upper' in config['layers']:
                # 上層雲（赤）
                cf_upper = ax.contourf(region.lon, region.lat,
                                       upper_cloud,
                                       levels=levels,
                                       colors=['#330000', '#550000', '#770000', '#AA0000', '#CC0000',
                                              '#EE0000', '#FF1111', '#FF3333', '#FF5555', '#FF7777'],
                                       alpha=0.8,
                                       transform=ccrs.PlateCarree(),
                                       zorder=6)

            # 海岸線と国境を最上層に（雲の上に表示）
            ax.add_feature(cfeature.COASTLINE, linewidth=1.2, edgecolor='white', alpha=0.9, zorder=20)
            ax.add_feature(cfeature.BORDERS, linewidth=0.7, edgecolor='white', alpha=0.7, zorder=20)

            # 山のマーカーを追加（白枠のみ、最上層）
            for mountain_name, (lat, lon) in mountains.items():
                # 範囲内の山だけ表示
                if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                    # 白枠の三角マーカー（塗りつぶしなし）
                    ax.plot(lon, lat, marker='^',
                            markerfacecolor='none',
                            markeredgecolor='white',
                            markeredgewidth=1.5,
                            markersize=7,
                            transform=ccrs.PlateCarree(), zorder=21)

            # タイトル（時刻のみ、フォーマット済み）
            time_str = format_time(region.time.isel(time=t_idx).values)
            ax.set_title(f'{config["title"]}\n{time_str}',
                         fontsize=15, color='white', pad=20, weight='bold')

            # 凡例を追加
            ax.text(0.02, 0.02, config['legend'],
                    transform=ax.transAxes,
                    fontsize=10,
                    color='white',
                    verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='black',
                             alpha=0.8, edgecolor='white', linewidth=1.5),
                    zorder=22)

            # 保存
            filename = f'{temp_dir}/cloud_{t_idx:03d}.png'
            plt.savefig(filename, dpi=150, bbox_inches='tight',
                        facecolor='black', edgecolor='none')
            plt.close()

        print(f"  Frames generated! Creating GIF...")

        # GIF作成
        image_files = sorted(glob.glob(f'{temp_dir}/cloud_*.png'))
        images = []

        for img_file in image_files:
            img = Image.open(img_file)
            images.append(img)

        # GIFとして保存
        output_path = os.path.join(output_dir, config['filename'])
        images[0].save(output_path,
                       save_all=True,
                       append_images=images[1:],
                       duration=500,  # 各フレーム500ms
                       loop=0)

        print(f"  GIF created: {output_path}")

        # 一時ディレクトリと画像を削除
        print(f"  Cleaning up temporary files...")
        shutil.rmtree(temp_dir)

        generated_files[config['name']] = output_path
        print(f"  ✓ {config['title']} completed!")

    print("\n" + "="*60)
    print("All GIF generation completed!")
    print("="*60)

    return generated_files


if __name__ == '__main__':
    # スタンドアロンで実行する場合
    import sys

    if len(sys.argv) > 1:
        nc_file = sys.argv[1]
    else:
        nc_file = get_latest_nc_file()

    if not nc_file or not os.path.exists(nc_file):
        print("Error: No NetCDF file found")
        sys.exit(1)

    generate_cloud_gifs(nc_file)
