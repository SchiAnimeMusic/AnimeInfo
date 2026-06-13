# AnimeInfo

YouTubeの公式アニメOP/ED再生リストから動画情報を自動取得し、CSVに一元管理するツールです。

## 機能

- YouTubeの再生リストから動画情報を自動取得
- 動画ID、タイトル、説明、公開日時、チャンネル名、再生回数をCSVに保存
- 差分更新対応（実行するたびに新規動画のみ追加）
- 手動実行（CLIコマンド）と定期実行（スケジューラー）の両方に対応

## セットアップ

### 前提条件

- Python 3.8以上
- YouTube Data API v3のAPIキー

### ステップ1: YouTubeデータAPIの有効化とキーを取得

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. YouTubeデータAPI v3を有効化
4. APIキーを作成（認証情報 > APIキー）

### ステップ2: 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### ステップ3: ローカル実行時の環境変数設定

ローカル環境で手動実行する場合：

1. `.env.example` をコピーして `.env` を作成
```bash
cp .env.example .env
```

2. `.env` を編集してYouTubeAPIキーを設定
```
YOUTUBE_API_KEY=YOUR_API_KEY_HERE
```

または、環境変数を直接設定：
```bash
# Linux/macOS
export YOUTUBE_API_KEY=YOUR_API_KEY_HERE
python fetch_playlist.py

# Windows (PowerShell)
$env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python fetch_playlist.py
```

### ステップ4: GitHub Secretsの設定（GitHub Actions実行時）

このリポジトリをフォークして使用する場合、GitHub Actions で自動実行するには：

1. フォークしたリポジトリの **Settings** ページに移動
2. **Secrets and variables** > **Actions** をクリック
3. **New repository secret** をクリック
4. 名前: `YOUTUBE_API_KEY`、値: YouTubeデータAPI キーを入力
5. **Add secret** をクリック

これで、毎日UTC 2時（日本時間 11時）に自動的にデータが更新されます。

## 使い方

### 手動実行（ローカル）

環境変数が設定されている状態で実行：

```bash
python fetch_playlist.py
```

カスタム設定ファイルを使う場合（オプション）：
```bash
python fetch_playlist.py --config /path/to/config.json
```

### 自動実行（GitHub Actions）

このリポジトリをフォークして、GitHub Secrets に `YOUTUBE_API_KEY` を設定すると、毎日UTC 2時に自動実行されます。

手動で実行したい場合は、GitHub リポジトリの **Actions** タブから **Fetch Anime OP/ED** ワークフローを選択し、**Run workflow** をクリックしてください。

### 定期実行（ローカルサーバー）

Linux/macOS（crontab）で定期実行する場合：

```bash
crontab -e
```

以下を追加（毎日午前2時に実行）：
```
0 2 * * * cd /path/to/AnimeInfo && YOUTUBE_API_KEY=YOUR_KEY python fetch_playlist.py
```

Windows（タスクスケジューラー）で定期実行する場合：

1. タスクスケジューラーを起動
2. 基本タスクを作成
3. トリガー：実行頻度を設定（例：毎日午前2時）
4. 操作：以下を設定
   - プログラム：`python.exe`
   - 引数：`fetch_playlist.py`
   - 開始位置：`C:\path\to\AnimeInfo`
   - 環境変数：`YOUTUBE_API_KEY` を設定

## 出力ファイル

実行後、`data/anime_op_ed.csv` が生成されます。

CSVの列：
- `video_id`: YouTube動画ID
- `title`: 動画タイトル
- `description`: 説明文
- `published_at`: 公開日時（ISO 8601形式）
- `channel_name`: チャンネル名
- `view_count`: 再生回数

## トラブルシューティング

### 「YouTube APIキーが設定されていません」エラー

環境変数 `YOUTUBE_API_KEY` が設定されているか確認してください。

**ローカル実行時：**
- `.env` ファイルに `YOUTUBE_API_KEY=YOUR_KEY` が記載されているか確認
- または、環境変数を直接設定して実行

**GitHub Actions 実行時：**
- リポジトリの **Settings** > **Secrets and variables** > **Actions** から `YOUTUBE_API_KEY` が設定されているか確認

### 「再生リストが見つかりません」エラー

再生リストIDが正しいか確認してください。YouTube再生リストのURLから確認できます。
```
https://www.youtube.com/playlist?list=PLarZd9ydotojcNKocdU95YFqooKnF-w_p
                                           ↑ この部分がplaylist_id
```

### YouTubeデータAPIクォータエラー

YouTubeデータAPIは無料で1日あたり10,000ユニットのクォータが付与されます。このエラーが発生した場合は、翌日までお待ちください。

### 新規動画が検出されない

- 再生リストに新しい動画が追加されているか確認
- `data/anime_op_ed.csv` ファイルが存在し、正しくロードされているか確認
- 既存データとの重複チェックが正しく機能しているか確認

## ライセンス

MIT License