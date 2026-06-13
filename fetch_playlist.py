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
                        'video_id': f"https://www.youtube.com/watch?v={item['id']}",
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],
                        'channel_id': item['snippet']['channelId'],
                        'view_count': item['statistics'].get('viewCount', 0),
                    }
                    videos.append(video_info)

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        return videos

    def fetch_channel_names(self, channel_ids):
        """チャンネル名を取得（キャッシング）"""
        channel_names = {}
        unique_channel_ids = list(set(channel_ids))

        # 1リクエストで最大50個のチャンネル情報を取得
        for i in range(0, len(unique_channel_ids), 50):
            batch_ids = unique_channel_ids[i:i+50]

            try:
                request = self.youtube.channels().list(
                    part='snippet',
                    id=','.join(batch_ids)
                )
                response = request.execute()

                for item in response.get('items', []):
                    channel_names[item['id']] = item['snippet']['title']

            except HttpError as e:
                logger.error(f'APIエラー: {e}')
                sys.exit(1)

        return channel_names

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
        # チャンネル名を取得
        channel_ids = [v['channel_id'] for v in videos_data]
        channel_names = self.fetch_channel_names(channel_ids)

        # チャンネル名を追加
        for video in videos_data:
            video['channel_name'] = channel_names.get(video['channel_id'], 'Unknown')

        # 既存データを読み込む
        existing_df = self.load_existing_data()

        # 新規データをデータフレームに変換
        new_df = pd.DataFrame(videos_data)

        # video_id が既に存在するデータをフィルタリング
        if not existing_df.empty:
            existing_ids = set(existing_df['video_id'])
            new_df = new_df[~new_df['video_id'].isin(existing_ids)]

            if len(new_df) == 0:
                logger.info('新規動画はありません')
                return

        # 必要なカラムのみを選択
        new_df = new_df[['video_id', 'title', 'published_at', 'channel_name', 'view_count']]

        # データを結合
        if not existing_df.empty:
            result_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            result_df = new_df

        # ディレクトリを作成
        os.makedirs(os.path.dirname(self.output_csv) or '.', exist_ok=True)

        # CSVに保存
        result_df.to_csv(self.output_csv, index=False, encoding='utf-8')

        logger.info(f'新規 {len(new_df)} 件をCSVに追加しました (合計: {len(result_df)} 件)')

    def run(self):
        """メイン処理"""
        try:
            logger.info('再生リストからの取得を開始します...')

            # 再生リストから動画IDを取得
            video_ids = self.fetch_playlist_items()

            # 動画の詳細情報を取得
            logger.info('動画の詳細情報を取得中...')
            videos_data = self.fetch_video_details(video_ids)

            # チャンネル名を取得
            logger.info('チャンネル名を取得中...')
            channel_ids = [v['channel_id'] for v in videos_data]
            channel_names = self.fetch_channel_names(channel_ids)

            # チャンネル名を追加
            for video in videos_data:
                video['channel_name'] = channel_names.get(video['channel_id'], 'Unknown')
                del video['channel_id']  # channel_id は不要なので削除

            # CSVに保存
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
