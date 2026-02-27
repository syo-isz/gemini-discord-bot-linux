import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import subprocess
import re
import hashlib
from dotenv import load_dotenv

# Load environment
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DEFAULT_SESSION = os.getenv("TMUX_SESSION_NAME", "gemini-bot")
GEMINI_CMD = os.getenv("GEMINI_EXECUTABLE_PATH", "gemini") + " --y"
MY_DISCORD_ID = os.getenv("MY_DISCORD_ID")
LAST_SESSION_FILE = os.path.join(os.path.dirname(__file__), '.last_session')

# Setup Intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.dm_messages = True

class TmuxGemini:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.sent_messages_hashes = set()
        self.current_session = self._load_last_session()
        self.current_window = "0"
        print(f"INFO: Loaded session '{self.current_session}' from persistence.")

    def _load_last_session(self):
        if os.path.exists(LAST_SESSION_FILE):
            try:
                with open(LAST_SESSION_FILE, 'r') as f:
                    return f.read().strip() or DEFAULT_SESSION
            except:
                pass
        return DEFAULT_SESSION

    def _save_last_session(self, name):
        try:
            with open(LAST_SESSION_FILE, 'w') as f:
                f.write(name)
        except:
            pass

    @property
    def target(self):
        return f"{self.current_session}:{self.current_window}"

    def run_tmux(self, cmd_args):
        try:
            return subprocess.check_output(["tmux"] + cmd_args, stderr=subprocess.STDOUT).decode(errors='ignore')
        except:
            return ""

    async def ensure_active(self):
        check = subprocess.run(["tmux", "has-session", "-t", self.target], capture_output=True)
        if check.returncode != 0:
            # Create session if it doesn't exist, or a new window
            subprocess.run(["tmux", "new-session", "-d", "-s", self.current_session, "-n", "gemini-chat"], capture_output=True)
            await asyncio.sleep(1)
        
        # Ensure proper size for Gemini CLI output
        subprocess.run(["tmux", "resize-pane", "-t", self.target, "-x", "500", "-y", "100"], capture_output=True)
        await asyncio.sleep(1)
        
        # 履歴の最後の方をチェックして、Gemini のプロンプトがあるか確認
        pane_out = self.run_tmux(["capture-pane", "-t", self.target, "-p", "-J"])
        lines = [l.strip() for l in pane_out.splitlines() if l.strip()]
        
        # Gemini のプロンプト (* Type your message...) が見つからない場合は起動を試みる
        has_gemini = any("Type your message" in l or "*" == l[:1] for l in lines[-10:])
        
        if not has_gemini:
            print(f"DEBUG: Gemini prompt not found in {self.target}. Starting Gemini...")
            # Bashの入力をクリアしてから起動
            self.run_tmux(["send-keys", "-t", self.target, "C-c", "C-u"])
            await asyncio.sleep(0.5)
            self.run_tmux(["send-keys", "-t", self.target, GEMINI_CMD, "Enter"])
            # 起動を待つ
            await asyncio.sleep(8)

    async def ask(self, prompt, channel):
        async with channel.typing():
            async with self.lock:
                await self.ensure_active()
                
                # 入力行をクリア
                print(f"DEBUG: Clearing line in {self.target}")
                self.run_tmux(["send-keys", "-t", self.target, "C-c", "C-u"])
                await asyncio.sleep(1.0) 
                
                # 文字を送信
                print(f"DEBUG: Sending to tmux: {prompt}")
                # 特殊文字による誤動作を防ぐため、文字列をそのまま送る
                subprocess.run(["tmux", "send-keys", "-t", self.target, "-l", prompt])
                await asyncio.sleep(0.8) 
                
                # 実行（Enter を確実に叩く）
                self.run_tmux(["send-keys", "-t", self.target, "C-m"])
                await asyncio.sleep(0.5)
                
                last_pane = ""
                stable_count = 0
                msg_handles = [] 
                
                # 送信直後の状態を保存
                initial_pane = self.run_tmux(["capture-pane", "-t", self.target, "-p", "-J", "-S", "-500"])

                await asyncio.sleep(2)  # 初期思考待ち
                for i in range(200):     # 最大400秒待機
                    await asyncio.sleep(2)
                    pane_out = self.run_tmux(["capture-pane", "-t", self.target, "-p", "-J", "-S", "-500"])
                    if not pane_out.strip(): continue
                    
                    if pane_out == last_pane:
                        stable_count += 1
                    else:
                        stable_count = 0
                        last_pane = pane_out
                    
                    # 変化がない場合は、初期状態（送信直後）からも変化がないかチェック
                    # これにより、コマンドが全く受け付けられなかった場合を検知できる
                    if stable_count > 5 and pane_out == initial_pane:
                        print(f"DEBUG: No change detected from initial state for {prompt}. Retrying Enter...")
                        self.run_tmux(["send-keys", "-t", self.target, "C-m"])
                        stable_count = 0
                        continue
                    
                    # 抽出（最新の状態を反映）
                    current_responses = self._extract_latest_responses(pane_out, prompt)
                    
                    # リアルタイム送信/編集ロジック
                    for idx in range(len(current_responses)):
                        content = current_responses[idx]
                        fixed_content = self._fix_japanese_line_breaks(content) if "✦" in content else content
                        
                        # まだこのインデックスのメッセージを送っていない場合
                        if idx >= len(msg_handles):
                            # 新規送信
                            h = await channel.send(fixed_content[:2000])
                            msg_handles.append(h)
                        else:
                            # 既存メッセージの更新（内容が変わっている場合のみ）
                            if msg_handles[idx].content != fixed_content[:2000]:
                                try:
                                    await msg_handles[idx].edit(content=fixed_content[:2000])
                                except:
                                    pass # 削除されていた場合など
                    
                    # 完了判定
                    has_prompt = any(l.strip().startswith("*") for l in pane_out.splitlines()[-5:])
                    if has_prompt and stable_count >= 1:
                        print(f"DEBUG: Finished because prompt detected.")
                        break
                    if stable_count >= 40: # 80秒停止でタイムアウト
                        print(f"DEBUG: Finished because stable for 80s.")
                        break
                
                if not msg_handles:
                    await channel.send("（応答を抽出できませんでした）")
                else:
                    print(f"DEBUG: Interaction complete. Sent {len(msg_handles)} chunks.")

    def _fix_japanese_line_breaks(self, text):
        # ターミナル幅を 500 に広げたため、基本的には改行を尊重する
        # 余計な連結はせず、Gemini の意図したレイアウトを維持
        return text.strip()

    def _extract_latest_responses(self, pane_text, user_input):
        parts = pane_text.splitlines()
        
        # 🚨 ユーザーの入力をより確実にスキップする
        start_line = 0
        search_term = user_input.splitlines()[0][:15] if user_input.splitlines() else user_input[:15]
        
        # 後ろからスキャンして、最新の（一番下にある）ユーザー入力を探す
        for idx in range(len(parts) - 1, -1, -1):
            line = parts[idx]
            clean_l = re.sub(r'\x1b\[[0-9;]*[mK]', '', line)
            
            if search_term in clean_l:
                is_prompt = False
                if clean_l.strip().startswith(">") or clean_l.strip().startswith("*") or ("> " + search_term in clean_l):
                    is_prompt = True
                
                if is_prompt:
                    potential_start = idx
                    # プロンプト自体の続きをスキップし、最初の出力を探す
                    for j in range(potential_start + 1, len(parts)):
                        clean_j = re.sub(r'\x1b\[[0-9;]*[mK]', '', parts[j])
                        if "✦" in clean_j or any(c in clean_j for c in "─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰"):
                            start_line = j
                            break
                    if start_line: break
        
        if not start_line: return []
        
        content_lines = parts[start_line:]
        res = []
        current_chunk = []
        is_log_mode = False
        
        ui_bars = ["▀▀", "▄▄", "███", "░░░", "Type your message", "shortcuts", "skills"]
        
        for line in content_lines:
            clean_line = re.sub(r'\x1b\[[0-9;]*[mK]', '', line)
            if any(bar in clean_line for bar in ui_bars): continue

            stripped_line = clean_line.lstrip()
            # ✦ が行の先頭（または空白の後）にあるか
            has_sparkle_at_start = stripped_line.startswith("✦")
            # 新しいボックスの開始記号が行の先頭にあるか
            is_new_box_at_start = stripped_line.startswith(("┌", "╭", "╔"))
            # 罫線全般（継続判定用）
            is_box_line = any(c in clean_line for c in "─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰")
            
            # 1. 新しい ✦ セクションが「行の先頭で」始まった場合
            if has_sparkle_at_start:
                if current_chunk:
                    text = "\n".join(current_chunk)
                    if is_log_mode:
                        clean = self._clean_output(text, preserve_layout=True)
                        if clean: res.append("```\n" + clean + "\n```")
                    else:
                        clean = self._clean_output(text)
                        if clean: res.append("✦ " + clean)
                
                sparkle_idx = clean_line.find("✦")
                current_chunk = [clean_line[sparkle_idx+1:]]
                is_log_mode = False
                continue
            
            # 2. 新しいボックスが「行の先頭で」始まった場合
            if is_new_box_at_start:
                if current_chunk:
                    text = "\n".join(current_chunk)
                    if is_log_mode:
                        clean = self._clean_output(text, preserve_layout=True)
                        if clean: res.append("```\n" + clean + "\n```")
                    else:
                        clean = self._clean_output(text)
                        if clean: res.append("✦ " + clean)
                current_chunk = [line]
                is_log_mode = True
                continue
            
            # 3. ボックス（ログ）継続判定
            if is_box_line:
                if not is_log_mode:
                    if current_chunk:
                        text = "\n".join(current_chunk)
                        clean = self._clean_output(text)
                        if clean: res.append("✦ " + clean)
                    current_chunk = [line]
                    is_log_mode = True
                else:
                    current_chunk.append(line)
                continue
            
            # 4. ボックスの終了判定（罫線がない行が来た場合）
            if is_log_mode:
                # ログモード中に罫線がない行が来たら、即座にログを閉じる
                if current_chunk:
                    text = "\n".join(current_chunk)
                    clean = self._clean_output(text, preserve_layout=True)
                    if clean: res.append("```\n" + clean + "\n```")
                current_chunk = [line]
                is_log_mode = False
                continue

            # 5. 通常のテキスト
            # ✦ がなくても、プロンプト後の最初のテキストセクションとして扱う
            current_chunk.append(line)
            
        if current_chunk:
            text = "\n".join(current_chunk)
            if is_log_mode:
                clean = self._clean_output(text, preserve_layout=True)
                if clean: res.append("```\n" + clean + "\n```")
            else:
                clean = self._clean_output(text)
                # ✦ が含まれていないプレーンテキスト（/helpなど）の場合は、コードブロックで囲うと見やすい
                if clean:
                    if "✦" not in text:
                        res.append("```\n" + clean + "\n```")
                    else:
                        res.append("✦ " + clean)
                
        return [r for r in res if r.strip()]

    def _clean_output(self, text, preserve_layout=False):
        # UI ornaments and box characters to strip
        ignore = ["Type your message", "Press Ctrl+C", "no sandbox", "Update available", "shortcuts", "YOLO", "skills", "file |", "▀▀", "▄▄", "███", "░░░"]
        
        lines = text.splitlines()
        result = []
        for l in lines:
            if any(p in l for p in ignore): continue
            
            # Remove ANSI color codes
            clean_l = re.sub(r'\x1b\[[0-9;]*[mK]', '', l)
            
            # 🚨 枠線（罫線）を徹底的に消す！（丸い角 ╭╮╯╰ も追加！）
            clean_l = re.sub(r'[─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰]', '', clean_l)
            
            if not preserve_layout:
                clean_l = clean_l.strip()
            else:
                # ログモードの時は、右側の空白だけ消してインデントは守る
                clean_l = clean_l.rstrip()
                
            if clean_l.strip(): # 中身がある行だけを採用
                result.append(clean_l)
        
        return "\n".join(result).strip()

