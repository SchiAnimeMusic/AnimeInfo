#!/usr/bin/env python3
"""
CSVデータを可視化してチャンネル毎の統計情報をグラフ表示
HTMLレポート生成、統計CSVの出力も対応
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import logging
from datetime import datetime
import base64
from io import BytesIO

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


def create_visualizations(channel_stats, csv_path, show=True):
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

    if show:
        plt.show()
    else:
        plt.close(fig)


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


def save_statistics_csv(channel_stats, csv_path):
    """統計情報をCSVファイルに保存"""
    output_dir = os.path.dirname(csv_path)
    
    # 全チャンネルの統計をCSVで保存
    stats_df = channel_stats.reset_index()
    stats_df.columns = ['チャンネル名', '動画数', '合計再生回数', '平均再生回数']
    stats_df = stats_df.sort_values('合計再生回数', ascending=False).reset_index(drop=True)
    stats_df.index = stats_df.index + 1
    stats_df.index.name = 'ランク'
    
    stats_output_path = os.path.join(output_dir, 'channel_statistics.csv')
    stats_df.to_csv(stats_output_path, encoding='utf-8-sig')
    logger.info(f'統計情報をCSVで保存しました: {stats_output_path}')


def generate_html_report(channel_stats, csv_path):
    """HTMLレポートを生成"""
    output_dir = os.path.dirname(csv_path)
    html_output_path = os.path.join(output_dir, 'statistics_report.html')
    
    # グラフ画像をBase64エンコード
    top_20_by_count = channel_stats.sort_values('video_count', ascending=False).head(20)
    top_20_by_views = channel_stats.sort_values('total_views', ascending=False).head(20)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 12))
    fig.suptitle('チャンネル毎の統計情報（TOP 20）', fontsize=16, fontweight='bold')
    
    # グラフ作成
    ax1 = axes[0]
    top_20_by_count['video_count'].plot(kind='barh', ax=ax1, color='steelblue')
    ax1.set_xlabel('動画数', fontsize=12)
    ax1.set_ylabel('チャンネル名', fontsize=12)
    ax1.set_title('チャンネル毎の合計動画数（TOP 20）', fontsize=14, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    ax1.invert_yaxis()
    
    for i, v in enumerate(top_20_by_count['video_count']):
        ax1.text(v + 0.1, i, str(int(v)), va='center', fontsize=10)
    
    ax2 = axes[1]
    (top_20_by_views['total_views'] / 1e6).plot(kind='barh', ax=ax2, color='coral')
    ax2.set_xlabel('合計再生回数 (百万)', fontsize=12)
    ax2.set_ylabel('チャンネル名', fontsize=12)
    ax2.set_title('チャンネル毎の合計再生回数（TOP 20）', fontsize=14, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    ax2.invert_yaxis()
    
    for i, v in enumerate(top_20_by_views['total_views'] / 1e6):
        ax2.text(v + 10, i, f'{v:.1f}M', va='center', fontsize=10)
    
    plt.tight_layout()
    
    # グラフをBase64エンコード
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    graph_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    
    # TOP 20テーブル（動画数）
    top_20_count_table = channel_stats.sort_values('video_count', ascending=False).head(20).reset_index()
    
    # TOP 20テーブル（再生回数）
    top_20_views_table = channel_stats.sort_values('total_views', ascending=False).head(20).reset_index()
    
    # 全体統計
    total_videos = int(channel_stats['video_count'].sum())
    total_views = channel_stats['total_views'].sum()
    total_channels = len(channel_stats)
    avg_views = total_views / total_videos if total_videos > 0 else 0
    
    # HTMLを生成
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>アニメOP/ED チャンネル統計レポート</title>
        <style>
            body {{
                font-family: 'Yu Gothic', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            h1 {{
                text-align: center;
                color: #333;
                border-bottom: 3px solid #0066cc;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #0066cc;
                border-left: 4px solid #0066cc;
                padding-left: 10px;
                margin-top: 30px;
            }}
            .summary {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            }}
            .summary-item {{
                background: white;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .summary-item .label {{
                color: #666;
                font-size: 14px;
                margin-bottom: 5px;
            }}
            .summary-item .value {{
                font-size: 24px;
                font-weight: bold;
                color: #0066cc;
            }}
            .graph-container {{
                background: white;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin: 20px 0;
                text-align: center;
            }}
            .graph-container img {{
                max-width: 100%;
                height: auto;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                margin: 20px 0;
            }}
            th {{
                background-color: #0066cc;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }}
            td {{
                padding: 10px 12px;
                border-bottom: 1px solid #ddd;
            }}
            tr:hover {{
                background-color: #f9f9f9;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .rank {{
                font-weight: bold;
                color: #0066cc;
            }}
            .footer {{
                text-align: center;
                color: #999;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <h1>アニメOP/ED チャンネル統計レポート</h1>
        
        <div class="summary">
            <div class="summary-item">
                <div class="label">総チャンネル数</div>
                <div class="value">{total_channels}</div>
            </div>
            <div class="summary-item">
                <div class="label">総動画数</div>
                <div class="value">{total_videos:,}</div>
            </div>
            <div class="summary-item">
                <div class="label">総再生回数</div>
                <div class="value">{total_views:,.0f}</div>
            </div>
            <div class="summary-item">
                <div class="label">平均再生回数</div>
                <div class="value">{avg_views:,.0f}</div>
            </div>
        </div>
        
        <div class="graph-container">
            <img src="data:image/png;base64,{graph_base64}" alt="チャンネル統計グラフ">
        </div>
        
        <h2>TOP 20 チャンネル（動画数順）</h2>
        <table>
            <thead>
                <tr>
                    <th>ランク</th>
                    <th>チャンネル名</th>
                    <th>動画数</th>
                    <th>合計再生回数</th>
                    <th>平均再生回数</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for rank, (idx, row) in enumerate(top_20_count_table.iterrows(), 1):
        html_content += f"""
                <tr>
                    <td class="rank">{rank}</td>
                    <td>{row['channel_name']}</td>
                    <td>{int(row['video_count'])}</td>
                    <td>{row['total_views']:,.0f}</td>
                    <td>{row['avg_views']:,.0f}</td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
        
        <h2>TOP 20 チャンネル（再生回数順）</h2>
        <table>
            <thead>
                <tr>
                    <th>ランク</th>
                    <th>チャンネル名</th>
                    <th>合計再生回数</th>
                    <th>動画数</th>
                    <th>平均再生回数</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for rank, (idx, row) in enumerate(top_20_views_table.iterrows(), 1):
        html_content += f"""
                <tr>
                    <td class="rank">{rank}</td>
                    <td>{row['channel_name']}</td>
                    <td>{row['total_views']:,.0f}</td>
                    <td>{int(row['video_count'])}</td>
                    <td>{row['avg_views']:,.0f}</td>
                </tr>
        """
    
    html_content += f"""
            </tbody>
        </table>
        
        <div class="footer">
            <p>レポート生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    with open(html_output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f'HTMLレポートを生成しました: {html_output_path}')


def main():
    import argparse

    parser = argparse.ArgumentParser(description='アニメOP/ED統計情報を可視化')
    parser.add_argument('--csv', '-c', default='./data/anime_op_ed.csv',
                        help='CSVファイルのパス (デフォルト: ./data/anime_op_ed.csv)')
    parser.add_argument('--no-display', action='store_true',
                        help='グラフ表示を行わない（バッチ処理用）')

    args = parser.parse_args()

    # データを読み込み
    df = load_csv_data(args.csv)

    # 統計情報を計算
    channel_stats = analyze_by_channel(df)

    # グラフを作成（PNGファイル保存）
    create_visualizations(channel_stats, args.csv, show=not args.no_display)
    
    # 統計情報をターミナルに出力
    print_statistics(channel_stats)
    
    # HTMLレポート生成
    generate_html_report(channel_stats, args.csv)
    
    # 統計情報をCSVで保存
    save_statistics_csv(channel_stats, args.csv)


if __name__ == '__main__':
    main()
