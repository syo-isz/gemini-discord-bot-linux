# Gemini-Tmux Discord Bridge 🚀

Gemini CLI を Discord から快適・安全・スタイリッシュに操作するためのプライベートブリッジツールです。
公式 API を使用せず、**裏で稼働する `tmux` セッションの標準出力をリアルタイムに解析して Discord に流し込む**という、ハッカーライクなアプローチを採用しています。

Gemini が思考し、ツールを実行し、回答を綴るプロセスを **2秒ごとのリアルタイム更新（Message Edit）** で実況中継するのが最大の特徴です。

---

## 🌟 主な特徴

1.  **リアルタイム実況中継 (Streaming)**
    *   Gemini の出力を 2 秒間隔でスキャンし、Discord 上のメッセージを動的に書き換えます。
    *   「今まさに考えている」「1行ずつ回答が生成されている」様子をリアルタイムで体感できます。
2.  **スッキリ・スマート解析エンジン**
    *   Gemini CLI 特有の罫線や UI ノイズ（`╭╮╯╰` など）を正規表現で自動消去。
    *   ツール実行ログ（コードブロック）と Gemini の回答（✦ 始まり）を自動判別し、美しく整形して表示します。
    *   ログ終了後、即座にコードブロックを閉じて次の文章へ移行する最適化済み。
3.  **鉄壁のオーナー専用ガード**
    *   `.env` に設定した「あなたの Discord ID」以外からのメッセージやコマンドを徹底的に無視。
    *   DM でも公開サーバーでも、自分専用の秘書として安全に運用可能です。
4.  **話題ごとのセッション管理**
    *   `tmux` セッションを切り替えることで、話題ごとに Gemini の記憶（プロセス）を完全に分離。
    *   サービス再起動後も、前回使用していたセッションを自動で復元して続きから再開できます。

---

## 🛠 動作環境

- **OS**: Linux (Ubuntu 22.04 / 24.04 推奨)
- **依存ツール**: `tmux`, `Node.js (v24+)`, `Python 3.12+`, `systemd`

---

## 🚀 セットアップガイド (3ステップ)

### 1. 準備とインストール
リポジトリをクローンしたディレクトリで実行してください。
```bash
python -m venv bot_venv
source bot_venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境設定 (.env)
`.env.example` を `.env` という名前でコピーし、以下の項目を埋めてください。
⚠️ **注意**: `.env` には機密情報が含まれます。絶対に公開リポジトリにコミットしないでください。

```ini
DISCORD_TOKEN=あなたのボットトークン
DISCORD_CHANNEL_ID=反応させたいチャンネルID
MY_DISCORD_ID=あなたのDiscordユーザーID (18桁の数字)
GEMINI_EXECUTABLE_PATH=gemini
```
> 💡 **IDの調べ方**: Discord の「設定」>「詳細設定」>「開発者モード」を ON にし、自分のアイコンを右クリックして「ユーザーIDをコピー」を選択してください。

### 3. 常駐サービス化 (systemd)
以下を `~/.config/systemd/user/gemini-bot.service` に保存します（ディレクトリがなければ作成）。
※ `WorkingDirectory` と `ExecStart` のパスは、ご自身の環境に合わせて必ず書き換えてください。

```ini
[Unit]
Description=Gemini Discord Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/ubuntu/gemini-discord-bot
ExecStart=/home/ubuntu/gemini-discord-bot/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

保存後、以下のコマンドで起動・自動起動化します。
```bash
systemctl --user daemon-reload
systemctl --user enable --now gemini-bot.service
```

---

## 🎮 コマンド体系

### 💡 Gemini CLI への命令
Gemini 本体のコマンド（`/help` や `/reset` など）を呼び出す際は、メッセージの先頭に `cmd` を付けるか、スラッシュコマンドを使用してください。`/` はシステムが自動補完します。

- **チャット入力**: `cmd help`, `cmd reset`, `cmd file example.md`
- **スラッシュコマンド**: `/cmd reset` など

### ⚙️ ボット管理 (スラッシュコマンド)
ボット自体の状態操作やセッション管理に使用します。

- `/status`: 現在操作しているターゲットの tmux セッション情報を確認。
- `/sessions`: 稼働中の全セッションをリストアップ。
- `/session [name]`: 操作対象のセッションを切り替え。
- `/session_new [name]`: 新規セッションを作成し、Gemini CLI を起動。
- `/session_kill [name]`: 指定したセッションを終了（消去）。

---

## 📂 ファイル構成

- `main.py`: ボット本体（リアルタイム抽出・パースエンジン）。
- `start.sh`: tmux の準備、PID管理、およびボットの起動スクリプト。
- `README.md`: 本ドキュメント。
- `.last_session`: 最後に使用したセッション名を記録する永続化ファイル。

---

## ⚠️ 免責事項 (Known Issues)
このツールは Gemini CLI の標準出力（ターミナル UI）を正規表現で解析しています。そのため、Google 側が Gemini CLI のプロンプト記号（`*` や `✦`）やレイアウト仕様を変更した場合、出力のパースが崩れる、あるいは Bot が正常に応答しなくなる可能性があります。
あくまで個人用のハックツールとしてご利用ください。

## 📜 ライセンス (License)
This project is licensed under the MIT License - see the LICENSE file for details.

---
Designed with ❤️ by Gemini CLI (YOLO Mode)
