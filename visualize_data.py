#!/usr/bin/env python3
"""
CSVデータを可視化してチャンネル毎の統計情報をグラフ表示
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import logging

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Yu Gothic', 'DejaVu Sans']

# ログの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_csv_data(csv_path):
    """CSVファイルを読み込む"""
    if not os.path.exists(csv_path):
        logger.error(f'CSVファイルが見つかりません: {csv_path}')
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path)
        logger.info(f'{len(df)} 件の動画データを読み込みました')
        return df
    except Exception as e:
        logger.error(f'CSVの読み込みに失敗しました: {e}')
        sys.exit(1)


def analyze_by_channel(df):
    """チャンネル毎の統計情報を計算"""
    # view_countを数値に変換（必要に応じて）
    df['view_count'] = pd.to_numeric(df['view_count'], errors='coerce')

    # チャンネル毎に集計
    channel_stats = df.groupby('channel_name').agg(
        video_count=('title', 'count'),
        total_views=('view_count', 'sum'),
        avg_views=('view_count', 'mean')
    ).sort_values('video_count', ascending=False)

    return channel_stats


def create_visualizations(channel_stats, csv_path):
    """グラフを作成（TOP 20のみ表示）"""
    # 動画数でTOP 20に制限
    top_20_by_count = channel_stats.sort_values('video_count', ascending=False).head(20)
    
    # 合計再生回数でTOP 20に制限
    top_20_by_views = channel_stats.sort_values('total_views', ascending=False).head(20)

    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    fig.suptitle('チャンネル毎の統計情報（TOP 20）', fontsize=16, fontweight='bold')

    # 1. チャンネル毎の動画数（動画数でTOP 20）
    ax1 = axes[0]
    top_20_by_count['video_count'].plot(kind='barh', ax=ax1, color='steelblue')
    ax1.set_xlabel('動画数', fontsize=12)
    ax1.set_ylabel('チャンネル名', fontsize=12)
    ax1.set_title('チャンネル毎の合計動画数（TOP 20）', fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    ax1.invert_yaxis()  # 上から順番に表示

    # 値をバーの右側に表示
    for i, v in enumerate(top_20_by_count['video_count']):
        ax1.text(v + 0.1, i, str(int(v)), va='center', fontsize=10)

    # 2. チャンネル毎の合計再生回数（合計再生回数でTOP 20）
    ax2 = axes[1]
    (top_20_by_views['total_views'] / 1e6).plot(kind='barh', ax=ax2, color='coral')
    ax2.set_xlabel('合計再生回数 (百万)', fontsize=12)
    ax2.set_ylabel('チャンネル名', fontsize=12)
    ax2.set_title('チャンネル毎の合計再生回数（TOP 20）', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    ax2.invert_yaxis()  # 上から順番に表示

    # 値をバーの右側に表示
    for i, v in enumerate(top_20_by_views['total_views'] / 1e6):
        ax2.text(v + 10, i, f'{v:.1f}M', va='center', fontsize=10)

    plt.tight_layout()

    # グラフをファイルに保存
    output_dir = os.path.dirname(csv_path)
    output_path = os.path.join(output_dir, 'channel_statistics.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    logger.info(f'グラフを保存しました: {output_path}')

    plt.show()

    # ターミナルにも統計情報を出力
    print_statistics(channel_stats)


def print_statistics(channel_stats):
    """統計情報をターミナルに出力"""
    # TOP 20に制限
    top_20 = channel_stats.head(20)

    print('\n' + '=' * 90)
    print('チャンネル毎の統計情報（TOP 20）')
    print('=' * 90)

    # 動画数でソート済み
    print('\n【TOP 20 チャンネル毎の動画数と合計再生回数】')
    for rank, (channel, row) in enumerate(top_20.iterrows(), 1):
        print(f'{rank:>2}. {channel:<45} | 動画数: {int(row["video_count"]):>3} | '
              f'合計再生回数: {row["total_views"]:>15,.0f}')

    print('\n【全体統計】')
    print(f'総チャンネル数: {len(channel_stats)} 個')
    print(f'総動画数: {int(channel_stats["video_count"].sum())} 本')
    print(f'総再生回数: {channel_stats["total_views"].sum():,.0f}')
    print(f'平均再生回数: {channel_stats["total_views"].sum() / channel_stats["video_count"].sum():,.0f}')
    print('=' * 90 + '\n')


def main():
    import argparse

    parser = argparse.ArgumentParser(description='アニメOP/ED統計情報を可視化')
    parser.add_argument('--csv', '-c', default='./data/anime_op_ed.csv',
                        help='CSVファイルのパス (デフォルト: ./data/anime_op_ed.csv)')

    args = parser.parse_args()

    # データを読み込み
    df = load_csv_data(args.csv)

    # 統計情報を計算
    channel_stats = analyze_by_channel(df)

    # グラフを作成
    create_visualizations(channel_stats, args.csv)


if __name__ == '__main__':
    main()
