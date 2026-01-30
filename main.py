import discord
import os
import asyncio
import ast  # Thư viện phân tích cú pháp
from dotenv import load_dotenv

# --- CẤU HÌNH ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# --- BỘ NHỚ TẠM ---
user_sessions = {}


# --- LỚP PHÂN TÍCH CODE (MINI-PYCHARM ENGINE) ---
class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.defined_vars = set()
        self.used_vars = set()
        self.imported_modules = set()
        # Từ điển lưu kiểu dữ liệu suy luận: {'a': 'str', 'b': 'int'}
        self.var_types = {}

        # 1. Theo dõi biến và Kiểu dữ liệu (Type Inference)

    def visit_Assign(self, node):
        # Lấy kiểu dữ liệu nếu gán trực tiếp (Ví dụ: a = 5)
        inferred_type = None
        if isinstance(node.value, ast.Constant):  # Python 3.8+ dùng Constant cho số/chuỗi
            inferred_type = type(node.value.value).__name__  # 'int', 'str', 'float'...

        for target in node.targets:
            if isinstance(target, ast.Name):
                self.defined_vars.add(target.id)
                if inferred_type:
                    self.var_types[target.id] = inferred_type
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.defined_vars.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.defined_vars.add(alias.asname or alias.name)
        self.generic_visit(node)

    # 2. Kiểm tra sử dụng biến (NameError)
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_vars.add(node.id)
            builtins = {'print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'set', 'input', 'sum', 'min',
                        'max'}
            if node.id not in self.defined_vars and node.id not in builtins:
                self.errors.append(
                    f"⚠️ **Dòng {node.lineno}:** Biến `{node.id}` được sử dụng nhưng chưa được định nghĩa (NameError).")
        self.generic_visit(node)

    # 3. Kiểm tra phép toán (TypeError - Tính năng mới bạn yêu cầu)
    def visit_BinOp(self, node):
        # Kiểm tra phép cộng (+)
        if isinstance(node.op, ast.Add):
            left_type = self._get_node_type(node.left)
            right_type = self._get_node_type(node.right)

            # Nếu cộng Chuỗi với Số -> Lỗi
            if (left_type == 'str' and right_type == 'int') or \
                    (left_type == 'int' and right_type == 'str'):
                self.errors.append(
                    f"❌ **Dòng {node.lineno}:** Lỗi kiểu dữ liệu (TypeError)! Không thể cộng trực tiếp chuỗi (str) với số (int).")

        self.generic_visit(node)

    # Hàm phụ trợ để lấy kiểu của node
    def _get_node_type(self, node):
        if isinstance(node, ast.Name):
            return self.var_types.get(node.id)  # Lấy từ bộ nhớ đã lưu
        elif isinstance(node, ast.Constant):
            return type(node.value).__name__
        return None

    # 4. Kiểm tra bảo mật
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec']:
                self.errors.append(
                    f"🛡️ **Dòng {node.lineno}:** Cảnh báo bảo mật! Không nên dùng hàm `{node.func.id}()`.")
        self.generic_visit(node)


# --- HÀM HỖ TRỢ ---
async def send_help(channel):
    # Đã sửa tiêu đề theo yêu cầu
    embed_msg = discord.Embed(
        title="📚 Bot hỗ trợ học tập",
        description="Danh sách lệnh (không cần dấu !):",
        color=discord.Color.green()
    )
    embed_msg.add_field(name="checkcode", value="Phát hiện lỗi cú pháp và lỗi kiểu dữ liệu (Type Check).", inline=False)
    embed_msg.add_field(name="pomodoro", value="Đồng hồ học tập (có cộng dồn).", inline=False)
    embed_msg.add_field(name="hello", value="Bot chào bạn.", inline=False)
    await channel.send(embed=embed_msg)


# --- SỰ KIỆN CHÍNH ---

