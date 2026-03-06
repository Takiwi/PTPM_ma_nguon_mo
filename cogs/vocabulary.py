import discord
import requests
import asyncio
import random
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from deep_translator import GoogleTranslator

# --- CẤU HÌNH CHỦ ĐỀ (TOEIC / IELTS / GIAO TIẾP) ---
TOPICS = [
    "business", "marketing", "contract", "investment", "office",  # Kinh tế
    "university", "research", "analysis", "theory",  # Học thuật
    "technology", "software", "innovation", "digital",  # Công nghệ
    "communication", "negotiation", "strategy", "leader",  # Kỹ năng
    "travel", "culture", "environment", "health"  # Đời sống
]


# --- LOGIC XỬ LÝ TỪ VỰNG ---

def get_word_logic():
    translator = GoogleTranslator(source='auto', target='vi')

    # Thử tối đa 5 lần để tìm từ có đủ thông tin
    for _ in range(5):
        try:
            # 1. Chọn chủ đề & Lấy từ liên quan
            topic = random.choice(TOPICS)
            # Lấy danh sách từ liên quan (Means Like)
            resp = requests.get(f"https://api.datamuse.com/words?ml={topic}&sp=?????*&max=40")
            if resp.status_code != 200: continue

            candidates = resp.json()
            if not candidates: continue
            random.shuffle(candidates)

            # 2. Tra từ điển chi tiết
            for item in candidates[:5]:
                word = item['word']

                # Gọi Dictionary API
                dict_resp = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}")
                if dict_resp.status_code != 200: continue

                data = dict_resp.json()[0]

                # --- [FIX QUAN TRỌNG] LỌC VÀ CHỌN NGẪU NHIÊN LOẠI TỪ ---
                # Thay vì lấy [0], ta lấy tất cả các meanings có ví dụ
                valid_meanings = []
                for m in data.get('meanings', []):
                    # Chỉ lấy Danh/Động/Tính/Trạng (Bỏ giới từ, thán từ...)
                    if m['partOfSpeech'] in ['noun', 'verb', 'adjective', 'adverb']:
                        # Kiểm tra xem có definition và example không
                        for d in m.get('definitions', []):
                            if 'example' in d and 'definition' in d:
                                # Lưu lại cả bộ (Loại từ, Nghĩa, Ví dụ)
                                valid_meanings.append({
                                    'pos': m['partOfSpeech'],
                                    'def': d['definition'],
                                    'ex': d['example']
                                })

                # Nếu từ này không có meaning nào hợp lệ (có ví dụ), bỏ qua tìm từ khác
                if not valid_meanings: continue

                # Chọn NGẪU NHIÊN 1 loại từ trong danh sách tìm được
                # (Để lúc thì ra Noun, lúc ra Verb, lúc ra Adj)
                selected = random.choice(valid_meanings)

                # Lấy phiên âm
                phonetic = data.get('phonetic', '') or data.get('phonetics', [{}])[0].get('text', '/.../')

                # Audio Link
                audio_url = f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={word}&tl=en"

                # 3. DỊCH THUẬT
                # Dịch nghĩa từ chính (Word)
                meaning_vi_direct = translator.translate(word)

                # Dịch giải thích (Definition)
                definition_vi = translator.translate(selected['def'])

                # Dịch ví dụ (Example)
                example_vi = translator.translate(selected['ex'])

                return {
                    "word": word.capitalize(),
                    "type": selected['pos'].capitalize(),  # Loại từ đã chọn ngẫu nhiên
                    "phonetic": phonetic,
                    "audio": audio_url,
                    "meaning_vi_direct": meaning_vi_direct.capitalize(),
                    "definition_en": selected['def'],
                    "definition_vi": definition_vi,
                    "example_en": selected['ex'],
                    "example_vi": example_vi,
                    "topic": topic.capitalize()
                }
        except Exception as e:
            print(f"Lỗi tìm từ: {e}")
            continue

    return None


# --- GIAO DIỆN HIỂN THỊ ---

class VocabularyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Từ tiếp theo", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_word(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        data = await asyncio.to_thread(get_word_logic)

        if data:
            embed = create_embed(data)
            await interaction.edit_original_response(embed=embed, view=self)
        else:
            await interaction.followup.send("⚠️ Đang tải dữ liệu... bấm lại lần nữa nhé!", ephemeral=True)


def get_color(pos):
    """Màu sắc phân loại từ"""
    p = pos.lower()
    if 'verb' in p: return discord.Color.from_rgb(231, 76, 60)  # Đỏ (Hành động)
    if 'noun' in p: return discord.Color.from_rgb(52, 152, 219)  # Xanh Dương (Sự vật)
    if 'adj' in p: return discord.Color.from_rgb(241, 196, 15)  # Vàng (Tính chất)
    if 'adv' in p: return discord.Color.from_rgb(155, 89, 182)  # Tím (Cách thức)
    return discord.Color.dark_grey()


def create_embed(data):
    # Tiêu đề
    embed = discord.Embed(
        title=f"🇬🇧 {data['word']}",
        description=f"**{data['phonetic']}** • *{data['type']}*",
        color=get_color(data['type'])
    )

    # 1. NGHĨA SÁT
    embed.add_field(
        name="🇻🇳 Nghĩa Tiếng Việt",
        value=f"## **{data['meaning_vi_direct']}**",
        inline=False
    )

    # 2. GIẢI THÍCH
    embed.add_field(
        name="📖 Giải thích (Definition)",
        value=f"🇬🇧 {data['definition_en']}\n🇻🇳 *{data['definition_vi']}*",
        inline=False
    )

    # 3. VÍ DỤ
    embed.add_field(
        name="💡 Ví dụ ngữ cảnh",
        value=f"> 🇺🇸 {data['example_en']}\n> 🇻🇳 {data['example_vi']}",
        inline=False
    )

    # Footer
    embed.add_field(
        name="🔊 Phát âm & Chủ đề",
        value=f"[Nghe giọng bản xứ]({data['audio']}) • Topic: `{data['topic']}`",
        inline=False
    )

    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2436/2436636.png")
    embed.set_footer(text="Học tiếng Anh chuẩn • Dữ liệu đa dạng (Verb/Adj/Noun)")

    return embed


# --- COG CHÍNH ---
class Vocabulary(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="word", description="Học từ vựng ngẫu nhiên (Đủ loại từ)")
    async def word(self, interaction: discord.Interaction):
        await interaction.response.defer()

        data = await asyncio.to_thread(get_word_logic)

        if data:
            embed = create_embed(data)
            view = VocabularyView()
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send("⚠️ Mạng hơi lag, thử lại nhé!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Vocabulary(bot))