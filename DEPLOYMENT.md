# GPV Cloud Animation - デプロイメントガイド

## 概要

このドキュメントでは、GPV雲アニメーションアプリケーションをDockerを使用してサーバーにデプロイする方法を説明します。

## システム要件

- Docker 20.10以上
- Docker Compose 1.29以上
- 最低2GBのRAM
- 最低10GBのディスク空き容量
- インターネット接続（GPVデータのダウンロード用）

## 事前準備

### 1. Dockerのインストール

サーバーにDockerとDocker Composeをインストールしてください。

**Ubuntu/Debianの場合:**
```bash
# Dockerのインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Composeのインストール
sudo apt-get update
sudo apt-get install docker-compose-plugin

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER
```

**CentOS/RHELの場合:**
```bash
# Dockerのインストール
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Dockerサービスの開始
sudo systemctl start docker
sudo systemctl enable docker

# 現在のユーザーをdockerグループに追加
sudo usermod -aG docker $USER
```

インストール後、一度ログアウトして再ログインしてください。

### 2. プロジェクトファイルの配置

プロジェクトをサーバーに転送します：

```bash
# ローカルマシンから
scp -r /path/to/GPV user@server:/home/user/

# または、gitリポジトリから
git clone <repository-url> /home/user/GPV
```

## デプロイ手順

### 1. ディレクトリ構造の確認

プロジェクトディレクトリに移動して、必要なディレクトリが存在することを確認：

```bash
cd /home/user/GPV

# 必要なディレクトリの作成
mkdir -p data/raw data/logs output static/images
```

### 2. 設定ファイルの確認

`config/config.yaml`を確認し、必要に応じて設定を調整します：

```bash
cat config/config.yaml
```

主要な設定項目：
- `gpv_database.base_url`: GPVデータベースのURL
- `gpv_database.forecast_hours`: 取得する予報時刻
- `storage.raw_data_dir`: データ保存ディレクトリ
- `download.timeout`: ダウンロードタイムアウト

### 3. Dockerイメージのビルド

```bash
docker compose build
```

初回ビルドには5-10分程度かかります。

### 4. アプリケーションの起動

```bash
# バックグラウンドで起動
docker compose up -d

# ログを表示しながら起動（デバッグ用）
docker compose up
```

### 5. 動作確認

```bash
# コンテナの状態確認
docker compose ps

# ログの確認
docker compose logs -f

# アプリケーションのステータス確認
curl http://localhost:5000/status
```

ブラウザで`http://<サーバーIP>:5000`にアクセスして、アプリケーションが動作していることを確認します。

## 運用

### ログの確認

```bash
# アプリケーションログ
docker compose logs -f gpv-app

# 最新100行のログを表示
docker compose logs --tail=100 gpv-app

# ダウンロードログ
cat data/logs/download.log
```

### コンテナの管理

```bash
# 停止
docker compose stop

# 起動
docker compose start

# 再起動
docker compose restart

# 完全停止と削除
docker compose down

# イメージの再ビルドと再起動
docker compose up -d --build
```

### データの確認

```bash
# ダウンロードされたNetCDFファイル
ls -lh data/raw/

# 生成されたGIFファイル
ls -lh static/images/

# ログファイル
tail -f data/logs/download.log
```

### 手動更新

コンテナ内でスクリプトを実行して手動更新：

```bash
docker compose exec gpv-app python scripts/manual_update.py
```

## 自動更新スケジュール

アプリケーションは以下のスケジュールで自動的にデータを更新します：

- **頻度**: 毎時00分（00:00, 01:00, 02:00...）
- **処理内容**:
  1. 最新のGPVデータをダウンロード
  2. 雲アニメーションGIFを生成
  3. 古いファイルを削除（最新のみ保持）

スケジュールは`app.py`の以下の部分で設定されています：

```python
scheduler.add_job(
    func=update_data,
    trigger=CronTrigger(minute=0),  # 毎時00分
    id='update_gpv_data',
    name='Update GPV data and generate GIFs',
    replace_existing=True
)
```

## リバースプロキシの設定（推奨）

本番環境では、NginxなどのリバースプロキシでFlaskアプリケーションを公開することを推奨します。