@client.event
async def on_ready():
    print(f'Bot {client.user} đã sẵn sàng!')


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    msg = message.content.strip()
    msg_lower = msg.lower()
    user_id = message.author.id

    # 1. LỆNH CƠ BẢN
    if msg_lower == 'hello':
        # Đã sửa câu chào theo yêu cầu
        await message.channel.send(f'Xin chào {message.author.mention}! Chúc bạn một ngày tốt lành.')
        return

    elif msg_lower == 'help':
        await send_help(message.channel)
        return

    # 2. KHỞI ĐỘNG TÍNH NĂNG
    if msg_lower == 'pomodoro':
        if user_id not in user_sessions or user_sessions[user_id].get('type') != 'pomodoro':
            user_sessions[user_id] = {'type': 'pomodoro', 'status': 'waiting_for_time', 'total_minutes': 0}
        await message.channel.send(f"🍅 [Pomodoro] Bạn muốn học hiệp này bao nhiêu phút? (Nhập số)")
        user_sessions[user_id]['status'] = 'waiting_for_time'
        return

    if msg_lower == 'checkcode':
        user_sessions[user_id] = {'type': 'checkcode', 'status': 'waiting_for_code'}
        await message.channel.send("🕵️‍♀️ [Code Inspector] Hãy dán code Python vào đây...")
        return

    # 3. XỬ LÝ LOGIC
    if user_id in user_sessions:
        session = user_sessions[user_id]

        # --- LOGIC POMODORO ---
        if session['type'] == 'pomodoro':
            if session['status'] == 'waiting_for_time':
                if msg.isdigit():
                    minutes = int(msg)
                    session['total_minutes'] += minutes
                    session['status'] = 'studying'
                    await message.channel.send(f"✅ Bắt đầu {minutes} phút tập trung.")
                    await asyncio.sleep(minutes * 60)  # Demo: Nhớ chỉnh nhỏ lại khi test
                    await message.channel.send(f"⏰ {message.author.mention} Hết giờ! Gõ **'nghi'** hoặc **'dung'**.")
                    session['status'] = 'waiting_for_choice'
                else:
                    await message.channel.send("Chỉ nhập số phút thôi nhé.")

            elif session['status'] == 'waiting_for_choice':
                if msg_lower == 'nghi':
                    await message.channel.send("☕ Nghỉ ngơi 5 phút...")
                    await asyncio.sleep(5 * 60)  # Demo: Nhớ chỉnh nhỏ lại
                    await message.channel.send(f"🔔 Hết giờ nghỉ! Nhập số phút để học tiếp.")
                    session['status'] = 'waiting_for_time'
                elif msg_lower == 'dung':
                    total = session['total_minutes']
                    await message.channel.send(f"🎉 Tổng kết hôm nay: **{total} phút**.")
                    del user_sessions[user_id]
                else:
                    await message.channel.send("Chọn **'nghi'** hoặc **'dung'**.")

        # --- LOGIC CHECK CODE (V5 - TYPE CHECK) ---
        elif session['type'] == 'checkcode':
            raw_code = message.content
            if raw_code.startswith('```'):
                lines = raw_code.split('\n')
                if lines[0].startswith('```'): lines = lines[1:]
                if lines[-1].startswith('```'): lines = lines[:-1]
                raw_code = '\n'.join(lines)

            # BƯỚC 1: CHECK CÚ PHÁP
            try:
                tree = ast.parse(raw_code)
            except SyntaxError as e:
                hint = "Kiểm tra cú pháp chung."
                if 'expected' in str(e.msg) and ':' in str(e.msg):
                    hint = "Thiếu dấu hai chấm `:`."
                elif 'indent' in str(e.msg).lower():
                    hint = "Lỗi thụt đầu dòng."
                elif 'EOL' in str(e.msg) or 'EOF' in str(e.msg):
                    hint = "Chưa đóng ngoặc `()` hoặc dấu nháy."

                await message.channel.send(f"🚫 **Lỗi Cú Pháp:** Dòng {e.lineno}: `{e.msg}`\n💡 Gợi ý: {hint}")
                del user_sessions[user_id]
                return

            # BƯỚC 2: CHECK LOGIC & TYPE
            analyzer = CodeAnalyzer()
            analyzer.visit(tree)

            if not analyzer.errors:
                await message.channel.send("✅ **Code Clean!** (Không phát hiện lỗi cú pháp hay lỗi kiểu dữ liệu).")
            else:
                report = "\n".join(analyzer.errors)
                await message.channel.send(f"⚠️ **Phát hiện vấn đề:**\n{report}")

            del user_sessions[user_id]


if TOKEN:
    client.run(TOKEN)