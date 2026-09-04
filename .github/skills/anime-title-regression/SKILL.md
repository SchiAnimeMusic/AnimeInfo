---
name: anime-title-regression
description: "アニメ動画タイトルのシリーズ抽出を変更するとき、特殊なYouTube動画タイトルを確認するとき、またはパーサー変更前後でシリーズ分類が変わっていないことを検証するときに使う。"
---

# アニメタイトル回帰評価

YouTubeのアニメ動画タイトルからシリーズ情報を抽出する処理を変更したとき、特殊なタイトルをまとめて評価し、変更前後で意図しない分類差分がないことを確認する。対象実装は `scripts/fetch_playlist.py` の `_extract_series_metadata` と `_normalize_series_key` である。

## 評価の対象

固定ケースでは、少なくとも次の入力形式を含める。

- `TVアニメ『作品名』`、`アニメ「作品名」`、`【作品名】`
- `|` / `｜` で区切られた作品名
- `第12話`、`#12`、`第2期`、`Season 3`、`前期`、`後期`
- `ノンクレジット`、`映像`、`ムービー`、`主題歌`、曲名、歌手名の混在
- `OP`、`ED`、`オープニング`、`エンディング`、`挿入歌`、`MV`、スペシャル
- 日本語・英語表記、全角記号、Unicode NFKCで同一視すべき表記
- 作品名が説明にだけ存在する動画
- 同一作品の本編、続編、劇場版、特殊EDを同一シリーズへ関連付けるケース
- 独立作品・スピンオフを誤って本編へ統合しないケース
- シリーズ名を抽出できない関連動画

評価データは `assets/title_cases.json` に追加する。既存の実データで発生した不具合は、再発防止ケースとして必ず固定する。

## 変更前後の比較手順

1. 作業開始時に、現在の抽出器と固定ケースの結果を `before.json` として保存する。
2. 抽出処理を変更する。
3. 同じ入力・同じ順序で再実行し、`after.json` を作る。APIアクセスや再生数取得は行わない。
4. `series_name`、`series_key`、`anime_key`、`tag`、`segment_label`、`priority_order` をケース単位で比較する。
5. 差分があれば、意図した変更か回帰かを判定する。意図しない差分は修正してから再実行する。
6. `anime_key == series_key`、空でないキー、`tag` と `segment_label` の対応も検査する。

実行用の最小スクリプト例:

```python
import json
import sys
from types import ModuleType

# fetch_playlist.py のAPI依存を読み込み時だけスタブ化する。
api = ModuleType('googleapiclient')
discovery = ModuleType('googleapiclient.discovery')
errors = ModuleType('googleapiclient.errors')
discovery.build = lambda *args, **kwargs: None
errors.HttpError = Exception
api.discovery = discovery
api.errors = errors
sys.modules.update({
    'google': ModuleType('google'),
    'googleapiclient': api,
    'googleapiclient.discovery': discovery,
    'googleapiclient.errors': errors,
})

from scripts.fetch_playlist import PlaylistFetcher

fetcher = PlaylistFetcher.__new__(PlaylistFetcher)
with open('.github/skills/anime-title-regression/assets/title_cases.json', encoding='utf-8') as file:
    cases = json.load(file)

def evaluate():
    results = []
    for case in cases:
        metadata = fetcher._extract_series_metadata(
            case['title'], case.get('description', '')
        )
        result = {
            'id': case['id'],
            'series_name': metadata['series_name'],
            'series_key': metadata['series_key'],
            'anime_key': metadata['anime_key'],
            'tag': metadata['tag'],
            'segment_label': metadata['segment_label'],
            'priority_order': metadata['priority_order'],
        }
        expected = case['expected']
        for field, value in expected.items():
            if result[field] != value:
                raise AssertionError(
                    f"{case['id']}: {field}: {result[field]!r} != {value!r}"
                )
        if result['anime_key'] != result['series_key']:
            raise AssertionError(f"{case['id']}: anime_key and series_key differ")
        results.append(result)
    return results

with open(sys.argv[1], 'w', encoding='utf-8') as file:
    json.dump(evaluate(), file, ensure_ascii=False, indent=2)
    file.write('\n')
```

`before.json` と `after.json` は同じケースIDで比較する。比較はJSON全体の文字列ではなく、ケースIDと評価フィールドの構造化値で行い、JSONの整形差分を無視する。

## 実データの整合性検査

固定ケースが通った後、必要に応じて `data/anime_op_ed.csv` と `data/network_data.json` も検査する。

- 同一シリーズの動画で `series_key` と `anime_key` が一致する。
- CSVの動画IDとJSONの動画ノードIDが対応する。
- 動画ノードとエッジの `series_key`、`tag`、`season_order`、`priority_order` がCSVと一致する。
- `season_order` はタイトル中の第N期ではなく、`published_at` の昇順で連番になる。
- スピンオフや判定不能動画を、名前が似ている本編へ自動統合しない。

## 判定基準

- 期待値を変更する場合は、タイトル抽出の仕様変更理由をケースの近くに記録する。
- 単に実データへ合わせて期待値を更新しない。変更前後の差分が意図したものか確認する。
- 新しい正規化例を追加したら、同じ作品の既存表記、OP/EDの両方、説明補完のケースを最低1件ずつ再評価する。
- 失敗時は、まず `_extract_series_metadata` の候補抽出、装飾除去、正規化キー生成のどの段階で差が生じたかを特定する。
- APIキーやYouTube APIを使わず、タイトルと説明だけで再現可能な評価にする。
