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
            subprocess.run(["tmux", "new-window", "-t", self.current_session, "-n", "gemini-chat", "-k"], capture_output=True)
            await asyncio.sleep(1)
        
        # Ensure proper size for Gemini CLI output
        subprocess.run(["tmux", "resize-pane", "-t", self.target, "-x", "500", "-y", "100"], capture_output=True)
        await asyncio.sleep(1)
        
        pane_out = self.run_tmux(["capture-pane", "-t", self.target, "-p"])
        if "*" not in pane_out:
            self.run_tmux(["send-keys", "-t", self.target, "C-c", "C-u"])
            self.run_tmux(["send-keys", "-t", self.target, GEMINI_CMD, "Enter"])
            # Initial launch takes some time
            await asyncio.sleep(8)

    async def ask(self, prompt, channel):
        async with channel.typing():
            async with self.lock:
                await self.ensure_active()
                
                # Clear line and send prompt
                print(f"DEBUG: Sending to tmux: {prompt}")
                self.run_tmux(["send-keys", "-t", self.target, "C-c", "C-u"])
                await asyncio.sleep(0.5)
                subprocess.run(["tmux", "send-keys", "-t", self.target, "-l", prompt])
                await asyncio.sleep(0.2)
                self.run_tmux(["send-keys", "-t", self.target, "Enter"])
                
                last_pane = ""
                stable_count = 0
                sent_chunks_count = 0
                await asyncio.sleep(5)  # Wait for initial thinking
                for i in range(90):     # Increased wait for Thinking models
                    await asyncio.sleep(2)
                    pane_out = self.run_tmux(["capture-pane", "-t", self.target, "-p", "-J"])
                    if not pane_out.strip(): continue
                    
                    if pane_out == last_pane: stable_count += 1
                    else:
                        stable_count = 0
                        last_pane = pane_out
                    
                    # Try to extract intermediate responses
                    current_responses = self._extract_latest_responses(pane_out, prompt)
                    
                    # If we have multiple ✦ chunks and there are completed ones we haven't sent, send them
                    if len(current_responses) > sent_chunks_count + 1:
                        for idx in range(sent_chunks_count, len(current_responses) - 1):
                            resp = current_responses[idx]
                            fixed_resp = self._fix_japanese_line_breaks(resp)
                            for chunk in [fixed_resp[j:j+2000] for j in range(0, len(fixed_resp), 2000)]:
                                await channel.send(chunk)
                            sent_chunks_count += 1

                    # Detect prompt char (*) at the end of output
                    has_prompt = any(l.strip().startswith("*") for l in pane_out.splitlines()[-5:])
                    
                    # Try to extract intermediate responses
                    current_responses = self._extract_latest_responses(pane_out, prompt)
                    
                    # 🚀 送信条件の改善：
                    # 1. すでに次のチャンクが始まっている
                    # 2. すべての処理が終了した
                    # 3. 最後のチャンクが安定して止まった (安定回数 4回 = 約8秒)
                    is_ready_to_send = (len(current_responses) > sent_chunks_count + 1) or \
                                      (has_prompt and len(current_responses) > sent_chunks_count) or \
                                      (len(current_responses) > sent_chunks_count and stable_count >= 4)

                    if is_ready_to_send:
                        # まだ送っていないチャンクをすべて送る
                        end_idx = len(current_responses) if (has_prompt or stable_count >= 4) else len(current_responses) - 1
                        
                        for idx in range(sent_chunks_count, end_idx):
                            resp = current_responses[idx]
                            fixed_resp = self._fix_japanese_line_breaks(resp) if "✦" in resp else resp
                            for chunk in [fixed_resp[j:j+2000] for j in range(0, len(fixed_resp), 2000)]:
                                await channel.send(chunk)
                            sent_chunks_count += 1

                    if has_prompt and stable_count >= 1: break
                    if stable_count >= 15: break # 余裕を持って待つ
                
                if sent_chunks_count == 0:
                    await channel.send("（新しい応答を抽出できませんませんでした。Gemini が思考中のままか、プロンプトが認識されていない可能性があります）")
                else:
                    print(f"DEBUG: Successfully sent {sent_chunks_count} chunks.")

    def _fix_japanese_line_breaks(self, text):
        # ターミナル幅を 500 に広げたため、基本的には改行を尊重する
        # 余計な連結はせず、Gemini の意図したレイアウトを維持
        return text.strip()

    def _extract_latest_responses(self, pane_text, user_input):
        parts = pane_text.splitlines()
        
        # 🚨 ユーザーの入力をより確実にスキップする
        # プロンプトが終わった後の、最初の「✦」か「罫線」が始まる行を探す
        start_line = 0
        search_term = user_input.splitlines()[0][:15] if user_input.splitlines() else user_input[:15]
        
        for idx, line in enumerate(reversed(parts)):
            if search_term in line:
                # ユーザーのプロンプト行が見つかったら、そこから下をスキャン
                potential_start = len(parts) - idx - 1
                # プロンプト自体の続き（複数行）をスキップするために、最初の有効な出力を探す
                for j in range(potential_start + 1, len(parts)):
                    clean_j = re.sub(r'\x1b\[[0-9;]*[mK]', '', parts[j])
                    if "✦" in clean_j or any(c in clean_j for c in "─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰"):
                        start_line = j
                        break
                if start_line: break
        
        content_lines = parts[start_line:]
        if not content_lines: return []
        
        res = []
        current_chunk = []
        is_log_mode = False
        
        # UI ornaments to ignore
        ui_bars = ["▀▀", "▄▄", "███", "░░░", "Type your message", "shortcuts", "skills"]
        
        for line in content_lines:
            clean_line = re.sub(r'\x1b\[[0-9;]*[mK]', '', line)
            
            # Detect box/log characters
            is_box_line = any(c in clean_line for c in "─│┌┐└┘├┤┬┴┼═║╔╗╚╝╠╣╦╩╬╭╮╯╰")
            has_sparkle = "✦" in clean_line
            is_ornament = any(bar in clean_line for bar in ui_bars)
            
            if has_sparkle:
                if current_chunk:
                    chunk_text = "\n".join(current_chunk)
                    if is_log_mode:
                        clean = self._clean_output(chunk_text, preserve_layout=True)
                        if clean: res.append("```\n" + clean + "\n```")
                    else:
                        clean = self._clean_output(chunk_text)
                        if clean: res.append("✦ " + clean)
                
                sparkle_idx = clean_line.find("✦")
                current_chunk = [clean_line[sparkle_idx+1:]]
                is_log_mode = False
                continue
            
            if is_box_line:
                if not is_log_mode:
                    if current_chunk:
                        chunk_text = "\n".join(current_chunk)
                        clean = self._clean_output(chunk_text)
                        if clean: res.append("✦ " + clean)
                    current_chunk = [line]
                    is_log_mode = True
                else:
                    current_chunk.append(line)
                continue

            if is_ornament: continue
            current_chunk.append(line)
            
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            if is_log_mode:
                clean = self._clean_output(chunk_text, preserve_layout=True)
                if clean: res.append("```\n" + clean + "\n```")
            else:
                clean = self._clean_output(chunk_text)
                if clean: res.append("✦ " + clean)
                
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
    # セッションが存在するかチェック
    check = subprocess.run(["tmux", "has-session", "-t", name], capture_output=True)
    if check.returncode == 0:
        await interaction.followup.send(f"⚠️ セッション `{name}` は既に存在しているよ。")
        return
    
    # 新規作成
    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-n", "gemini-chat"], capture_output=True)
    await asyncio.sleep(1)
    # Gemini 起動
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

