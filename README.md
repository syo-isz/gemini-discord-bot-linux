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

---

## 📜 ライセンス (License)
This project is licensed under the MIT License - see the LICENSE file for details.

---
---

# Gemini-Tmux Discord Bridge 🚀 (English Version)

A private bridge tool designed to operate Gemini CLI comfortably, safely, and stylishly from Discord.
Instead of using official APIs, it employs a "hacker-like" approach by **parsing the standard output of a background `tmux` session in real-time and streaming it to Discord**.

The standout feature is its **real-time streaming (Message Edit)**, which provides live updates every 2 seconds as Gemini thinks, executes tools, and writes its response.

---

## 🌟 Key Features

1.  **Real-time Streaming**
    *   Scans Gemini output every 2 seconds and dynamically updates Discord messages.
    *   Experience the live process of "Thinking" and "Generation" line by line.
2.  **Clean & Smart Parsing Engine**
    *   Automatically strips Gemini CLI-specific borders and UI noise (e.g., `╭╮╯╰`) using regex.
    *   Intelligently distinguishes between tool execution logs (code blocks) and Gemini's answers (starting with ✦).
    *   Optimized to immediately close code blocks and transition to normal text once tool execution finishes.
3.  **Owner-Only Security Shield**
    *   Ignores all messages and commands from anyone other than the Discord ID specified in your `.env`.
    *   Safe to operate as your private AI assistant in DMs or public servers.
4.  **Topic-Based Session Management**
    *   Isolates Gemini's memory/processes by switching between different `tmux` sessions.
    *   Automatically restores the last used session even after a service restart.

---

## 🛠 Prerequisites

- **OS**: Linux (Ubuntu 22.04 / 24.04 recommended)
- **Dependencies**: `tmux`, `Node.js (v24+)`, `Python 3.12+`, `systemd`

---

## 🚀 Setup Guide (3 Steps)

### 1. Preparation & Installation
Run these commands in the cloned repository directory:
```bash
python -m venv bot_venv
source bot_venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (.env)
Copy `.env.example` to `.env` and fill in the following fields.
⚠️ **Caution**: The `.env` file contains sensitive information. Never commit it to a public repository.

```ini
DISCORD_TOKEN=Your_Bot_Token
DISCORD_CHANNEL_ID=Target_Channel_ID
MY_DISCORD_ID=Your_Discord_User_ID (18-digit number)
GEMINI_EXECUTABLE_PATH=gemini
```
> 💡 **How to find your ID**: Enable "Developer Mode" in Discord Settings > Advanced, right-click your profile icon, and select "Copy User ID".

### 3. Service Backgrounding (systemd)
Save the following to `~/.config/systemd/user/gemini-bot.service` (create the directory if it doesn't exist).
*Note: Be sure to update `WorkingDirectory` and `ExecStart` with your absolute paths.*

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

Enable and start the service:
```bash
systemctl --user daemon-reload
systemctl --user enable --now gemini-bot.service
```

---

## 🎮 Commands

### 💡 Sending Commands to Gemini CLI
To call internal Gemini CLI commands (like `/help` or `/reset`), prefix your message with `cmd` or use the slash command. The `/` prefix is added automatically.

- **Chat Input**: `cmd help`, `cmd reset`, `cmd file example.md`
- **Slash Command**: `/cmd reset` etc.

### ⚙️ Bot Management (Slash Commands)
Use these to manage the bot's state and sessions.

- `/status`: Check current target tmux session information.
- `/sessions`: List all active tmux sessions.
- `/session [name]`: Switch the target session.
- `/session_new [name]`: Create a new session and launch Gemini CLI.
- `/session_kill [name]`: Terminate a specific session.

---

## 📂 File Structure

- `main.py`: Core bot logic (Real-time extraction & parsing).
- `start.sh`: Tmux preparation, PID management, and startup script.
- `README.md`: This documentation.
- `.last_session`: Persistence file to track the last used session.

---

## ⚠️ Disclaimer (Known Issues)
This tool parses the standard output (Terminal UI) of Gemini CLI using regular expressions. If Google changes the prompt symbols (`*` or `✦`) or layout specifications, parsing may fail or the bot may become unresponsive. This is intended as a personal-use hack tool.

---
Designed with ❤️ by Gemini CLI (YOLO Mode)
