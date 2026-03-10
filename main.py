import discord
import os
import traceback
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.all()


class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        print("\n--- ĐANG NẠP MODULES ---")

        # 1. Tìm đường dẫn tuyệt đối
        current_dir = os.path.dirname(os.path.abspath(__file__))
        cogs_dir = os.path.join(current_dir, 'cogs')

        if not os.path.exists(cogs_dir):
            print(f"LỖI: Không tìm thấy thư mục tại: {cogs_dir}")
            return

        # 2. Nạp từng file và bắt lỗi chi tiết
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'Đã nạp: {filename}')
                except Exception as e:
                    print(f'LỖI KHI NẠP {filename}')
                    traceback.print_exc()

        print("--------------------------")
        # Lưu ý: Không sync global ở đây nữa để tránh bị rate limit khi restart nhiều lần.
        # Chúng ta sẽ dùng lệnh !sync thủ công.

    async def on_ready(self):
        print(f'\n🤖 {self.user} ĐÃ ONLINE!')
        print("HƯỚNG DẪN: Vào Discord gõ lệnh '!sync' để cập nhật menu.")
        await self.change_presence(activity=discord.Game(name="!sync để update lệnh"))


bot = MyBot()


# --- [FIX QUAN TRỌNG] LỆNH SYNC CỤC BỘ ---
# Lệnh này giúp menu hiện ra NGAY LẬP TỨC
@bot.command()
async def sync(ctx):
    msg = await ctx.send("Đang ép đồng bộ lệnh vào Server này (Guild Sync)...")
    try:
        # 1. Xóa lệnh cũ (để tránh trùng lặp ảo)
        bot.tree.clear_commands(guild=ctx.guild)

        # 2. Copy lệnh từ code vào server hiện tại
        bot.tree.copy_global_to(guild=ctx.guild)

        # 3. Đồng bộ
        synced = await bot.tree.sync(guild=ctx.guild)

        await msg.edit(
            content=f"**THÀNH CÔNG!** Đã cập nhật {len(synced)} lệnh vào Server: **{ctx.guild.name}**.\n => Bạn hãy gõ thử `/explain` xem nhé!")
    except Exception as e:
        await msg.edit(content=f"Lỗi: {e}")


if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("LỖI: Thiếu Token trong .env")