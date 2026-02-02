import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Cấu hình Bot
intents = discord.Intents.default()
intents.message_content = True


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        # Tự động load các file trong folder 'cogs'
        for filename in os.listdir('./cogs'):
            # CHỈNH SỬA Ở ĐÂY: Thêm điều kiện bỏ qua file __init__.py
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ Đã nạp module: {filename}')
                except Exception as e:
                    print(f'❌ Không thể nạp module {filename}: {e}')

        # Đồng bộ lệnh Slash Command lên server
        try:
            await self.tree.sync()
            print("🔄 Đã đồng bộ Slash Commands!")
        except Exception as e:
            print(f"⚠️ Lỗi đồng bộ lệnh: {e}")

    async def on_ready(self):
        print(f'🤖 {self.user} đã online và sẵn sàng phục vụ!')
        # Set trạng thái hoạt động cho bot
        await self.change_presence(activity=discord.Game(name="/help để xem hướng dẫn"))


bot = MyBot()

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ Lỗi: Chưa có Token trong file .env")