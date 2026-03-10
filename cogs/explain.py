import discord
import os
import asyncio
import traceback
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Thử import thư viện
try:
    from google import genai
    from google.genai import types
    HAS_LIB = True
except ImportError:
    HAS_LIB = False
    print("[EXPLAIN] LỖI: Chưa cài thư viện 'google-genai'.")

load_dotenv()
GOOGLE_API_KEY = os.getenv('GEMINI_API_KEY')


class Explain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if HAS_LIB and GOOGLE_API_KEY:
            try:
                self.client = genai.Client(api_key=GOOGLE_API_KEY)
                print("[EXPLAIN] Đã kết nối Gemini AI (Auto-Retry Mode)!")
            except Exception as e:
                print(f"[EXPLAIN] Lỗi kết nối: {e}")
                self.client = None
        else:
            self.client = None

    @app_commands.command(name="explain", description="Giải thích khái niệm")
    @app_commands.describe(field="Lĩnh vực (Vd: Toán, Lý, IT)", concept="Khái niệm cần giải thích")
    async def explain(self, interaction: discord.Interaction, field: str, concept: str):
        # Defer để tránh timeout
        await interaction.response.defer()

        if not self.client:
            await interaction.followup.send("Lỗi: Admin chưa cấu hình API Key.", ephemeral=True)
            return

        # --- TỐI ƯU PROMPT ĐỂ HIỂN THỊ ĐẸP & SINH ĐỘNG ---
        prompt = (
            f"Bạn là một giáo sư vui tính, chuyên gia hàng đầu về '{field}'. "
            f"Hãy giải thích khái niệm '{concept}' cho sinh viên.\n\n"

            f"QUY TẮC ĐỊNH DẠNG (BẮT BUỘC TUÂN THỦ):\n"
            f"1. TUYỆT ĐỐI KHÔNG dùng LaTeX ($...$).\n"
            f"2. MỌI công thức toán phải đặt trong khối mã ```text``` để dùng font monospace.\n"
            f"3. KHUNG công thức phải rộng cố định và căn giữa nội dung.\n\n"

            f"CÁCH VẼ CÔNG THỨC CHUẨN:\n"

            f"• Công thức đơn:\n"
            f"```text\n"
            f"+-------------------------------+\n"
            f"|        E = m × c^2            |\n"
            f"+-------------------------------+\n"
            f"```\n\n"

            f"• Phân số:\n"
            f"```text\n"
            f"+-------------------------------+\n"
            f"|            a + b              |\n"
            f"|        -------------          |\n"
            f"|            c + d              |\n"
            f"+-------------------------------+\n"
            f"```\n\n"

            f"• Căn bậc hai:\n"
            f"```text\n"
            f"+-------------------------------+\n"
            f"|        sqrt(x^2 + y^2)        |\n"
            f"+-------------------------------+\n"
            f"```\n\n"

            f"• Tích phân:\n"
            f"```text\n"
            f"+-------------------------------+\n"
            f"|      ∫(a→b) f(x) dx          |\n"
            f"+-------------------------------+\n"
            f"```\n\n"

            f"4. Các dòng trong khung PHẢI thẳng hàng.\n"
            f"5. Không để chữ chạm viền khung.\n\n"

            f"CẤU TRÚC TRẢ LỜI:\n"
            f"- **Định nghĩa:** Ngắn gọn.\n"
            f"- **Ví dụ đời thường:** Dùng blockquote (>).\n"
            f"- **Công thức / Cơ chế:** Bắt buộc theo mẫu khung trên.\n"
            f"- **Ứng dụng:** Gạch đầu dòng.\n"
            f"- **Ghi nhớ:** Mẹo nhớ nhanh."
        )

        # --- CƠ CHẾ TỰ ĐỘNG THỬ LẠI (RETRY) ---
        max_retries = 3
        current_try = 0

        # [Cấu hình Model]
        target_model = 'gemini-3-flash-preview'

        while current_try < max_retries:
            try:
                response = await self.client.aio.models.generate_content(
                    model=target_model,
                    contents=prompt
                )

                # Cắt ngắn nếu quá dài (Discord limit 4096)
                description_text = response.text[:4000]

                # --- TẠO EMBED ĐẸP ---
                embed = discord.Embed(
                    title=f"Bài giảng: {concept.title()}",
                    description=description_text,
                    color=discord.Color.gold()  # Màu vàng tri thức
                )

                # Thêm Thumbnail (Hình nhỏ bên phải)
                embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2051/2051935.png")

                # Tách field cho gọn
                embed.add_field(name="Chuyên ngành", value=f"**{field.upper()}**", inline=True)
                embed.add_field(name="Model", value=f"`{target_model}`", inline=True)

                # Footer có avatar người dùng
                embed.set_footer(
                    text=f"Yêu cầu bởi {interaction.user.display_name} • Học tập hiệu quả!",
                    icon_url=interaction.user.avatar.url if interaction.user.avatar else None
                )

                await interaction.followup.send(embed=embed)
                return  

            except Exception as e:
                error_str = str(e)
                # Xử lý lỗi quá tải (429)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    current_try += 1
                    wait_time = 4 * current_try
                    if current_try < max_retries:
                        print(f"[AI Busy] Đang thử lại lần {current_try} sau {wait_time}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        await interaction.followup.send("AI đang quá tải. Vui lòng thử lại sau 1 phút!",
                                                        ephemeral=True)
                        return
                else:
                    # Các lỗi khác
                    traceback.print_exc()
                    await interaction.followup.send(f"Lỗi xử lý: {e}", ephemeral=True)
                    return


async def setup(bot):
    await bot.add_cog(Explain(bot))