tmux_gemini = TmuxGemini()

class GeminiBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Synced slash commands.")

bot = GeminiBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await tmux_gemini.ensure_active()
    print('Ready! (Slash Commands Active)')

def is_owner():
    def predicate(interaction: discord.Interaction):
        return MY_DISCORD_ID and str(interaction.user.id) == str(MY_DISCORD_ID)
    return app_commands.check(predicate)

@bot.tree.command(name="sessions", description="稼働中の tmux セッション一覧を表示するよ")
@is_owner()
async def sessions(interaction: discord.Interaction):
    try:
        out = subprocess.check_output(["tmux", "ls"], stderr=subprocess.STDOUT).decode(errors='ignore')
        if not out.strip():
            await interaction.response.send_message("ℹ️ 稼働中の tmux セッションはありません。")
        else:
            await interaction.response.send_message(f"📋 **稼働中のセッション一覧:**\n```\n{out.strip()}\n```")
    except subprocess.CalledProcessError:
        await interaction.response.send_message("⚠️ tmux セッションが見つかりませんでした。")

@bot.tree.command(name="session_new", description="新しい tmux セッションを作成して Gemini を起動するよ")
@app_commands.describe(name="新しいセッション名")
@is_owner()
async def session_new(interaction: discord.Interaction, name: str):
    await interaction.response.defer()
    check = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True)
    if check.returncode == 0:
        await interaction.followup.send(f"⚠️ セッション `{name}` は既に存在しているよ。")
        return
    
    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-n", "gemini-chat"], capture_output=True)
    await asyncio.sleep(1)
    subprocess.run(["tmux", "send-keys", "-t", f"{name}:0", GEMINI_CMD, "Enter"], capture_output=True)
    
    tmux_gemini.current_session = name
    tmux_gemini.current_window = "0"
    tmux_gemini._save_last_session(name)
    await interaction.followup.send(f"🚀 新しいセッション `{name}` を作成して、Gemini を起動したよ！ターゲットも切り替えたよ。")

