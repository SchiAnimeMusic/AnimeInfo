@echo off
REM アニメOP/ED情報を自動更新・統計レポート生成するスクリプト

cd /d "%~dp0"

REM 仮想環境を有効化
call .venv\Scripts\activate.bat

REM APIキーを環境変数から取得（設定済みの場合）
REM $env:YOUTUBE_API_KEY="YOUR_API_KEY_HERE"

REM 動画情報を取得
echo [%date% %time%] 動画情報を取得中...
python fetch_playlist.py
if errorlevel 1 (
    echo エラー: 動画情報の取得に失敗しました
    pause
    exit /b 1
)

REM 統計レポートを生成（グラフ表示なし）
echo [%date% %time%] 統計レポートを生成中...
python visualize_data.py --no-display
if errorlevel 1 (
    echo エラー: 統計レポートの生成に失敗しました
    pause
    exit /b 1
)

echo [%date% %time%] 処理完了
exit /b 0
