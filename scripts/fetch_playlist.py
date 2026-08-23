#!/usr/bin/env python3
"""
YouTube再生リストからアニメOP/ED情報を取得し、CSVに保存するスクリプト
"""

import json
import os
import sys
import csv
import math
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import logging

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# .env ファイルを読み込む
load_dotenv()

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlaylistFetcher:
    def __init__(self, config_path=None):
        api_key = self._load_api_key()
        self.config = self._load_config(config_path)
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.output_csv = self.config['output_csv_path']
        self.output_network_json = self.config['output_network_json_path']

        self.nodes = {}  # IDをキーとするノードの辞書
        self.edges = []  # エッジのリスト
        self._node_id_counter = 0 # ノードIDのカウンター

    @staticmethod
    def _load_api_key():
        """環境変数からYouTube APIキーを読み込む"""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            logger.error('YouTube APIキーが設定されていません')
            logger.error('環境変数 YOUTUBE_API_KEY を設定してください')
            logger.error('ローカル実行時は .env ファイルに YOUTUBE_API_KEY=YOUR_KEY を記載してください')
            sys.exit(1)
        return api_key

    @staticmethod
    def _load_config(config_path):
        """設定ファイルを読み込む（オプション）"""
        if config_path is None:
            # デフォルト設定を返す
            return {
                'playlist_id': 'PLO8ZpNNZxVSA',
                'output_csv_path': './data/anime_op_ed.csv',
                'output_network_json_path': './data/network_data.json',
                'timezone': 'Asia/Tokyo'
            }

        if not os.path.exists(config_path):
            logger.warning(f'設定ファイルが見つかりません: {config_path}')
            logger.warning('デフォルト設定を使用します')
            return {
                'playlist_id': 'PLO8ZpNNZxVSA',
                'output_csv_path': './data/anime_op_ed.csv',
                'output_network_json_path': './data/network_data.json',
                'timezone': 'Asia/Tokyo'
            }

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # configにoutput_network_json_pathがない場合は追加
            if 'output_network_json_path' not in config:
                config['output_network_json_path'] = './data/network_data.json'
            return config
        except json.JSONDecodeError as e:
            logger.error(f'設定ファイルのパースに失敗しました: {e}')
            sys.exit(1)

    def fetch_playlist_items(self):
        """再生リストから全動画IDを取得"""
        all_videos = []
        next_page_token = None

        while True:
            try:
                request = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=self.config['playlist_id'],
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response.get('items', []):
                    video_id = item['contentDetails']['videoId']
                    all_videos.append(video_id)

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        logger.info(f'再生リストから {len(all_videos)} 個の動画を取得しました')
        return all_videos

    def _get_next_node_id(self):
        self._node_id_counter += 1
        return self._node_id_counter

    def _calculate_node_size(self, node_type, metric_value):
        """人気度に応じてノードサイズを計算する"""
        metric_value = int(metric_value or 0)
        if metric_value <= 0:
            return 14 if node_type == 'channel' else 12

        if node_type == 'channel':
            size = 14 + min(36, int(math.log10(metric_value + 1) * 12))
        else:
            size = 12 + min(36, int(math.log10(metric_value + 1) * 14))

        return max(12, min(60, size))

    def _add_node_if_not_exists(self, label, node_type, image_url=None, external_id=None, link_url=None, metric_value=None, metadata=None):
        """ノードが存在しない場合に追加し、そのIDを返す。画像URLやリンクURL、サイズ用のメトリクスが与えられたら設定する。"""
        # 同じラベルとタイプのノードが既に存在するかチェック
        for node_id, node_data in self.nodes.items():
            if (node_data['label'] == label and node_data['type'] == node_type) or (external_id and node_data.get('external_id') == external_id):
                # external_idを保持
                if external_id and 'external_id' not in node_data:
                    node_data['external_id'] = external_id
                # 既存ノードに画像が無ければ追加する
                if image_url and 'image' not in node_data:
                    node_data['image'] = image_url
                    node_data['shape'] = 'image'
                # 既存ノードにリンクが無ければ追加する
                if link_url and 'url' not in node_data:
                    node_data['url'] = link_url
                # 既存ノードのメトリクスが大きい場合だけ更新する
                if metric_value is not None:
                    current_metric = node_data.get('metric_value', 0)
                    if current_metric < int(metric_value):
                        node_data['metric_value'] = int(metric_value)
                        node_data['size'] = self._calculate_node_size(node_type, metric_value)
                if metadata:
                    for key, value in metadata.items():
                        if value is not None and key not in node_data:
                            node_data[key] = value
                return node_id

        # 存在しない場合は新規作成
        node_id = self._get_next_node_id()
        node = {
            'id': node_id,
            'label': label,
            'type': node_type,
            'group': node_type,
            'title': label,  # ツールチップ用
        }

        # アニメノードは可能なら画像で表示する
        if node_type == 'anime':
            if image_url:
                node['shape'] = 'image'
                node['image'] = image_url
            else:
                node['shape'] = 'box'
        else:
            node['shape'] = 'dot'

        # 外部IDがあれば保存（例: channelId）
        if external_id:
            node['external_id'] = external_id
        if link_url:
            node['url'] = link_url
        if metric_value is not None:
            node['metric_value'] = int(metric_value)
            node['size'] = self._calculate_node_size(node_type, metric_value)
        else:
            node['metric_value'] = 0
            node['size'] = 14 if node_type == 'channel' else 12
        if metadata:
            for key, value in metadata.items():
                if value is not None:
                    node[key] = value

        self.nodes[node_id] = node
        return node_id

    @staticmethod
    def _normalize_space(value):
        return re.sub(r'\s+', '', str(value or '').strip())

    def _extract_series_metadata(self, title, description=''):
        """タイトルと説明からアニメシリーズ名・シーズン・曲種を抽出する"""
        source = ' '.join(part for part in [title or '', description or ''] if part)
        searchable = re.sub(r'\s+', '', source)

        kind = 'related'
        kind_label = '関連動画'
        if re.search(r'(?:オープニング|OP|opening|ＯＰ)', searchable, re.IGNORECASE):
            kind = 'op'
            kind_label = 'OP'
        elif re.search(r'(?:エンディング|ED|ending|ＥＤ)', searchable, re.IGNORECASE):
            kind = 'ed'
            kind_label = 'ED'
        elif re.search(r'(?:挿入歌|insert song|インサート)', searchable, re.IGNORECASE):
            kind = 'insert'
            kind_label = '挿入歌'
        elif re.search(r'(?:MV|music video|ミュージックビデオ)', searchable, re.IGNORECASE):
            kind = 'mv'
            kind_label = 'MV'
        elif re.search(r'(?:スペシャル|special)', searchable, re.IGNORECASE):
            kind = 'special'
            kind_label = 'SP'

        season_order = 99
        season_label = '未分類'
        season_patterns = [
            (r'(?:第\s*1|1st|第一)\s*(?:クール|シーズン|期)', '第1クール', 1),
            (r'(?:第\s*2|2nd|第二)\s*(?:クール|シーズン|期)', '第2クール', 2),
            (r'(?:第\s*3|3rd|第三)\s*(?:クール|シーズン|期)', '第3クール', 3),
            (r'(?:第\s*4|4th|第四)\s*(?:クール|シーズン|期)', '第4クール', 4),
            (r'(?:前期)', '前期', 1),
            (r'(?:後期)', '後期', 2),
            (r'(?:Season|season)\s*(\d+)', 'Season', 0),
            (r'(?:第\s*(\d+)\s*(?:クール|シーズン|期))', 'クール/シーズン', 0),
        ]
        for pattern, label, default_value in season_patterns:
            match = re.search(pattern, source, re.IGNORECASE)
            if not match:
                continue
            season_label = label
            if '前期' in pattern:
                season_order = 1
            elif '後期' in pattern:
                season_order = 2
            elif 'Season' in pattern or 'season' in pattern:
                # Season パターンはグループ1を持つ
                season_order = int(match.group(1)) if match.lastindex and match.lastindex >= 1 else 0
            elif match.lastindex and match.lastindex >= 1:
                # クール/シーズン パターンはグループ1を持つ
                season_order = int(match.group(1))
            else:
                season_order = default_value
            break

        candidate = title or description or ''
        title_matches = list(re.finditer(r'[『「]([^』」]+)[』」]', candidate))
        anime_title_matches = [
            match for match in title_matches
            if re.search(r'(?:TV\s*)?アニメ\s*$', candidate[:match.start()])
        ]
        if anime_title_matches:
            candidate = anime_title_matches[-1].group(1)
        pipe_parts = [part.strip() for part in re.split(r'[|｜]', candidate) if part.strip()]
        series_part = next(
            (part for part in pipe_parts if re.search(r'アニメ|EXCEEDS|シリーズ', part, re.IGNORECASE)
             and not re.search(r'ノンクレジット|\b(?:OP|ED)\b', part, re.IGNORECASE)),
            None,
        )
        if series_part:
            candidate = re.sub(r'^TV\s*アニメ\s*', '', series_part, flags=re.IGNORECASE).strip()
        elif len(title_matches) == 1 and not anime_title_matches:
            candidate = title_matches[0].group(1)
        elif len(title_matches) > 1:
            leading_title_match = re.search(r'[『「]([^』」]+)[』」]', re.split(r'[／/|｜]', title)[0])
            if leading_title_match:
                candidate = leading_title_match.group(1)
        candidate = re.sub(r'[〜～].*?[〜～]', ' ', candidate)
        candidate = re.sub(r'\s*第\s*\d+\s*話.*$', '', candidate)
        candidate = re.sub(r'\s*[／/|].*$', '', candidate)
        candidate = re.sub(r'\s+', ' ', candidate).strip()
        candidate = candidate.replace('【', ' ').replace('】', ' ')
        candidate = candidate.replace('「', ' ').replace('」', ' ').replace('『', ' ').replace('』', ' ')
        candidate = candidate.replace('|', ' ').replace('｜', ' ').replace('／', ' ')
        candidate = re.sub(r'\([^)]*\)', ' ', candidate)
        candidate = re.sub(r'\[[^\]]*\]', ' ', candidate)
        candidate = re.sub(r'#\s*\d+\s*[「『][^」』]+[」』]', ' ', candidate)
        candidate = re.sub(r'(?i)\b(?:TV\s*Anime|TVアニメ|Anime|アニメ|Official|official)\b', ' ', candidate)
        candidate = re.sub(r'(?i)\b(?:ノンクレジット|ノンテロップ|TV放送版|歌詞有|歌詞付き|ver|VER|映像|ムービー|主題歌|テーマ|ミュージックビデオ|オープニング|エンディング|挿入歌)\b', ' ', candidate)
        candidate = re.sub(r'(?i)\b(?:Season|season)\s*\d+\b', ' ', candidate)
        candidate = re.sub(r'(?i)(?:第\s*\d+\s*(?:クール|シーズン|期)|前期|後期)', ' ', candidate)
        candidate = re.sub(r'[^0-9A-Za-zぁ-んァ-ン一-龥ー〜\s\-]', '', candidate)
        candidate = re.sub(r'\s+', ' ', candidate).strip(' -_')

        if len(candidate) < 2:
            fallback = title or description or ''
            fallback = re.sub(r'(?i)\b(?:OP|ED|MV|オープニング|エンディング|ノンクレジット|ノンテロップ|映像|ムービー)\b', ' ', fallback)
            fallback = re.sub(r'\s+', ' ', fallback).strip(' -_')
            candidate = fallback

        series_key = candidate or (title or description or 'Unknown')
        return {
            'anime_key': series_key,
            'series_key': series_key,
            'series_name': series_key,
            'season_order': season_order,
            'season_label': season_label,
            'tag': kind,
            'segment_label': kind_label,
            'priority_order': {'op': 0, 'ed': 1, 'mv': 2, 'insert': 3, 'special': 4, 'related': 99}.get(kind, 99),
        }

    def _build_series_sequence_edges(self):
        """同一アニメシリーズ内の動画を優先度順に接続し、同列に並ぶようにする"""
        groups = defaultdict(list)
        for node in self.nodes.values():
            if node.get('type') != 'anime':
                continue
            key = node.get('series_key') or node.get('anime_key') or node.get('label')
            groups[key].append(node)

        for series_nodes in groups.values():
            series_nodes.sort(key=lambda node: (
                int(node.get('season_order', 99)),
                int(node.get('priority_order', 99)),
                -int(node.get('metric_value', 0)),
                str(node.get('label', '')),
            ))
            for previous, current in zip(series_nodes, series_nodes[1:]):
                self.edges.append({
                    'from': previous['id'],
                    'to': current['id'],
                    'label': 'series',
                    'arrows': 'to',
                    'dashes': True,
                    'series_link': True,
                    'color': {'color': '#7c3aed', 'highlight': '#6d28d9'},
                    'font': {'align': 'middle', 'color': '#4c1d95'},
                    'width': 2,
                })

    def _extract_edge_label(self, title):
        """動画タイトルからエッジのラベル（OP/ED/MVなど）を抽出"""
        title_lower = title.lower()
        if 'オープニング' in title_lower or 'op' in title_lower:
            return 'OP'
        if 'エンディング' in title_lower or 'ed' in title_lower:
            return 'ED'
        if 'mv' in title_lower or 'music video' in title_lower:
            return 'MV'
        if '挿入歌' in title_lower:
            return '挿入歌'
        if 'スペシャル' in title_lower:
            return 'SP'
        return '関連動画' # デフォルト

    def fetch_video_details(self, video_ids):
        """動画の詳細情報を取得"""
        videos = []

        # チャンネルID収集用
        channel_ids_set = set()
        channel_id_to_name = {}

        # 1リクエストで最大50個の動画情報を取得
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]

            try:
                request = self.youtube.videos().list(
                    part='snippet,statistics',
                    id=','.join(batch_ids)
                )
                response = request.execute()

                for item in response.get('items', []):
                    # サムネイルURLを取得（high > medium > default の順で選択）
                    thumbs = item['snippet'].get('thumbnails', {})
                    thumbnail_url = None
                    for key in ('high', 'medium', 'default'):
                        if key in thumbs:
                            thumbnail_url = thumbs[key].get('url')
                            break
                    channel_id = item['snippet'].get('channelId')

                    video_info = {
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'published_at': item['snippet']['publishedAt'],
                        'channel_name': item['snippet'].get('channelTitle', 'Unknown'),
                        'channel_id': channel_id,
                        'view_count': item['statistics'].get('viewCount', 0),
                        'thumbnail_url': thumbnail_url,
                    }
                    series_metadata = self._extract_series_metadata(video_info['title'], video_info.get('description', ''))
                    video_info.update({
                        'anime_key': series_metadata['anime_key'],
                        'series_key': series_metadata['series_key'],
                        'series_name': series_metadata['series_name'],
                        'season_order': series_metadata['season_order'],
                        'season_label': series_metadata['season_label'],
                        'tag': series_metadata['tag'],
                        'segment_label': series_metadata['segment_label'],
                        'priority_order': series_metadata['priority_order'],
                    })
                    videos.append(video_info)

                    # ネットワークデータ生成
                    channel_name = video_info['channel_name']
                    anime_title = video_info['title']  # 現状は動画タイトルをそのままアニメ作品名とする
                    channel_url = f'https://www.youtube.com/channel/{channel_id}' if channel_id else None
                    anime_url = f'https://www.youtube.com/watch?v={video_info["video_id"]}' if video_info.get('video_id') else None
                    if channel_id:
                        channel_ids_set.add(channel_id)
                        # 後でアイコンを紐付けるために名前を保持
                        channel_id_to_name[channel_id] = channel_name

                    # チャンネルノードを追加
                    channel_node_id = self._add_node_if_not_exists(
                        channel_name,
                        'channel',
                        external_id=channel_id,
                        link_url=channel_url,
                        metric_value=0,
                    )

                    # アニメ作品ノードを追加（サムネを渡して画像ノード化）
                    anime_node_id = self._add_node_if_not_exists(
                        anime_title,
                        'anime',
                        image_url=video_info.get('thumbnail_url'),
                        external_id=video_info['video_id'],
                        link_url=anime_url,
                        metric_value=video_info.get('view_count', 0),
                        metadata={
                            'anime_key': video_info.get('anime_key'),
                            'series_key': video_info.get('series_key'),
                            'series_name': video_info.get('series_name'),
                            'season_order': video_info.get('season_order'),
                            'season_label': video_info.get('season_label'),
                            'tag': video_info.get('tag'),
                            'segment_label': video_info.get('segment_label'),
                            'priority_order': video_info.get('priority_order'),
                        },
                    )

                    # エッジを追加
                    edge_label = self._extract_edge_label(anime_title)
                    self.edges.append({
                        'from': channel_node_id,
                        'to': anime_node_id,
                        'label': edge_label,
                        'video_id': video_info['video_id'],  # エッジに動画IDを付与
                        'arrows': 'to',
                        'font': {'align': 'middle'},
                        'series_key': video_info.get('series_key'),
                        'tag': video_info.get('tag'),
                        'priority_order': video_info.get('priority_order'),
                    })

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        # 取得したチャンネルIDに対してアイコンを取得し、チャネルノードに画像をセット
        if channel_ids_set:
            icons_map = self.fetch_channel_icons(channel_ids_set)
            for cid, name in channel_id_to_name.items():
                channel_info = icons_map.get(cid, {})
                icon = channel_info.get('icon_url')
                subscriber_count = channel_info.get('subscriber_count', 0)
                if icon or subscriber_count > 0:
                    # 既存のチャンネルノードにアイコンと登録者数を設定（external_idでマッチ）
                    self._add_node_if_not_exists(
                        name,
                        'channel',
                        image_url=icon,
                        external_id=cid,
                        metric_value=subscriber_count,
                    )

            # 動画データにもチャンネルアイコンURLを追加
            for v in videos:
                cid = v.get('channel_id')
                if cid:
                    channel_info = icons_map.get(cid, {})
                    v['channel_icon_url'] = channel_info.get('icon_url')
                    v['subscriber_count'] = channel_info.get('subscriber_count', 0)

        return videos

    def fetch_channel_icons(self, channel_ids):
        """Channels.list を使ってチャンネルアイコンと登録者数を取得し、channelId->情報 の辞書を返す"""
        icons = {}
        ids = list(channel_ids)
        for i in range(0, len(ids), 50):
            batch = ids[i:i+50]
            try:
                request = self.youtube.channels().list(
                    part='snippet,statistics',
                    id=','.join(batch),
                    maxResults=50
                )
                response = request.execute()
                for item in response.get('items', []):
                    cid = item.get('id')
                    thumbs = item['snippet'].get('thumbnails', {})
                    icon_url = None
                    for key in ('high', 'default', 'medium'):
                        if key in thumbs:
                            icon_url = thumbs[key].get('url')
                            break
                    subscriber_count = item['statistics'].get('subscriberCount', 0)
                    icons[cid] = {
                        'icon_url': icon_url,
                        'subscriber_count': int(subscriber_count or 0),
                    }
            except HttpError as e:
                logger.error(f'Channels API エラー: {e}')
        return icons

    def save_to_csv(self, videos_data):
        """データをCSVに保存（既存データを読み込まず、完全に上書き）"""
        # 重複排除
        unique_videos = []
        seen_video_ids = set()
        for video in videos_data:
            video_id = video.get('video_id')
            if video_id and video_id in seen_video_ids:
                continue
            if video_id:
                seen_video_ids.add(video_id)
            unique_videos.append(video)

        # 保存先ディレクトリを作成
        os.makedirs(os.path.dirname(self.output_csv) or '.', exist_ok=True)

        # CSV書き出し
        fieldnames = list(unique_videos[0].keys()) if unique_videos else []
        with open(self.output_csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in unique_videos:
                writer.writerow(row)

        logger.info(f'CSVファイルを最新データで上書きしました (総動画数: {len(unique_videos)} 件)')

    def save_network_data_to_json(self):
        """ノードとエッジのデータをJSONファイルに保存"""
        output_dir = os.path.dirname(self.output_network_json)
        os.makedirs(output_dir or '.', exist_ok=True)
        self._build_series_sequence_edges()

        network_data = {
            'nodes': list(self.nodes.values()),
            'edges': self.edges
        }

        with open(self.output_network_json, 'w', encoding='utf-8') as f:
            json.dump(network_data, f, ensure_ascii=False, indent=4)

        logger.info(f'ネットワークデータをJSONで保存しました: {self.output_network_json}')


    def run(self):
        """メイン処理"""
        try:
            logger.info('再生リストからの取得を開始します...')

            # 再生リストから動画IDを取得
            video_ids = self.fetch_playlist_items()

            # 動画の詳細情報を取得し、ノードとエッジも生成
            logger.info('動画の詳細情報を取得中...')
            videos_data = self.fetch_video_details(video_ids)

            # CSVに新規上書き保存
            self.save_to_csv(videos_data)

            # ネットワークデータをJSONで保存
            self.save_network_data_to_json()

            logger.info('処理が完了しました')

        except Exception as e:
            logger.error(f'予期しないエラーが発生しました: {e}')
            sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='YouTube再生リストからアニメOP/ED情報を取得')
    parser.add_argument('--config', default=None, help='設定ファイルのパス (オプション。省略時はデフォルト設定を使用)')
    args = parser.parse_args()

    fetcher = PlaylistFetcher(args.config)
    fetcher.run()


if __name__ == '__main__':
    main()