@bot.tree.command(name="session_kill", description="指定した tmux セッションを終了させるよ")
@app_commands.describe(name="終了させるセッション名")
@is_owner()
async def session_kill(interaction: discord.Interaction, name: str):
    check = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True)
    if check.returncode != 0:
        await interaction.response.send_message(f"⚠️ セッション `{name}` は見つからなかったよ。")
        return
    
    subprocess.run(["tmux", "kill-session", "-t", name], capture_output=True)
    await interaction.response.send_message(f"💥 セッション `{name}` を終了させたよ。")

@bot.tree.command(name="status", description="今のセッション情報を確認するよ")
@is_owner()
async def status(interaction: discord.Interaction):
    await interaction.response.send_message(f"ℹ️ 現在のターゲット: `{tmux_gemini.target}`")

@bot.tree.command(name="session", description="ターゲットにする tmux セッションを切り替えるよ")
@app_commands.describe(name="セッション名", window="ウィンドウ番号 (省略可)")
@is_owner()
async def session(interaction: discord.Interaction, name: str, window: str = "0"):
    tmux_gemini.current_session = name
    tmux_gemini.current_window = window
    tmux_gemini._save_last_session(name)
    await interaction.response.send_message(f"✅ ターゲットを `{tmux_gemini.target}` に切り替えたよ！")
    await tmux_gemini.ensure_active()

