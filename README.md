# Gemini Discord Bot 🚀 (リアルタイム実況中継モード)

Gemini CLI を Discord から快適・安全・スタイリッシュに操作するためのブリッジツールだよ。
Gemini が裏で思考し、ツールを実行し、回答を綴る様子を **2秒ごとのリアルタイム更新（Message Edit）** で中継するのが最大の特徴！

## 🌟 主な特徴

1.  **リアルタイム実況 (Streaming)**:
    *   確定を待たず、2秒ごとにメッセージを書き換えて進捗を表示。
    *   ツール実行ログ（コードブロック）と Gemini の回答（✦ 始まり）を自動判別。
2.  **スマートな解析ロジック**:
    *   行頭の記号のみでセクションを判定し、文中の記号による誤分割を防止。
    *   ログが終われば即座にコードブロックを閉じ、次の文章へスムーズに移行。
    *   `/help` などのプレーンテキストな結果も、コードブロックで綺麗に表示。
3.  **鉄壁のオーナー専用ガード**:
    *   `.env` に設定したあなたの Discord ID 以外からのメッセージは、DM・メンション含めすべて無視。
4.  **セッション永続化**:
    *   サービス再起動後も、前回使用していた tmux セッションを自動で復元。

## 🛠 動作環境

- **OS**: Linux (Ubuntu 22.04 / 24.04 推奨)
- **依存ツール**: `tmux`, `Node.js (v24+)`, `Python 3.12+`, `systemd`

---

## 🚀 セットアップガイド

### 1. インストール
```bash
python -m venv bot_venv
source bot_venv/bin/activate
pip install -r requirements.txt
```

### 2. 設定 (.env)
`.env` ファイルに以下を設定してね。
```ini
DISCORD_TOKEN=あなたのボットトークン
DISCORD_CHANNEL_ID=反応させたいチャンネルID
MY_DISCORD_ID=あなたのDiscordユーザーID
GEMINI_EXECUTABLE_PATH=gemini
```

---

## 🎮 コマンド体系

### 💡 Gemini CLI への命令
Gemini CLI 自体のコマンドを呼び出すときは、メッセージの先頭に `cmd` を付けるか、`/cmd` スラッシュコマンドを使ってね（`/` は自動で補完されるよ）。

*   **チャット入力**: `cmd help`, `cmd reset`, `cmd status`, `cmd file gemini.md`
*   **スラッシュコマンド**: `/cmd help` など

### ⚙️ ボット自体の管理 (スラッシュコマンド)
*   `/status`: 現在のターゲットセッションを確認。
*   `/sessions`: 稼働中の tmux セッションをリストアップ。
*   `/session [name]`: 指定したセッションに切り替え。
*   `/session_new [name]`: 新規セッション作成 ＆ Gemini 起動。
*   `/session_kill [name]`: セッションを終了。

---

## 📂 ファイル構成

- `main.py`: ボット本体（リアルタイム抽出エンジン）。
- `start.sh`: tmux の準備とボットの起動スクリプト。
- `README.md`: この説明書。
- `.last_session`: 前回のセッション名を保持。

---
Designed with ❤️ by Gemini CLI (YOLO Mode)
