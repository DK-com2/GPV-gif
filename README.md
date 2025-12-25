# GPV Cloud Animation Web Application

自動更新機能付き雲量予測可視化Webアプリケーション - 京都大学のGPV (Grid Point Value) 気象予測データから雲量をアニメーション化して表示します。

## Overview

日本アルプスを中心とした山岳地域の雲量を3層（上層雲・中層雲・下層雲）で可視化し、2時間ごとに自動更新するWebアプリケーションです。登山やアウトドア活動の計画に役立ちます。

## Features

### Webアプリケーション
- **自動更新**: 2時間おきに最新データを自動ダウンロード・可視化
- **手動更新**: ボタンクリックで即座に最新データを取得可能
- **4種類のGIFアニメーション**:
  - 全層統合（赤: 上層雲、緑: 中層雲、青: 下層雲）
  - 下層雲のみ
  - 中層雲のみ
  - 上層雲のみ
- **山岳地域の可視化**: 北アルプス、中央アルプス、南アルプスの主要な山を表示
- **リアルタイムステータス**: 更新状態を30秒ごとに確認

### データ取得システム
- 京都大学GPVデータベースから最新予測データを自動取得
- リトライロジック付きダウンロード機能
- 古いファイルの自動クリーンアップ
- 詳細なログ記録

## Project Structure

```
GPV/
├── app.py                      # Flask Webアプリケーション (メイン)
├── data/
│   ├── raw/                    # ダウンロードされたNetCDFファイル
│   │   └── MSM*.nc             # 最新の予測ファイル
│   └── logs/                   # ダウンロードログ
├── scripts/
│   ├── download_gpv.py         # データダウンロードスクリプト
│   ├── generate_cloud_gif.py   # GIF生成スクリプト（関数化版）
│   ├── cloud_animation.py      # GIF生成スクリプト（オリジナル）
│   └── utils.py                # ユーティリティ関数
├── static/
│   └── images/                 # 生成されたGIFファイル
│       ├── cloud_all_layers.gif
│       ├── cloud_low_only.gif
│       ├── cloud_mid_only.gif
│       └── cloud_upper_only.gif
├── templates/
│   └── index.html              # Webページテンプレート
├── config/
│   └── config.yaml             # 設定ファイル
├── requirements.txt            # Python依存パッケージ
└── README.md                   # このファイル
```

## Quick Start

### 1. Install Dependencies

仮想環境を使用することを推奨します:

```bash
# 仮想環境の作成（初回のみ）
python -m venv venv

# 仮想環境の有効化
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# パッケージのインストール
pip install -r requirements.txt
```

主要なパッケージ:
- `Flask>=3.0.0` - Webフレームワーク
- `APScheduler>=3.10.0` - スケジューラー
- `xarray`, `netCDF4` - NetCDFデータ処理
- `matplotlib`, `cartopy` - 地図可視化
- `Pillow` - 画像処理
- `requests`, `pyyaml`, `tqdm` - ユーティリティ

### 2. Webアプリケーションの起動

```bash
# 仮想環境が有効化されていることを確認
python app.py
```

アプリが起動すると:
- 初回起動時: 自動的に最新データをダウンロード・GIF生成（数分かかります）
- ブラウザで `http://localhost:5000` にアクセス
- 2時間ごとに自動更新

### 3. 使い方

- **自動更新**: アプリを起動したまま放置すると2時間ごとに自動更新
- **手動更新**: Webページの「今すぐ更新」ボタンをクリック
- **状態確認**: ステータスインジケーターで更新状態を確認（30秒ごとに自動更新）

## Configuration

必要に応じて `config/config.yaml` を編集できます:

```yaml
gpv_database:
  base_url: "https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/latest/"
  forecast_hours: [0, 3, 6, 9, 12, 15, 18, 21]
  data_delay_hours: 2  # データ公開の遅延時間

storage:
  raw_data_dir: "./data/raw"
  log_dir: "./data/logs"

download:
  timeout: 60
  max_retries: 3
  retry_delay: 5
  user_agent: "WeatherApp/1.0 (Educational Purpose)"
  request_interval: 5
```

## 個別スクリプトの使用

### データダウンロードのみ

最新データをダウンロード:

```bash
python scripts/download_gpv.py --mode auto
```

特定の日時を指定:

```bash
python scripts/download_gpv.py --mode manual --date 20251224 --hour 3
```

### GIF生成のみ

既にダウンロード済みのNetCDFファイルからGIFを生成:

```bash
python scripts/generate_cloud_gif.py data/raw/MSM2025122403S.nc
```

または最新ファイルを自動検出:

```bash
python scripts/generate_cloud_gif.py
```

