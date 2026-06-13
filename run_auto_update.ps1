# アニメOP/ED情報を自動更新・統計レポート生成するスクリプト
# 使用方法: powershell -NoProfile -ExecutionPolicy Bypass -File run_auto_update.ps1

Set-Location $PSScriptRoot

# 仮想環境を有効化
& ".\.venv\Scripts\Activate.ps1"

# ログファイルのパス
$logFile = ".\data\auto_update.log"

# ログ出力関数
function Write-Log {
    param([string]$message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append -Encoding utf8
    Write-Host "[$timestamp] $message"
}

Write-Log "========== 自動更新処理開始 =========="

# 動画情報を取得
Write-Log "動画情報を取得中..."
python fetch_playlist.py
if ($LASTEXITCODE -ne 0) {
    Write-Log "エラー: 動画情報の取得に失敗しました (終了コード: $LASTEXITCODE)"
    exit 1
}

# 統計レポートを生成（グラフ表示なし）
Write-Log "統計レポートを生成中..."
python visualize_data.py --no-display
if ($LASTEXITCODE -ne 0) {
    Write-Log "エラー: 統計レポートの生成に失敗しました (終了コード: $LASTEXITCODE)"
    exit 1
}

Write-Log "========== 自動更新処理完了 =========="
exit 0
