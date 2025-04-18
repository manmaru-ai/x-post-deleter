# TwitterアーカイブとAPIでツイートを一括削除するツール

---

## 前提条件

- 削除対象は**自分自身のツイート**のみです。
- **Twitterアカウントのアーカイブ**（tweets.jsなど）が必要です。
- **APIキー/トークン**（Read, Write, Direct Messages権限）が必要です（無料アカウント可）。
- **Python**が実行できる環境が必要です。

---

## セットアップ手順

### 1. APIキーの設定

ルートディレクトリに`.env`ファイルを作成し、以下の内容を記載してください。

```
API_KEY=あなたのAPIキー
API_SECRET=あなたのAPIシークレットキー
ACCESS_TOKEN=あなたのアクセストークン
ACCESS_SECRET=あなたのアクセスシークレット
```

### 2. 必要なパッケージのインストール

Windowsの場合：

```sh
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 使い方

### 全ツイートを削除

```sh
python app.py
```

### 並列処理による高速削除

- 並列処理を有効にする：

```sh
python app.py --parallel
```

- ワーカー数（並列数）を指定：

```sh
python app.py --parallel --workers 20
```

- レート制限（1分あたりのリクエスト数）を調整：

```sh
python app.py --parallel --rate-limit 100
```

> ⚠️ **注意:** Twitter APIにはレート制限があります。過度な並列処理はAPI制限に抵触する可能性があります。

### 期間を指定して削除

- 2022年4月1日から2022年5月1日までのツイートを削除：

```sh
python app.py --start 2022-04-01 --end 2022-05-01
```

- 2022年4月1日以降のツイートを削除：

```sh
python app.py --start 2022-04-01
```

- 2022年5月1日以前のツイートを削除：

```sh
python app.py --end 2022-05-01
```

- 期間指定と並列処理を併用：

```sh
python app.py --start 2022-04-01 --end 2022-05-01 --parallel
```

### ツイートアーカイブファイルの指定

デフォルトでは`tweets.js`を使用しますが、別ファイルを指定する場合：

```sh
python app.py --file path\to\your\tweets.js
```
