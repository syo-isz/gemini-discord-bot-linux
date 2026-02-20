# gemini-discord-bot-linux

Gemini CLI を Discord から快適・安全・スタイリッシュに操作するためのプライベートブリッジツールです。
公式APIを使用せず、 **裏で稼働する `tmux` セッションの標準出力をリアルタイムにパージしてDiscordに流し込む**という、少し強引でハッカーライクなアプローチを採用しています。

## 🌟 3大特徴

1. **スッキリ実況中継**: ツール実行ログをリアルタイムで抽出。Gemini CLI特有の罫線やUIノイズ（`╭╮╯╰` など）を正規表現で自動消去し、Discord上で美しいテキストとして表示します。
2. **鉄壁のオーナー専用ガード**: `.env` に設定した「あなたのDiscord ID」以外からのメッセージやコマンドを問答無用で無視。DMでもサーバーでも、安全に自分専用のAIとして運用できます。
3. **セッション永続化と分離**: サービス再起動後も、前回使用していた tmux セッションを自動で復元。`/session_new` コマンドで話題ごとにGeminiの記憶（プロセス）を完全に分離して並行稼働できます。

## 🛠 動作環境

- **OS**: Linux (Ubuntu 22.04 / 24.04 推奨)
- **依存ツール**: `tmux`, `Node.js (v24+)`, `Python 3.12+`, `systemd`

---

## 🚀 セットアップガイド (3ステップ)

### 1. 準備とインストール
```bash
# リポジトリをクローンしたディレクトリで実行
python -m venv bot_venv
source bot_venv/bin/activate
pip install -r requirements.txt
```

2. 設定ファイル (.env) の作成
.env.example を .env という名前でコピーし、以下の項目を埋めてください。
⚠️ 注意: .env ファイルには機密情報が含まれます。絶対にGitでコミット・公開しないでください。

```bash
DISCORD_TOKEN=あなたのボットトークン
DISCORD_CHANNEL_ID=反応させたいチャンネルID
MY_DISCORD_ID=あなたのDiscordユーザーID (18桁くらいの数字)
GEMINI_EXECUTABLE_PATH=gemini  # もしフルパスが必要なら "/path/to/gemini"
```

💡 IDの調べ方: Discord の「設定」>「詳細設定」>「開発者モード」を ON にして、自分のアイコンを右クリックして「ユーザーIDをコピー」を選択！

3. 常駐サービス化 (systemd)
以下を ~/.config/systemd/user/gemini-bot.service に保存します（ディレクトリがなければ作成）。
※ WorkingDirectory と ExecStart のパスは、ご自身の環境に合わせて必ず書き換えてください。

3. 常駐サービス化 (systemd)
以下を ~/.config/systemd/user/gemini-bot.service に保存します（ディレクトリがなければ作成）。
※ WorkingDirectory と ExecStart のパスは、ご自身の環境に合わせて必ず書き換えてください。

```bash
[Unit]
Description=Gemini Discord Bot
After=network.target

[Service]
Type=simple
# ↓ ここを自分のリポジトリをクローンした絶対パスに変更する
WorkingDirectory=/path/to/your/gemini-discord-bot
ExecStart=/path/to/your/gemini-discord-bot/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

保存したら、以下のコマンドで起動・自動起動化します！
```bash
systemctl --user daemon-reload
systemctl --user enable --now gemini-bot.service
```

🎮 コマンド一覧 (オーナー専用)
全てのコマンドはスラッシュコマンドとして実装されており、オーナー以外が実行しても無視されます。

/status: 現在操作しているターゲットの tmux セッションを確認。

/session [name]: 指定した tmux セッションに切り替え。

/session_new [name]: 新規セッションを作成 ＆ Gemini CLI を起動。

/sessions: 稼働中の全セッションをリストアップ。

/reset: 現在のセッションの Gemini を Ctrl+C で強制リセット（応答が止まった時用）。

📂 ファイル構成
main.py: ボット本体（実況抽出・パースエンジン）。

start.sh: tmux の準備、PID管理、およびボットの起動スクリプト。

README.md: この説明書。

⚠️ 免責事項 (Known Issues)
このツールは Gemini CLI の標準出力（ターミナルUI）を正規表現で解析しています。そのため、Google側がGemini CLIのプロンプト記号（* や ✦）やレイアウト仕様を変更した場合、出力のパースが崩れる、あるいはBotが応答しなくなる可能性があります。
あくまで個人用のハックツールとしてご利用ください。

📜 ライセンス (License)
This project is licensed under the MIT License - see the LICENSE file for details.
