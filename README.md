# 概要

YouTubeのアニメOP/ED再生リストから動画情報を自動取得し、CSVへの一元管理および統計レポートの生成を自動化するツールです。
GitHub Actionsを利用して、毎日自動で最新データに更新されます。

## ディレクトリ構造

```
.
├── README.md              # このファイル
├── requirements.txt       # Python依存パッケージ
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

- YouTubeの再生リストから動画情報を自動取得(GitHub Actions)
- 動画ID(ハイパーリンク)、タイトル、公開日時、チャンネル名、再生回数をCSV形式で保存
- チャンネルの統計データをCSV/HTML/PNG形式でそれぞれ保存

#### 出力ファイル一覧

| ファイル | 説明 |
|---------|------|
| `channel_statistics.png` | チャンネル別の動画数・再生回数グラフ |
| `statistics_report.html` | インタラクティブなHTMLレポート（グラフ+テーブル） |
| `channel_statistics.csv` | 全チャンネルの統計データ |

#### 実行スケジュール

**毎日午前10時（UTC午前1時）** に自動実行されます。

---

## ライセンス

MIT License
