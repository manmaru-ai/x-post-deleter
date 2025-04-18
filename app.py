import json
import requests
import argparse
import datetime
import os
import concurrent.futures
import time
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

# .envファイルの読み込み
load_dotenv()

# 環境変数からAPI Keyを取得
API_KEY = os.getenv('API_KEY')
API_SECRET_KEY = os.getenv('API_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_SECRET')

# APIキーが設定されているか確認
if not all([API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET]):
    print("APIキーが設定されていません。.envファイルを確認してください。")
    print("必要な環境変数: API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET")
    exit(1)

# OAuth Authentication
auth = OAuth1(API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)

# Function to extract tweet IDs from archived data
def extract_tweet_ids_from_archive(archive_file_path, start_date=None, end_date=None):
    tweet_ids = []
    tweets_data_for_preview = []
    
    with open(archive_file_path, 'r', encoding='utf-8') as file:
        data = file.read()
        data = data.replace('window.YTD.tweets.part0 = ', '')
        tweets_data = json.loads(data)

        for tweet in tweets_data:
            tweet_info = tweet['tweet']
            tweet_id = tweet_info['id_str']
            
            # 日付情報の取得
            created_at = tweet_info['created_at']
            # Twitter APIの日付形式: "Wed Oct 10 20:19:24 +0000 2018"
            tweet_date = datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").date()
            
            # 期間指定フィルタリング
            if start_date and tweet_date < start_date:
                continue
            if end_date and tweet_date > end_date:
                continue
                
            tweet_ids.append(tweet_id)
            tweets_data_for_preview.append({
                'id': tweet_id,
                'date': tweet_date.strftime("%Y-%m-%d"),
                'text': tweet_info['full_text'] if 'full_text' in tweet_info else tweet_info['text']
            })
            
    return tweet_ids, tweets_data_for_preview

# 単一ツイート削除関数（並列処理用）
def delete_single_tweet(tweet_id):
    url_delete_tweet = "https://api.twitter.com/1.1/statuses/destroy/"
    try:
        del_response = requests.post(url_delete_tweet + f"{tweet_id}.json", auth=auth)
        if del_response.status_code == 200:
            return (True, tweet_id, "成功")
        else:
            return (False, tweet_id, f"ステータスコード: {del_response.status_code}")
    except Exception as e:
        return (False, tweet_id, str(e))

# 並列処理でツイートを削除する関数
def delete_tweets_parallel(tweet_ids, max_workers=10, rate_limit=50):
    """
    並列処理でツイートを削除する
    
    Args:
        tweet_ids: 削除するツイートIDのリスト
        max_workers: 最大並列数（デフォルト: 10）
        rate_limit: レート制限（1分あたりの最大API呼び出し数）
    """
    results = {"success": 0, "failed": 0}
    total_tweets = len(tweet_ids)
    
    # 進捗表示用
    def print_progress(completed, total):
        percent = (completed / total) * 100
        print(f"\r進捗: {completed}/{total} ({percent:.1f}%) 成功: {results['success']} 失敗: {results['failed']}", end="")
    
    print(f"合計 {total_tweets} 件のツイートを削除します...")
    
    # チャンク単位で処理（レート制限対策）
    chunk_size = min(rate_limit, total_tweets)
    for i in range(0, total_tweets, chunk_size):
        chunk = tweet_ids[i:i+chunk_size]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(delete_single_tweet, tweet_id) for tweet_id in chunk]
            
            for future in concurrent.futures.as_completed(futures):
                success, tweet_id, message = future.result()
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    print(f"\nツイートID: {tweet_id} の削除に失敗しました - {message}")
                
                print_progress(i + results["success"] + results["failed"], total_tweets)
        
        # レート制限に達した場合、次のチャンクまで待機
        if i + chunk_size < total_tweets:
            print("\nTwitter APIのレート制限のため、60秒待機します...")
            time.sleep(60)  # 1分待機
    
    print("\n")  # 進捗表示後の改行
    print(f"削除完了: 成功 {results['success']} 件、失敗 {results['failed']} 件")
    return results

# Function to delete a tweet (旧バージョン - 非並列処理)
def delete_tweets(tweet_ids):
    url_delete_tweet = "https://api.twitter.com/1.1/statuses/destroy/"
    for tweet_id in tweet_ids:
        del_response = requests.post(url_delete_tweet + f"{tweet_id}.json", auth=auth)
        if del_response.status_code == 200:
            print(f"ツイートID: {tweet_id} を削除しました")
        else:
            print(f"ツイートID: {tweet_id} の削除に失敗しました、ステータスコード: {del_response.status_code}")

# 削除前に確認を行う関数
def preview_tweets(tweets_data):
    print(f"\n削除予定のツイート数: {len(tweets_data)}\n")
    
    # プレビュー（最初の5つだけ表示）
    print("削除予定ツイートのプレビュー:")
    for i, tweet in enumerate(tweets_data[:5]):
        print(f"{i+1}. [{tweet['date']}] {tweet['text'][:50]}...")
    
    if len(tweets_data) > 5:
        print(f"...他 {len(tweets_data) - 5} 件のツイート\n")

def main():
    parser = argparse.ArgumentParser(description='期間指定してツイートを削除するプログラム')
    parser.add_argument('--file', type=str, default='tweets.js', help='ツイートアーカイブファイルのパス')
    parser.add_argument('--start', type=str, help='削除開始日（YYYY-MM-DD形式）')
    parser.add_argument('--end', type=str, help='削除終了日（YYYY-MM-DD形式）')
    parser.add_argument('--workers', type=int, default=10, help='並列処理の最大ワーカー数（デフォルト: 10）')
    parser.add_argument('--rate-limit', type=int, default=50, help='1分あたりのAPIリクエスト上限（デフォルト: 50）')
    parser.add_argument('--parallel', action='store_true', help='並列処理を有効にする')
    args = parser.parse_args()
    
    # 日付の変換
    start_date = None
    end_date = None
    
    if args.start:
        try:
            start_date = datetime.datetime.strptime(args.start, "%Y-%m-%d").date()
        except ValueError:
            print("不正な開始日の形式です。YYYY-MM-DD形式で指定してください。")
            return
    
    if args.end:
        try:
            end_date = datetime.datetime.strptime(args.end, "%Y-%m-%d").date()
        except ValueError:
            print("不正な終了日の形式です。YYYY-MM-DD形式で指定してください。")
            return
    
    # ツイートIDの抽出と削除確認用データの準備
    tweet_ids, tweets_preview = extract_tweet_ids_from_archive(args.file, start_date, end_date)
    
    if not tweet_ids:
        print("指定された期間内のツイートはありません。")
        return
    
    # 削除予定ツイートのプレビュー表示
    preview_tweets(tweets_preview)
    
    # ユーザーに確認
    confirmation = input("これらのツイートを削除しますか？ (y/n): ")
    if confirmation.lower() == 'y':
        # 並列処理または通常処理を選択
        start_time = time.time()
        
        if args.parallel:
            delete_tweets_parallel(tweet_ids, max_workers=args.workers, rate_limit=args.rate_limit)
        else:
            delete_tweets(tweet_ids)
            print(f"合計 {len(tweet_ids)} 件のツイートを削除しました。")
        
        elapsed_time = time.time() - start_time
        print(f"処理時間: {elapsed_time:.2f}秒")
    else:
        print("削除処理をキャンセルしました。")

if __name__ == "__main__":
    main()
