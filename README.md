# AnimeInfo

YouTubeの公式アニメOP/ED再生リストから動画情報を自動取得し、CSVに一元管理するツールです。

## ディレクトリ構造

```
.
├── README.md              # このファイル
├── requirements.txt       # Python依存パッケージ
├── .env.example          # 環境変数テンプレート
├── scripts/              # Pythonスクリプト
│   ├── fetch_playlist.py     # 再生リスト取得スクリプト
│   └── visualize_data.py     # 統計レポート生成スクリプト
├── docs/                 # ドキュメント
│   └── config.example.json   # 設定ファイルテンプレート
├── data/                 # 出力データ（Git追跡対象外）
│   ├── anime_op_ed.csv
│   ├── channel_statistics.png
│   ├── channel_statistics.csv
│   └── statistics_report.html
└── .github/workflows/    # GitHub Actions設定
    └── auto-update.yml
```

## 機能

- YouTubeの再生リストから動画情報を自動取得
- 動画ID(ハイパーリンク)、タイトル、公開日時、チャンネル名、再生回数をCSVに保存
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

### ステップ2: 仮想環境を作成して依存パッケージをインストール （推奨）

プロジェクトごとに仮想環境を作成して依存関係を隔離することを推奨します。

PowerShell (Windows) の例:

```powershell
# プロジェクトルートで一度だけ実行
py -3.11 -m venv .venv

# 仮想環境を有効化
.\.venv\Scripts\Activate.ps1

# pip とビルドツールを最新版に更新
python -m pip install -U pip setuptools wheel

# 依存関係をインストール
python -m pip install -r requirements.txt
```

他のシェル/OS での有効化方法：

- CMD (Windows):

```
.\.venv\Scripts\activate.bat
```
- Git Bash / WSL / macOS / Linux:

```bash
source .venv/bin/activate
```

仮想環境が有効化されているかは `python` の実行ファイルや `pip` のパスで確認できます。例:

```bash
python -c "import sys; print(sys.executable)"
pip --version
```

既に `.venv` が作成済みであれば、有効化してから `python -m pip install -r requirements.txt` を実行してください。

（仮想環境を使わない場合は従来どおり `pip install -r requirements.txt` を実行できますが、システム環境を汚す可能性があるため推奨しません）

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
python scripts/fetch_playlist.py

# Windows (PowerShell)
$env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py
```

※ローカルで仮想環境を使っている場合は、上の `python` を実行する前に仮想環境を有効化してください。例（PowerShell、プロジェクトルートで）：

```powershell
.\.venv\Scripts\Activate.ps1
$env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py
```

## 使用方法

### 動画情報の取得と更新

```bash
# 仮想環境を有効化（前提）
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# または Linux/macOS/WSL:
source .venv/bin/activate

# APIキーを設定してスクリプトを実行
# Windows (PowerShell):
$env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py

# または Linux/macOS:
export YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py
```

実行すると、再生リストから新規動画を取得して `data/anime_op_ed.csv` に追加されます。

### 統計情報の可視化とレポート生成

チャンネル毎の動画数と合計再生回数をグラフで表示し、レポートを生成します。

#### インタラクティブモード（グラフ表示あり）
```bash
# 仮想環境を有効化（前提）
python scripts/visualize_data.py
```

**生成される出力:**
- **PNG グラフ**: `data/channel_statistics.png`
- **HTML レポート**: `data/statistics_report.html` （ブラウザで表示可能）
- **統計 CSV**: `data/channel_statistics.csv` （Excel等で確認可能）
- **ターミナル出力**: TOP 20 の詳細情報と全体統計

#### バッチ処理モード（グラフ表示なし、自動実行向け）
```bash
python scripts/visualize_data.py --no-display
```

#### 出力ファイル一覧

| ファイル | 説明 |
|---------|------|
| `channel_statistics.png` | チャンネル別の動画数・再生回数グラフ |
| `statistics_report.html` | インタラクティブなHTMLレポート（グラフ+テーブル） |
| `channel_statistics.csv` | 全チャンネルの統計データ |

### 自動実行スケジュール設定

GitHub Actions を使用して、定期的に自動実行できます。

### GitHub Actions の有効化と設定

1. **このリポジトリをフォークまたはクローン**

2. **GitHub Secrets に YouTube API キーを登録**
   - リポジトリの **Settings** → **Secrets and variables** → **Actions** に移動
   - **New repository secret** をクリック
   - 名前: `YOUTUBE_API_KEY`
   - 値: YouTube Data API のキーを入力
   - **Add secret** をクリック

3. **GitHub Actions を有効化**
   - リポジトリの **Actions** タブを確認
   - ワークフロー「AnimeInfo Auto Update」が表示されていることを確認
   - 自動的に有効状態になります
   - **古いワークフローがある場合は削除してください**（`fetch-anime-op-ed.yml` など）

#### 実行スケジュール

デフォルトでは **毎日午前10時（UTC午前1時）** に自動実行されます。

スケジュール変更は、`.github/workflows/auto-update.yml` の `cron` 値を編集：

```yaml
on:
  schedule:
    - cron: '0 1 * * *'  # 毎日 01:00 UTC (=午前10時JST)
