import discord
from discord import app_commands
from discord.ext import commands
import datetime

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- LỆNH 1: /HELLO ---
    @app_commands.command(name="hello", description="Gửi lời chào tới Bot")
    async def hello(self, interaction: discord.Interaction):
        hour = datetime.datetime.now().hour
        if 5 <= hour < 11:
            buoi = "buổi sáng"
            chuc = "chúc bạn một ngày mới đầy năng lượng! 🌅"
        elif 11 <= hour < 14:
            buoi = "buổi trưa"
            chuc = "nhớ nghỉ ngơi và ăn uống đầy đủ nhé! 🍱"
        elif 14 <= hour < 18:
            buoi = "buổi chiều"
            chuc = "cố gắng hoàn thành nốt deadline nhé! 🌇"
        else:
            buoi = "buổi tối"
            chuc = "thư giãn nhẹ nhàng thôi nhé! 🌙"

        await interaction.response.send_message(
            f"👋 Chào **{interaction.user.display_name}**! Bây giờ là {buoi}, {chuc}")

    # --- LỆNH 2: /HELP (Cập nhật đầy đủ tính năng) ---
    @app_commands.command(name="help", description="Xem danh sách các công cụ")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📘 MENU HỌC TẬP THÔNG MINH",
            description=f"Chào **{interaction.user.display_name}**! Dưới đây là bộ công cụ hỗ trợ bạn:",
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2997/2997295.png")

        # 1. AI & TRỢ LÝ (MỚI)
        embed.add_field(
            name="🤖 AI & TRỢ LÝ ẢO",
            value=(
                "**`/explain [ngành] [khái niệm]`**\n> 🧠 Giải thích khái niệm khó hiểu siêu đơn giản (Gemini).\n"
                "**`/research [chủ đề]`**\n> 🔎 Tìm kiếm tài liệu, giáo trình."
            ),
            inline=False
        )

        # 2. QUẢN LÝ
        embed.add_field(
            name="⏱️ QUẢN LÝ & KPI",
            value=(
                "**`/pomodoro [phút]`**\n> 🍅 Đồng hồ đếm ngược, tính KPI thời gian học.\n"
                "**`/todo`**\n> 🗂️ Dashboard quản lý Dự án & Task."
            ),
            inline=False
        )

        # 3. ÔN TẬP (FLASHCARD ĐẦY ĐỦ)
        embed.add_field(
            name="🧠 FLASHCARD (GHI NHỚ CHỦ ĐỘNG)",
            value=(
                "**`/flashcard_add`**\n> Thêm thẻ mới nhanh chóng.\n"
                "**`/flashcard_manage [topic]`**\n> 🛠️ **Quản lý:** Duyệt, sửa, xóa thẻ bằng nút bấm.\n"
                "**`/flashcard_review [topic]`**\n> 🃏 **Học bài:** Chế độ lật thẻ (Active Recall).\n"
                "**`/flashcard_list`**\n> Xem danh sách các môn đã tạo.\n"
                "**`/flashcard_delete_topic`**\n> Xóa vĩnh viễn một chủ đề.\n"
            ),
            inline=False
        )

        # 4. NGOẠI NGỮ
        embed.add_field(
            name="🌍 NGOẠI NGỮ",
            value=(
                "**`/word`**\n> 🇬🇧 Học từ vựng Tiếng Anh mỗi ngày."
            ),
            inline=False
        )

        embed.set_footer(text="Gõ lệnh để trải nghiệm ngay!",
                         icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.timestamp = datetime.datetime.now()

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))