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
                'timezone': 'Asia/Tokyo'
            }

        if not os.path.exists(config_path):
            logger.warning(f'設定ファイルが見つかりません: {config_path}')
            logger.warning('デフォルト設定を使用します')
            return {
                'playlist_id': 'PLarZd9ydotojcNKocdU95YFqooKnF-w_p',
                'output_csv_path': './data/anime_op_ed.csv',
                'timezone': 'Asia/Tokyo'
            }

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
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

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        return videos

    def load_existing_data(self):
        """既存のCSVファイルを読み込む"""
        if not os.path.exists(self.output_csv):
            return pd.DataFrame()

        try:
            return pd.read_csv(self.output_csv)
        except Exception as e:
            logger.warning(f'既存CSVの読み込みに失敗しました: {e}')
            return pd.DataFrame()

    def save_to_csv(self, videos_data):
        """データをCSVに保存"""
        # 新規取得したデータをデータフレーム化
        new_df = pd.DataFrame(videos_data)
        
        # 既存データを読み込む
        existing_df = self.load_existing_data()

        if not existing_df.empty:
            # 既存データと新規データを結合
            result_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            result_df = new_df

        # 最後に video_id を基準に重複を完全に排除する（新しく取得した側を優先）
        if 'video_id' in result_df.columns:
            result_df = result_df.drop_duplicates(subset=['video_id'], keep='last')
        else:
            result_df = result_df.drop_duplicates(subset=['title', 'channel_name'], keep='last')

        # ディレクトリを作成
        os.makedirs(os.path.dirname(self.output_csv) or '.', exist_ok=True)

        # CSVに保存
        result_df.to_csv(self.output_csv, index=False, encoding='utf-8')

        logger.info(f'CSVデータを更新しました (総動画数: {len(result_df)} 件)')

    def run(self):
        """メイン処理"""
        try:
            logger.info('再生リストからの取得を開始します...')

            # 再生リストから動画IDを取得
            video_ids = self.fetch_playlist_items()

            # 動画の詳細情報を取得
            logger.info('動画の詳細情報を取得中...')
            videos_data = self.fetch_video_details(video_ids)

            # CSVに保存（重複排除ロジック内蔵）
            self.save_to_csv(videos_data)

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