@bot.tree.command(name="cmd", description="Gemini CLI にコマンドを送信するよ (自動で / が付きます)")
@app_commands.describe(command="送信するコマンド (例: reset, help, file gemini.md)")
@is_owner()
async def cmd(interaction: discord.Interaction, command: str):
    # 頭に / がなければ付ける
    gemini_cmd = command if command.startswith("/") else f"/{command}"
    await interaction.response.send_message(f"⌨️ Gemini コマンド実行: `{gemini_cmd}`")
    await tmux_gemini.ask(gemini_cmd, interaction.channel)

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # 🚨 セキュリティガード：自分以外のユーザーからのメッセージは無視する
    if MY_DISCORD_ID and str(message.author.id) != str(MY_DISCORD_ID):
        print(f"SECURITY: Ignored message from unauthorized user {message.author} (ID: {message.author.id})")
        return

    print(f"DEBUG: Message from {message.author} in {message.channel.id}: {message.content}")
    # DM、メンション、または指定された特定のチャンネルでの発言に反応
    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user.mentioned_in(message)
    target_channel_id = os.getenv("DISCORD_CHANNEL_ID")
    is_target_channel = str(message.channel.id) == str(target_channel_id)
    
    if not (is_dm or is_mentioned or is_target_channel): return
    
    content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
    if not content: return
    
    # ✦ cmd xxx 形式のコマンド処理
    if content.lower().startswith("cmd "):
        cmd_part = content[4:].strip()
        if cmd_part:
            gemini_cmd = cmd_part if cmd_part.startswith("/") else f"/{cmd_part}"
            print(f"DEBUG: Command detected in message, sending: {gemini_cmd}")
            await tmux_gemini.ask(gemini_cmd, message.channel)
            return

    await tmux_gemini.ask(content, message.channel)

def main():
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found.")
        return
    if not MY_DISCORD_ID:
        print("Error: MY_DISCORD_ID not found in .env. Security risk. Exiting.")
        return
    bot.run(DISCORD_TOKEN)

if __name__ == '__main__':
    main()
