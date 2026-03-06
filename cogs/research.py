import discord
from discord import app_commands
from discord.ext import commands
from duckduckgo_search import DDGS


class Research(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_links(self, query, region='vn-vi', max_results=3):
        """Hàm chuyên dụng để đào link từ DuckDuckGo"""
        results = []
        try:
            with DDGS() as ddgs:
                # Sử dụng backend='html' để quét sâu hơn (tuy chậm hơn api 1 xíu nhưng ít bị miss)
                data = list(ddgs.text(query, region=region, max_results=max_results))

                for res in data:
                    link = res.get('href')
                    title = res.get('title')

                    # Chỉ lấy kết quả có Link và Tiêu đề đầy đủ
                    if link and title:
                        results.append({
                            'title': title,
                            'link': link,
                            'desc': res.get('body', 'Không có mô tả trước.')
                        })
        except Exception as e:
            print(f"Lỗi quét link ({query}): {e}")
        return results

    @app_commands.command(name="research", description="Tìm kiếm tài liệu & Trả về Link (PDF, Video, Web)")
    @app_commands.describe(topic="Nhập tên tài liệu/khóa học cần tìm")
    async def research(self, interaction: discord.Interaction, topic: str):
        # 1. Báo hiệu đang đào dữ liệu
        await interaction.response.defer()

        # Tạo Embed
        embed = discord.Embed(
            title=f"🔎 Kết quả tìm kiếm: {topic}",
            description="Bot đang tổng hợp các đường link tốt nhất...",
            color=discord.Color.brand_green()
        )
        message = await interaction.followup.send(embed=embed)

        # 2. CHIẾN THUẬT QUÉT ĐA LUỒNG (3 Nhóm)

        # Nhóm 1: TÀI LIỆU TẢI XUỐNG (PDF/DOC)
        # Tìm ưu tiên tiếng Việt trước
        docs = self.get_links(f"{topic} filetype:pdf OR filetype:docx", region='vn-vi', max_results=2)
        # Nếu không có Việt thì tìm Anh
        if not docs:
            docs = self.get_links(f"{topic} filetype:pdf", region='wt-wt', max_results=2)

        # Nhóm 2: VIDEO HƯỚNG DẪN (Youtube)
        videos = self.get_links(f"site:youtube.com {topic} hướng dẫn tutorial", region='wt-wt', max_results=2)

        # Nhóm 3: WEB / BLOG KIẾN THỨC
        webs = self.get_links(f"{topic} hướng dẫn tài liệu", region='vn-vi', max_results=3)

        # 3. TRÌNH BÀY KẾT QUẢ (Show Link rõ ràng)

        embed.description = ""  # Xóa dòng waiting
        has_result = False

        # --> Render phần Tài liệu
        if docs:
            has_result = True
            content = ""
            for item in docs:
                content += f"📂 **[{item['title']}]({item['link']})**\n🔗 `[Link Tải PDF/DOC]`({item['link']})\n\n"
            embed.add_field(name="📑 Tài liệu & Giáo trình", value=content, inline=False)

        # --> Render phần Video
        if videos:
            has_result = True
            content = ""
            for item in videos:
                content += f"🎬 **[{item['title']}]({item['link']})**\n🔗 `[Xem Video]`({item['link']})\n\n"
            embed.add_field(name="📺 Video Khóa học", value=content, inline=False)

        # --> Render phần Web
        if webs:
            has_result = True
            content = ""
            for item in webs:
                # Cắt mô tả ngắn
                desc = item['desc'][:100] + "..." if len(item['desc']) > 100 else item['desc']
                content += f"🌐 **[{item['title']}]({item['link']})**\n_{desc}_\n🔗 `[Đọc bài viết]`({item['link']})\n\n"
            embed.add_field(name="📰 Bài viết tham khảo", value=content, inline=False)

        # 4. TRƯỜNG HỢP KHÔNG TÌM THẤY (Fallback Link)
        if not has_result:
            embed.color = discord.Color.red()
            embed.description = "⚠️ Bot không cào được link trực tiếp. Vui lòng sử dụng các link dự phòng dưới đây:"

        # Luôn hiện link dự phòng Google (Đảm bảo 100% có chỗ để bấm)
        q_pdf = f"https://www.google.com/search?q={topic.replace(' ', '+')}+filetype:pdf"
        q_video = f"https://www.google.com/search?q={topic.replace(' ', '+')}+site:youtube.com"
        q_general = f"https://www.google.com/search?q={topic.replace(' ', '+')}"

        embed.add_field(
            name="🚀 Truy cập nhanh (Google Search)",
            value=(
                f"📂 [Tìm PDF trên Google]({q_pdf})\n"
                f"📺 [Tìm Video trên Google]({q_video})\n"
                f"🌍 [Tìm Tổng hợp]({q_general})"
            ),
            inline=False
        )

        embed.set_footer(text="Bot tự động lọc link PDF, Video và Web.")

        # Cập nhật tin nhắn
        await interaction.edit_original_response(embed=embed)


async def setup(bot):
    await bot.add_cog(Research(bot))