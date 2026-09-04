# 概要

YouTubeのアニメOP/ED再生リストから動画情報を自動取得し、CSVへの一元管理および統計レポートの生成を自動化するツールです。
GitHub Actionsを利用して、毎日自動で最新データに更新されます。

## 機能
- **YouTube動画情報の自動取得 (GitHub Actions)**
  - 公開中の再生リストから動画のメタデータや指標を定期的に自動取得します。
  - 対象の再生リストは [サッチー🎧アニソン総合チャンネル](https://www.youtube.com/@SachiAnimeMusic) にて公開の[【アニソン】公式アニメOP/ED 2020年代](https://www.youtube.com/playlist?list=PLarZd9ydotoiR_D19VIlsX06GhvGo75Jo)です。
- **統計レポートの自動生成とWeb公開**
  - 収集したデータを集計し、自動でHTMLレポートを出力します。
  - 統計レポートは [統計レポート](https://SchiAnimeMusic.github.io/AnimeInfo/data/statistics_report.html) から確認できます。
- **ネットワークノード/エッジ形式のJSONデータ自動生成とWeb公開**
  - 収集したデータをもとに、自動でネットワークノード/エッジ形式のJSONデータを出力します。
  - Vis.js で可視化したページは[ネットワーク可視化ページ](https://SchiAnimeMusic.github.io/AnimeInfo/data/network_graph.html) から確認できます。
  - ページを開くと、投稿動画数が最も多いチャンネルとその投稿動画を初期表示します。
  - 上部の検索欄に動画タイトルまたはチャンネル名を入力すると、一致したノードと直接つながる関連動画・チャンネルだけを表示します。
  - サムネ/アイコンにカーソルを合わせると、タイトルがツールチップで表示されます。
  - クリックすると対応する YouTube ページを新しいタブで開きます。

#### 出力ファイル一覧

| ファイル | 説明 |
|---------|------|
| `anime_op_ed.csv` | 再生リストから取得した生データ |
| `channel_statistics.png` | チャンネル別の動画数・再生回数グラフ |
| `statistics_report.html` | インタラクティブなHTMLレポート（グラフ+テーブル） |
| `channel_statistics.csv` | 全チャンネルの統計データ |
| `data/network_data.json` | Vis.js などで利用できるネットワークノード/エッジ形式のJSONデータ |
| `data/network_graph.html` | `data/network_data.json` を読み込んで Vis.js で可視化する最小構成ページ |

#### 実行スケジュール

**毎日午前10時（UTC午前1時）** に自動実行されます。

## 免責事項

本ツールおよびWebページは個人が趣味で制作した非公式のものです。使用している動画タイトルや再生数、サムネイル、チャンネルアイコンなどのデータは、YouTube APIを利用して取得した一般に公開されている情報です。データの正確性には万全を期していますが、本ツールおよびWebページの利用により生じた損害について、制作者は一切の責任を負いません。また、著作権や肖像権に関して問題がある場合は、[サッチー🎧アニソン総合チャンネル](https://www.youtube.com/@SachiAnimeMusic)までご連絡ください。速やかに対応いたします。

## ライセンス

MIT License