生成されるGIF:
- `static/images/cloud_all_layers.gif` - 全層統合
- `static/images/cloud_low_only.gif` - 下層雲のみ
- `static/images/cloud_mid_only.gif` - 中層雲のみ
- `static/images/cloud_upper_only.gif` - 上層雲のみ

## File Format

Downloaded files follow this naming convention:
- Format: `MSMYYYYMMDDhhS.nc`
- Example: `MSM2025122403S.nc`
  - `YYYYMMDD`: Date (2025-12-24)
  - `hh`: Forecast hour (03:00 UTC)
  - `S`: Surface level data

Typical file size: 150-200 MB per file

## Logging

Download logs are saved to `data/logs/download.log`:

```
2025-12-24 12:34:56 | SUCCESS | MSM2025122403S.nc | 189.2MB
2025-12-24 12:30:12 | FAILED  | MSM2025122400S.nc | Network timeout
```

## Error Handling

The script handles:
- Network timeouts (60 seconds)
- HTTP errors (404, 500, etc.)
- Connection failures
- Disk space issues
- File system errors

Failed downloads are automatically retried up to 3 times with 5-second delays.

## Data Source

- **Source**: Kyoto University Survivable Earth Research Institute
- **Database**: GPV (Grid Point Value) Latest Data
- **Model**: MSM (Meso-Scale Model)
- **Update Frequency**: Every 3 hours
- **Data Delay**: 1-2 hours after forecast time
- **Coverage**: Japan and surrounding regions

## 技術スタック

- **バックエンド**: Flask (Python Webフレームワーク)
- **スケジューラー**: APScheduler (バックグラウンド自動更新)
- **データ処理**: xarray, netCDF4 (気象データ処理)
- **可視化**: matplotlib, cartopy (地図・雲量の描画)
- **画像生成**: Pillow (GIFアニメーション作成)
- **フロントエンド**: HTML5, CSS3, JavaScript (レスポンシブデザイン)

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│              Flask Web Application                  │
│                   (app.py)                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │   APScheduler (Background Scheduler)         │  │
│  │   - Runs every 2 hours                       │  │
│  │   - Triggers download + GIF generation       │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │   Flask Routes                               │  │
│  │   - / (index page)                           │  │
│  │   - /status (API: current status)            │  │
│  │   - /update-now (API: manual trigger)        │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
           ↓                           ↓
    ┌──────────────┐          ┌─────────────────┐
    │ download_gpv │          │ generate_cloud_ │
    │     .py      │   →      │    gif.py       │
    └──────────────┘          └─────────────────┘
           ↓                           ↓
    ┌──────────────┐          ┌─────────────────┐
    │ data/raw/    │          │ static/images/  │
    │ MSM*.nc      │          │ cloud_*.gif     │
    └──────────────┘          └─────────────────┘
```

## Troubleshooting

### No files found

- Data may not be published yet (wait 1-2 hours after forecast time)
- Check network connection
- Verify URL is accessible: https://database.rish.kyoto-u.ac.jp/arch/jmadata/data/gpv/latest/

### Download timeout

- Large file size (189MB) may require longer timeout
- Adjust `timeout` in `config.yaml`
- Check internet connection speed

### Disk space error

- Each file is ~189MB
- Ensure sufficient disk space
- Run cleanup: `--cleanup`
- Reduce `retention_days` in config

### Permission errors

- Ensure write permissions for `data/` directory
- On Windows, run as administrator if needed
- On Linux, check file ownership: `chmod -R u+w data/`

## 表示内容

### 対象エリア
- **緯度**: 33.5°N - 37.5°N
- **経度**: 135.5°E - 140°E
- **主要地域**: 北アルプス、中央アルプス、南アルプス、富士山周辺

### 表示される山（一部）
- 北アルプス: 白馬岳、剱岳、立山、槍ヶ岳、穂高岳、乗鞍岳など
- 中央アルプス: 木曽駒ヶ岳、空木岳、御嶽山など
- 南アルプス: 北岳、間ノ岳、塩見岳、赤石岳、聖岳など
- その他: 富士山、八ヶ岳、伊吹山、白山など

### 雲量の見方
- **上層雲（赤）**: 高高度（6000m以上）の雲
- **中層雲（緑）**: 中高度（2000-6000m）の雲
- **下層雲（青）**: 低高度（2000m以下）の雲
- **濃さ**: 雲量の多さを表す（薄い→濃い = 少ない→多い）

## 今後の拡張可能性

- 降水量・積雪量の可視化
- 風速・風向の表示
- 特定の山のピンポイント予報
- スマートフォンアプリ化
- 通知機能（悪天候アラート）

## License

Educational purpose only. Please respect the data source's terms of use.

## Data Attribution

Data provided by:
**Research Institute for Sustainable Humanosphere, Kyoto University**
https://database.rish.kyoto-u.ac.jp/

## Contact

For issues or questions about this downloader system, please create an issue in the project repository.