@bot.tree.command(name="gemini_stop", description="今のセッションで動いている Gemini CLI を終了させるよ")
@is_owner()
async def gemini_stop(interaction: discord.Interaction):
    target = tmux_gemini.target
    # /quit を送って綺麗に終了させる
    subprocess.run(["tmux", "send-keys", "-t", target, "/quit", "Enter"], capture_output=True)
    await interaction.response.send_message(f"👋 `{target}` の Gemini CLI に終了コマンドを送ったよ。")

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
    # 必要に応じて初期化
    await tmux_gemini.ensure_active()

@bot.tree.command(name="reset", description="今のセッションの Gemini CLI を再起動するよ")
@is_owner()
async def reset(interaction: discord.Interaction):
    await interaction.response.defer()
    tmux_gemini.sent_messages_hashes.clear()
    subprocess.run(["tmux", "send-keys", "-t", tmux_gemini.target, "C-c", "C-u", GEMINI_CMD, "Enter"])
    await asyncio.sleep(5)
    await interaction.followup.send(f"✅ `{tmux_gemini.target}` の Gemini をリセットしたよ。")

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # 🚨 セキュリティガード：自分以外のユーザーからのメッセージは無視する
    if MY_DISCORD_ID and str(message.author.id) != str(MY_DISCORD_ID):
        # ログには残しておくと、誰かが勝手に使おうとしたかわかって便利かも
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
    if not content or content.startswith("!"): return
    
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
