import discord
import asyncio
import random
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View


# --- CLASS GIAO DIỆN NÚT BẤM ---
class PomodoroView(View):
    def __init__(self, original_user_id, session_data):
        super().__init__(timeout=None)
        self.original_user_id = original_user_id
        self.session_data = session_data
        self.value = None

    async def check_owner(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_user_id:
            # Giao diện báo lỗi cũng phải đẹp
            embed = discord.Embed(
                description="🚫 **Nút này không phải của bạn!**\nHãy tự tạo phòng học riêng bằng lệnh `/pomodoro`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Nghỉ giải lao (5p)", style=discord.ButtonStyle.success, emoji="☕")
    async def break_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_owner(interaction): return
        self.value = "nghi"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Dừng & Tổng kết", style=discord.ButtonStyle.secondary, emoji="🛑")
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_owner(interaction): return
        self.value = "dung"
        await interaction.response.defer()
        self.stop()


# --- CLASS COG CHÍNH ---
class Pomodoro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.user_stats = {}

    # Hàm tạo thanh tiến độ (Visual Trick)
    def create_progress_bar(self, current, total=100, length=10):
        # Ví dụ: ▓▓▓▓▓░░░░░
        progress = min(current, total)
        filled = int(length * progress / total)
        bar = "▓" * filled + "░" * (length - filled)
        return bar

    @app_commands.command(name="pomodoro", description="Đồng hồ học tập giao diện Premium")
    @app_commands.describe(minutes="Thời gian tập trung (phút)")
    async def pomodoro(self, interaction: discord.Interaction, minutes: int):
        user = interaction.user
        if user.id not in self.user_stats:
            self.user_stats[user.id] = 0

        # --- GIAO DIỆN 1: BẮT ĐẦU (MÀU ĐỎ CÀ CHUA) ---
        quotes = [
            "Sự tập trung là chìa khóa của mọi thành công.",
            "Một giờ hăng say hơn một ngày chiếu lệ.",
            "Keep pushing! You got this!",
            "Code hard, Play hard."
        ]

        embed_start = discord.Embed(
            title="🍅 POMODORO TIMER STARTED",
            description=f"_{random.choice(quotes)}_",  # Chữ nghiêng
            color=discord.Color.from_rgb(255, 99, 71)  # Màu đỏ cà chua chuẩn
        )

        # Trang trí thông tin
        embed_start.add_field(name="👤 User", value=f"**{user.display_name}**", inline=True)
        embed_start.add_field(name="⏳ Thời gian", value=f"**{minutes} phút**", inline=True)
        embed_start.add_field(name="🎯 Trạng thái", value="`Đang tập trung...`", inline=False)

        # Thêm Thumbnail (Ảnh nhỏ bên góc)
        embed_start.set_thumbnail(url="https://media.giphy.com/media/l0HlOaQcLJ2hHpYcw/giphy.gif")  # Gif đồng hồ cát
        embed_start.set_footer(text="Bot sẽ thông báo khi hết giờ. Hãy tắt thông báo MXH đi nhé!")

        await interaction.response.send_message(embed=embed_start)

        # Đếm ngược
        await asyncio.sleep(minutes * 60)

        self.user_stats[user.id] += minutes

        # --- GIAO DIỆN 2: HẾT GIỜ (MÀU VÀNG NHẮC NHỞ) ---
        view = PomodoroView(original_user_id=user.id, session_data=self.user_stats)

        embed_end = discord.Embed(
            title="⏰ RENG RENG! HẾT GIỜ RỒI",
            description=f"🎉 Chúc mừng **{user.mention}** đã hoàn thành 1 hiệp!",
            color=discord.Color.gold()
        )
        embed_end.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/857/857681.png")  # Icon chuông
        embed_end.add_field(name="Tiếp theo làm gì?", value="Chọn một nút bên dưới để tiếp tục:", inline=False)

        msg = await interaction.followup.send(content=f"🔔 {user.mention}", embed=embed_end, view=view)

        await view.wait()

        # --- GIAO DIỆN 3: XỬ LÝ NÚT BẤM ---

        if view.value == "nghi":
            # Embed Nghỉ ngơi (Màu Xanh Mint thư giãn)
            embed_break = discord.Embed(
                title="☕ BREAK TIME (5 PHÚT)",
                description="Đứng dậy, vươn vai và uống chút nước nhé!",
                color=discord.Color.teal()
            )
            embed_break.set_image(
                url="https://media.giphy.com/media/13HgwGsXf0aiGY/giphy.gif")  # Gif mèo uống cafe chill

            await interaction.followup.send(embed=embed_break)
            await asyncio.sleep(5 * 60)  # Chờ nghỉ

            # Thông báo hết giờ nghỉ
            await interaction.followup.send(
                f"📢 **{user.mention}** Hết giờ nghỉ rồi! Gõ `/pomodoro` để chiến tiếp hiệp sau.")

        elif view.value == "dung":
            total = self.user_stats[user.id]
            self.user_stats[user.id] = 0

            # Embed Tổng kết (Giao diện Báo cáo xịn xò)
            bar = self.create_progress_bar(total, total=120)  # Giả sử mục tiêu ngày là 120p

            embed_sum = discord.Embed(
                title="📊 BÁO CÁO PHIÊN HỌC",
                color=discord.Color.from_rgb(50, 205, 50)  # Màu xanh lá đậm
            )
            embed_sum.set_thumbnail(url=user.display_avatar.url)  # Lấy avatar của người dùng

            embed_sum.add_field(name="Người dùng", value=user.mention, inline=True)
            embed_sum.add_field(name="Tổng thời gian tích lũy", value=f"**{total} phút**", inline=True)

            # Thanh Level giả lập
            embed_sum.add_field(name="Năng suất hôm nay", value=f"`{bar}` {total}/120p", inline=False)

            embed_sum.set_footer(text="Great job! See you next time.")

            await interaction.followup.send(embed=embed_sum)


async def setup(bot):
    await bot.add_cog(Pomodoro(bot))