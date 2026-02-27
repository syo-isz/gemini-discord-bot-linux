# Gemini Discord Bot (Real-time Live Streaming Mode)

本プロジェクトは、Gemini CLI の操作を Discord から行えるようにするためのブリッジツールです。
Gemini CLI のターミナル出力をリアルタイムで解析し、Discord メッセージの編集機能（Message Edit）を用いることで、2秒ごとのストリーミング実況表示を実現しています。

## 🌟 主な機能

1.  **リアルタイム実況表示 (Streaming)**
    *   Gemini CLI の出力を 2 秒間隔で取得し、Discord 上のメッセージを動的に更新します。
    *   Gemini が思考し、回答を生成するプロセスをリアルタイムで確認可能です。
2.  **高度な出力解析ロジック**
    *   Gemini の回答（✦ プレフィックス）とツール実行ログ（コードブロック形式）を自動的に判別し、適切に分離して表示します。
    *   行頭記号に基づいたセクション判定により、文中の記号による誤分割を防止します。
    *   ツール実行完了後、即座にコードブロックを閉じて通常の回答へ移行する最適化が行われています。
3.  **セキュリティ機能**
    *   `.env` ファイルで指定された特定の Discord ユーザー ID（オーナー）以外からのメッセージやコマンドをすべて無視します。
4.  **セッションの永続化**
    *   システム再起動後も、直前に使用していた tmux セッションを自動的に復元し、会話を継続できます。

## 🛠 動作環境

- **OS**: Linux (Ubuntu 22.04 / 24.04 推奨)
- **依存ソフトウェア**: `tmux`, `Node.js (v24+)`, `Python 3.12+`, `systemd`

## 🚀 セットアップ手順

### 1. インストール
```bash
# リポジトリのクローン
git clone https://github.com/syo-isz/gemini-discord-bot-linux.git
cd gemini-discord-bot-linux

# 仮想環境の作成とライブラリのインストール
python -m venv bot_venv
source bot_venv/bin/activate
pip install -r requirements.txt
```

### 2. 環境設定 (.env)
`.env` ファイルを作成し、以下の項目を設定してください。
```ini
DISCORD_TOKEN=Your_Discord_Bot_Token
DISCORD_CHANNEL_ID=Target_Channel_ID
MY_DISCORD_ID=Your_Discord_User_ID
GEMINI_EXECUTABLE_PATH=gemini
```

## 🎮 コマンド体系

### Gemini CLI へのコマンド送信
Gemini CLI 内部のコマンドを実行する場合、メッセージの先頭に `cmd` を付与するか、`/cmd` スラッシュコマンドを使用してください（`/` プレフィックスは自動的に補完されます）。

*   **メッセージ入力例**: `cmd help`, `cmd reset`, `cmd file example.md`
*   **スラッシュコマンド**: `/cmd help` など

### ボット管理コマンド (スラッシュコマンド)
*   `/status`: 現在接続中の tmux セッションおよびウィンドウ情報を表示します。
*   `/sessions`: 現在稼働中の tmux セッション一覧を表示します。
*   `/session [name]`: 指定した tmux セッションへ操作対象を切り替えます。
*   `/session_new [name]`: 新規セッションを作成し、Gemini CLI を起動します。
*   `/session_kill [name]`: 指定したセッションを終了します。

## 📂 ファイル構成

- `main.py`: ボット本体（リアルタイム解析・送信エンジン）。
- `start.sh`: tmux のセットアップおよびボットの起動スクリプト。
- `README.md`: 本ドキュメント。
- `.last_session`: 最後に使用したセッション名を記録する永続化ファイル。

---
Designed by Gemini CLI (YOLO Mode)
