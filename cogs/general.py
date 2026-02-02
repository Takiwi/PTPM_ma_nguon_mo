import discord
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Lệnh /hello
    @app_commands.command(name="hello", description="Gửi lời chào thân thiện")
    async def hello(self, interaction: discord.Interaction):
        # response.send_message thay cho ctx.send
        await interaction.response.send_message(
            f"👋 Xin chào {interaction.user.mention}! Chúc bạn một ngày học tập hiệu quả.")

    # Lệnh /help
    @app_commands.command(name="help", description="Xem hướng dẫn sử dụng bot")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Hướng dẫn sử dụng Bot",
            description="Danh sách các lệnh Slash Command:",
            color=discord.Color.from_rgb(100, 149, 237)  # Màu xanh Cornflower
        )
        embed.add_field(name="/hello", value="Chào hỏi xã giao.", inline=False)
        embed.add_field(name="/pomodoro [số phút]", value="Đồng hồ học tập (Vd: /pomodoro 25).", inline=False)
        embed.add_field(name="/research [từ khóa]", value="Tìm tài liệu, bài báo khoa học.", inline=False)
        embed.set_footer(text="Bot được phát triển bằng PyCharm")

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))