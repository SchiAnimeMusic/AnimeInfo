#!/usr/bin/env python3
"""
YouTube再生リストからアニメOP/ED情報を取得し、CSVに保存するスクリプト
"""

import json
import os
import sys
import csv
from pathlib import Path
from datetime import datetime
import logging

import pandas as pd
from dotenv import load_dotenv
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
                'playlist_id': 'PLarZd9ydotojcNKocdU95YFqooKnF-w_p',
                'output_csv_path': './data/anime_op_ed.csv',
                'output_network_json_path': './data/network_data.json',
                'timezone': 'Asia/Tokyo'
            }

        if not os.path.exists(config_path):
            logger.warning(f'設定ファイルが見つかりません: {config_path}')
            logger.warning('デフォルト設定を使用します')
            return {
                'playlist_id': 'PLarZd9ydotojcNKocdU95YFqooKnF-w_p',
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

    def _add_node_if_not_exists(self, label, node_type):
        """ノードが存在しない場合に追加し、そのIDを返す"""
        # 同じラベルとタイプのノードが既に存在するかチェック
        for node_id, node_data in self.nodes.items():
            if node_data['label'] == label and node_data['type'] == node_type:
                return node_id

        # 存在しない場合は新規作成
        node_id = self._get_next_node_id()
        self.nodes[node_id] = {
            'id': node_id,
            'label': label,
            'type': node_type,
            'group': node_type,
            'shape': 'box' if node_type == 'anime' else 'dot',
        }
        return node_id
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
                    video_info = {
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': item['snippet']['description'],
                        'published_at': item['snippet']['publishedAt'],
                        'channel_name': item['snippet'].get('channelTitle', 'Unknown'),
                        'view_count': item['statistics'].get('viewCount', 0),
                    }
                    videos.append(video_info)

                    # ネットワークデータ生成
                    channel_name = video_info['channel_name']
                    anime_title = video_info['title'] # 現状は動画タイトルをそのままアニメ作品名とする

                    # チャンネルノードを追加
                    channel_node_id = self._add_node_if_not_exists(channel_name, 'channel')

                    # アニメ作品ノードを追加
                    anime_node_id = self._add_node_if_not_exists(anime_title, 'anime')

                    # エッジを追加
                    edge_label = self._extract_edge_label(anime_title)
                    self.edges.append({
                        'from': channel_node_id,
                        'to': anime_node_id,
                        'label': edge_label,
                        'video_id': video_info['video_id'],  # エッジに動画IDを付与
                        'arrows': 'to',
                        'font': {'align': 'middle'},
                    })

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        return videos

    def save_to_csv(self, videos_data):
        """データをCSVに保存（既存データを読み込まず、完全に上書き）"""
        # 新規取得したデータのみでデータフレームを作成
        result_df = pd.DataFrame(videos_data)

        # 再生リスト内に万が一重複があってもここで確実に排除
        if 'video_id' in result_df.columns:
            result_df = result_df.drop_duplicates(subset=['video_id'], keep='first')
        else:
            result_df = result_df.drop_duplicates(subset=['title', 'channel_name'], keep='first')

        # 保存先ディレクトリを作成
        os.makedirs(os.path.dirname(self.output_csv) or '.', exist_ok=True)

        # 既存ファイルを完全に上書き保存 (index=False)
        result_df.to_csv(self.output_csv, index=False, encoding='utf-8')

        logger.info(f'CSVファイルを最新データで上書きしました (総動画数: {len(result_df)} 件)')

    def save_network_data_to_json(self):
        """ノードとエッジのデータをJSONファイルに保存"""
        output_dir = os.path.dirname(self.output_network_json)
        os.makedirs(output_dir or '.', exist_ok=True)

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