### Nginxの設定例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # GIFファイルのキャッシュ設定
    location /static/ {
        proxy_pass http://localhost:5000/static/;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
}
```

### SSL/TLS設定（Let's Encrypt）

```bash
# Certbotのインストール
sudo apt-get install certbot python3-certbot-nginx

# SSL証明書の取得
sudo certbot --nginx -d your-domain.com

# 自動更新の設定
sudo systemctl enable certbot.timer
```

## トラブルシューティング

### コンテナが起動しない

```bash
# ログを確認
docker compose logs gpv-app

# コンテナの詳細情報を確認
docker compose ps -a

# イメージの再ビルド
docker compose build --no-cache
docker compose up -d
```

### ダウンロードが失敗する

```bash
# ネットワーク接続を確認
docker compose exec gpv-app curl -I http://database.rish.kyoto-u.ac.jp/

# 手動でダウンロードテスト
docker compose exec gpv-app python scripts/download_gpv.py --mode auto

# タイムアウト設定を増やす（config/config.yaml）
download:
  timeout: 300  # 60から300に増やす
```

### GIF生成が失敗する

```bash
# NetCDFファイルの存在確認
docker compose exec gpv-app ls -lh data/raw/

# 手動でGIF生成
docker compose exec gpv-app python scripts/generate_cloud_gif.py

# 依存パッケージの確認
docker compose exec gpv-app python -c "import xarray, matplotlib, cartopy"
```

### ディスク容量不足

```bash
# Dockerの不要なデータを削除
docker system prune -a

# 古いNetCDFファイルを手動削除
rm -f data/raw/MSM*.nc

# ログファイルのローテーション
> data/logs/download.log
```

## システムサービスとしての登録（オプション）

Dockerコンテナをsystemdサービスとして登録することで、サーバー起動時に自動起動できます。

### systemdサービスファイルの作成

```bash
sudo nano /etc/systemd/system/gpv-cloud-animation.service
```

```ini
[Unit]
Description=GPV Cloud Animation Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/GPV
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

### サービスの有効化

```bash
sudo systemctl daemon-reload
sudo systemctl enable gpv-cloud-animation.service
sudo systemctl start gpv-cloud-animation.service

# ステータス確認
sudo systemctl status gpv-cloud-animation.service
```

## バックアップ

重要なデータのバックアップ：

```bash
# バックアップディレクトリの作成
mkdir -p ~/gpv-backups

# データのバックアップ
tar czf ~/gpv-backups/gpv-data-$(date +%Y%m%d).tar.gz \
    data/ config/ static/

# 定期的なバックアップ（cron設定）
crontab -e
```

cron設定例（毎日午前3時にバックアップ）：

```cron
0 3 * * * cd /home/user/GPV && tar czf ~/gpv-backups/gpv-data-$(date +\%Y\%m\%d).tar.gz data/ config/ static/
```

## アップデート手順

アプリケーションを更新する場合：

```bash
# 新しいコードを取得
cd /home/user/GPV
git pull  # または新しいファイルを転送

# コンテナを停止
docker compose down

# イメージを再ビルド
docker compose build

# 再起動
docker compose up -d

# ログで動作確認
docker compose logs -f
```

## パフォーマンスチューニング

### メモリ制限の設定

`docker-compose.yml`にメモリ制限を追加：

```yaml
services:
  gpv-app:
    # ... 既存の設定 ...
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 1G
```

### ログローテーション

Dockerのログローテーション設定：

```yaml
services:
  gpv-app:
    # ... 既存の設定 ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## セキュリティ考慮事項

1. **ファイアウォール設定**: 必要なポートのみ開放
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Dockerソケットの保護**: 不要なユーザーのdockerグループからの削除

3. **定期的なアップデート**: Dockerイメージとシステムパッケージの更新
   ```bash
   docker compose pull
   docker compose up -d
   sudo apt-get update && sudo apt-get upgrade
   ```

## サポート

問題が発生した場合は、以下の情報を収集してください：

1. Dockerバージョン: `docker --version`
2. Docker Composeバージョン: `docker compose version`
3. コンテナログ: `docker compose logs gpv-app`
4. システムログ: `journalctl -u gpv-cloud-animation.service`
5. ディスク容量: `df -h`
6. メモリ使用量: `free -h`
