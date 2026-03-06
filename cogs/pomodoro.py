import discord
import asyncio
import random
from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View


# --- CLASS GIAO DIỆN NÚT BẤM ---
class PomodoroView(View):
    def __init__(self, original_user_id):
        super().__init__(timeout=None)
        self.original_user_id = original_user_id
        self.value = None

    async def check_owner(self, interaction: discord.Interaction):
        if interaction.user.id != self.original_user_id:
            await interaction.response.send_message("🚫 Nút này không phải của bạn!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Nghỉ giải lao (5p)", style=discord.ButtonStyle.success, emoji="☕")
    async def break_btn(self, interaction: discord.Interaction, button: Button):
        if not await self.check_owner(interaction): return
        self.value = "nghi"
        await interaction.response.defer()  # Báo cho Discord biết đã nhận lệnh
        self.stop()  # Dừng view để code phía dưới chạy tiếp

    @discord.ui.button(label="Dừng & Tổng kết", style=discord.ButtonStyle.danger, emoji="🛑")
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
        # Set chứa ID những người đang học (Để chặn spam lệnh)
        self.active_sessions = set()

    def create_progress_bar(self, current, total=100, length=10):
        if current > total:
            return "▓" * length + " 🔥 **(OVERLOAD!)**"
        progress = min(current, total)
        filled = int(length * progress / total)
        return "▓" * filled + "░" * (length - filled)

    @app_commands.command(name="pomodoro", description="Đồng hồ học tập (Có đếm ngược & Chống spam)")
    @app_commands.describe(minutes="Thời gian tập trung (phút)")
    async def pomodoro(self, interaction: discord.Interaction, minutes: int):
        user = interaction.user
        # QUAN TRỌNG: Lưu lại kênh chat để gửi tin nhắn sau khi token hết hạn
        channel = interaction.channel

        # 1. KIỂM TRA TRẠNG THÁI (LOCKING)
        if user.id in self.active_sessions:
            await interaction.response.send_message(
                "🚫 **Bạn đang trong một phiên học rồi!**\nHãy hoàn thành hoặc đợi phiên cũ kết thúc.",
                ephemeral=True
            )
            return

        # Khóa user lại
        self.active_sessions.add(user.id)

        if user.id not in self.user_stats:
            self.user_stats[user.id] = 0

        # 2. GIAO DIỆN BẮT ĐẦU
        end_time = datetime.now() + timedelta(minutes=minutes)
        timestamp_str = discord.utils.format_dt(end_time, style='R')

        quotes = ["Focus on being productive instead of busy.", "Code like a pro.", "Stay focused, stay humble."]
        embed_start = discord.Embed(
            title="🍅 POMODORO STARTED",
            description=f"_{random.choice(quotes)}_",
            color=discord.Color.from_rgb(255, 99, 71)
        )
        embed_start.set_thumbnail(url="https://media.giphy.com/media/l0HlOaQcLJ2hHpYcw/giphy.gif")
        embed_start.add_field(name="👤 User", value=user.mention, inline=True)
        embed_start.add_field(name="⏳ Kết thúc", value=f"{timestamp_str}", inline=True)

        # Phản hồi ngay lập tức (Token lúc này vẫn còn sống)
        await interaction.response.send_message(embed=embed_start)

        # Dùng try...finally để đảm bảo dù có lỗi gì thì cũng MỞ KHÓA cho user
        try:
            # Bot ngủ (Logic chạy ngầm)
            await asyncio.sleep(minutes * 60)

            # Cộng điểm
            self.user_stats[user.id] += minutes

            # --- GIAO DIỆN HẾT GIỜ (DÙNG CHANNEL SEND) ---
            view = PomodoroView(original_user_id=user.id)
            embed_end = discord.Embed(
                title="⏰ RENG RENG! HẾT GIỜ",
                description=f"🎉 {user.mention} đã hoàn thành 1 hiệp!",
                color=discord.Color.gold()
            )

            # [FIX LỖI 401]: Thay interaction.followup bằng channel.send
            if channel:
                msg = await channel.send(content=f"🔔 {user.mention}", embed=embed_end, view=view)
            else:
                # Trường hợp hiếm hoi không lấy được channel
                self.active_sessions.remove(user.id)
                return

            # Chờ người dùng bấm nút
            await view.wait()

            # --- XỬ LÝ NÚT BẤM ---
            if view.value == "nghi":
                break_end = datetime.now() + timedelta(minutes=5)
                break_ts = discord.utils.format_dt(break_end, style='R')

                embed_break = discord.Embed(
                    title="☕ GIỜ NGHỈ GIẢI LAO",
                    description=f"Thư giãn đi nhé! Quay lại làm việc {break_ts}.",
                    color=discord.Color.teal()
                )

                # [FIX LỖI 401]: Dùng channel.send
                await channel.send(embed=embed_break)

                # Bot ngủ 5 phút
                await asyncio.sleep(5 * 60)

                # [FIX LỖI 401]: Dùng channel.send
                await channel.send(f"📢 **{user.mention}** Hết giờ nghỉ! Gõ `/pomodoro` để bắt đầu hiệp mới.")

            elif view.value == "dung":
                total = self.user_stats[user.id]
                self.user_stats[user.id] = 0  # Reset sau khi tổng kết

                bar = self.create_progress_bar(total, total=120)
                embed_sum = discord.Embed(
                    title="📊 TỔNG KẾT PHIÊN HỌC",
                    color=discord.Color.green()
                )
                if user.avatar:
                    embed_sum.set_thumbnail(url=user.avatar.url)
                embed_sum.add_field(name="Tổng thời gian", value=f"**{total} phút**", inline=True)
                embed_sum.add_field(name="KPI hôm nay", value=f"`{bar}`", inline=False)

                # [FIX LỖI 401]: Dùng channel.send
                await channel.send(embed=embed_sum)

        except Exception as e:
            print(f"Lỗi Pomodoro: {e}")
            if channel:
                await channel.send(f"⚠️ Có lỗi xảy ra trong phiên của {user.mention}, đã reset trạng thái.")

        finally:
            # QUAN TRỌNG: Luôn mở khóa cho user dù có chuyện gì xảy ra
            if user.id in self.active_sessions:
                self.active_sessions.remove(user.id)


async def setup(bot):
    await bot.add_cog(Pomodoro(bot))