```

**cron 表記例:**
- `0 1 * * *` - 毎日午前1時UTC（午前10時JST）
- `0 */6 * * *` - 6時間ごと
- `0 10 * * MON` - 毎週月曜午前10時UTC

#### 手動実行

GitHub Actions ページから、ワークフロー「AnimeInfo Auto Update」を選択し、**Run workflow** をクリックするだけで即座に実行できます。

#### 実行内容（統合ワークフロー）

**AnimeInfo Auto Update** ワークフロー（`.github/workflows/auto-update.yml`）では以下を実行します：

1. ✅ 再生リストから動画情報を取得 (`fetch_playlist.py`)
2. ✅ 統計レポート生成 (`visualize_data.py --no-display`)
   - PNG グラフ
   - HTML レポート
   - 統計 CSV
3. ✅ 変更を自動コミット・プッシュ

**注意**: 複数のワークフローが存在する場合、API 呼び出しが重複します。古いワークフロー（`fetch-anime-op-ed.yml` など）は削除してください。

#### 実行結果の確認

- **Actions** タブで実行履歴と結果ログを確認可能
- 成功時は、自動で `data/` フォルダ内のファイルが更新されリポジトリに反映
- リポジトリのコミット履歴に「auto-update anime data and reports」という自動コミットが記録

---

## ローカル実行（開発・テスト用）

### 手動実行

```bash
# 仮想環境を有効化
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# または Linux/macOS:
source .venv/bin/activate

# APIキーを設定して実行
# Windows (PowerShell):
$env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py

# または Linux/macOS:
export YOUTUBE_API_KEY="YOUR_API_KEY_HERE"
python scripts/fetch_playlist.py
```

### 統計レポートの生成

```bash
python scripts/visualize_data.py
```

### ローカルでの定期実行（ローカル開発環境のみ）

**注意**: GitHub Actions を使用する場合はこの設定は不要です。

**Windows PowerShell** で定期実行する場合（スクリプト例）：

```powershell
$script = @"
cd C:\Users\MNS\AnimeInfo
.\.venv\Scripts\Activate.ps1
`$env:YOUTUBE_API_KEY='YOUR_API_KEY_HERE'
python scripts/fetch_playlist.py
python scripts/visualize_data.py --no-display
"@

$trigger = New-ScheduledTaskTrigger -Daily -At 2am
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$script`""
Register-ScheduledTask -TaskName "AnimeInfo_AutoUpdate" -Trigger $trigger -Action $action -Description "アニメOP/ED情報の自動更新と統計レポート生成"
```

**Linux/macOS** で cron を使用する場合：

```bash
crontab -e

# 毎日午前2時に実行する場合
0 2 * * * cd /path/to/AnimeInfo && source .venv/bin/activate && YOUTUBE_API_KEY="YOUR_API_KEY_HERE" python scripts/visualize_data.py --no-display
```

---

## トラブルシューティング

### YouTube API キーが見つからない場合

```
ERROR - YouTube APIキーが設定されていません
```

**解決方法：**
- 環境変数 `YOUTUBE_API_KEY` を設定してください
- `.env` ファイルがある場合、中身を確認してください

### GitHub Actions ワークフローが失敗する場合

1. **Secrets が設定されているか確認**
   - Settings > Secrets and variables > Actions で `YOUTUBE_API_KEY` が登録されているか確認

2. **実行ログを確認**
   - Actions タブからワークフロー実行履歴を確認
   - エラーメッセージを確認して対応

3. **API割り当て量超過**
   - YouTube API の割り当てが超過している可能性
   - Google Cloud Console でAPI使用状況を確認

---

## ライセンス

MIT License
