import discord
import json
import os
import random
from typing import List
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

# Tên file lưu dữ liệu
DB_FILE = "flashcards.json"


class Flashcard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.load_data()

    # --- HÀM XỬ LÝ DỮ LIỆU ---
    def load_data(self):
        if not os.path.exists(DB_FILE):
            self.data = {}
            self.save_data()
        else:
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except:
                self.data = {}

    def save_data(self):
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    # --- AUTOCOMPLETE ---
    async def topic_autocomplete(self, interaction: discord.Interaction, current: str) -> List[
        app_commands.Choice[str]]:
        user_id = str(interaction.user.id)
        if user_id not in self.data: return []
        topics = list(self.data[user_id].keys())
        return [app_commands.Choice(name=t, value=t) for t in topics if current.lower() in t.lower()][:25]

    # --- LỆNH 1: THÊM THẺ ---
    @app_commands.command(name="flashcard_add", description="Tạo thẻ mới")
    @app_commands.describe(topic="Chủ đề", question="Câu hỏi", answer="Đáp án")
    @app_commands.autocomplete(topic=topic_autocomplete)
    async def add_card(self, interaction: discord.Interaction, topic: str, question: str, answer: str):
        user_id = str(interaction.user.id)
        topic = topic.strip().title()

        if user_id not in self.data: self.data[user_id] = {}
        if topic not in self.data[user_id]: self.data[user_id][topic] = []

        self.data[user_id][topic].append({"q": question, "a": answer})
        self.save_data()

        embed = discord.Embed(title="Đã lưu thẻ!", color=discord.Color.green())
        embed.add_field(name="Chủ đề", value=topic, inline=True)
        embed.add_field(name="Hỏi", value=question, inline=False)
        embed.add_field(name="Đáp", value=answer, inline=False)
        await interaction.response.send_message(embed=embed)

    # --- LỆNH 2: QUẢN LÝ ---
    @app_commands.command(name="flashcard_manage", description="Sửa/Xóa thẻ")
    @app_commands.describe(topic="Chọn chủ đề")
    @app_commands.autocomplete(topic=topic_autocomplete)
    async def manage(self, interaction: discord.Interaction, topic: str):
        user_id = str(interaction.user.id)
        if user_id not in self.data or topic not in self.data[user_id] or not self.data[user_id][topic]:
            await interaction.response.send_message(f"Chủ đề **{topic}** trống hoặc không tồn tại.", ephemeral=True)
            return

        cards = self.data[user_id][topic]
        # Truyền user_id vào View để kiểm tra quyền
        view = ManageView(self, user_id, topic, cards)
        await view.send_initial_message(interaction)

    # --- LỆNH 3: ÔN TẬP ---
    @app_commands.command(name="flashcard_review", description="Bắt đầu học bài")
    @app_commands.describe(topic="Chọn chủ đề")
    @app_commands.autocomplete(topic=topic_autocomplete)
    async def review(self, interaction: discord.Interaction, topic: str):
        user_id = str(interaction.user.id)
        if user_id not in self.data or topic not in self.data[user_id]:
            await interaction.response.send_message(f"Không tìm thấy chủ đề **{topic}**.", ephemeral=True)
            return

        cards = self.data[user_id][topic]
        if not cards:
            await interaction.response.send_message("Chủ đề này chưa có thẻ nào!", ephemeral=True)
            return

        review_cards = cards.copy()
        random.shuffle(review_cards)
        # Truyền user_id vào View để kiểm tra quyền
        view = ReviewView(user_id, review_cards, topic)
        await view.send_initial_message(interaction)

    # --- LỆNH 4: XÓA CHỦ ĐỀ ---
    @app_commands.command(name="flashcard_delete_topic", description="Xóa vĩnh viễn chủ đề")
    @app_commands.describe(topic="Chọn chủ đề")
    @app_commands.autocomplete(topic=topic_autocomplete)
    async def delete_topic(self, interaction: discord.Interaction, topic: str):
        user_id = str(interaction.user.id)
        if user_id in self.data and topic in self.data[user_id]:
            del self.data[user_id][topic]
            self.save_data()
            await interaction.response.send_message(f"Đã xóa chủ đề **{topic}**.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Không tìm thấy chủ đề **{topic}**.", ephemeral=True)

    # --- LỆNH 5: LIST ---
    @app_commands.command(name="flashcard_list", description="Xem danh sách chủ đề")
    async def list_topics(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in self.data or not self.data[user_id]:
            await interaction.response.send_message("Bạn chưa tạo thẻ nào.", ephemeral=True)
            return

        text = ""
        for t in self.data[user_id]:
            text += f"**{t}**: {len(self.data[user_id][t])} thẻ\n"

        embed = discord.Embed(title="Kho Flashcard Của Bạn", description=text, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)


# --- [MODAL] FORM CHỈNH SỬA ---
class EditModal(Modal):
    def __init__(self, view, card_index):
        super().__init__(title="Chỉnh sửa thẻ")
        self.view_parent = view
        self.card_index = card_index
        current_card = view.cards[card_index]
        self.question = TextInput(label="Câu hỏi", default=current_card['q'], style=discord.TextStyle.paragraph,
                                  required=True)
        self.answer = TextInput(label="Đáp án", default=current_card['a'], style=discord.TextStyle.paragraph,
                                required=True)
        self.add_item(self.question)
        self.add_item(self.answer)

    async def on_submit(self, interaction: discord.Interaction):
        self.view_parent.cards[self.card_index]['q'] = self.question.value
        self.view_parent.cards[self.card_index]['a'] = self.answer.value
        self.view_parent.cog.save_data()
        await interaction.response.defer()
        await self.view_parent.update_view(interaction)
        await interaction.followup.send("Đã cập nhật thẻ!", ephemeral=True)


# --- [VIEW 1] QUẢN LÝ (BẢO MẬT) ---
class ManageView(View):
    def __init__(self, cog, user_id, topic, cards):
        super().__init__(timeout=600)
        self.cog = cog
        self.owner_id = str(user_id)  # Lưu ID chủ sở hữu
        self.topic = topic
        self.cards = cards
        self.index = 0

    # --- [QUAN TRỌNG] HÀM KIỂM TRA QUYỀN ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("**Đây không phải thẻ của bạn!** Hãy tự tạo thẻ riêng nhé.",
                                                    ephemeral=True)
            return False
        return True

    async def send_initial_message(self, interaction):
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.send_message(embed=embed, view=self)

    def get_embed(self):
        if not self.cards: return discord.Embed(title="Trống", description="Chủ đề này không còn thẻ nào.",
                                                color=discord.Color.red())
        card = self.cards[self.index]
        embed = discord.Embed(title=f"🛠️ Quản lý: {self.topic}",
                              description=f"Thẻ **{self.index + 1}/{len(self.cards)}**", color=discord.Color.orange())
        embed.add_field(name="Câu hỏi", value=card['q'], inline=False)
        embed.add_field(name="Đáp án", value=card['a'], inline=False)
        return embed

    def update_buttons(self):
        self.clear_items()
        if not self.cards: return

        btn_prev = Button(emoji="⬅️", style=discord.ButtonStyle.secondary, disabled=(self.index == 0))
        btn_prev.callback = self.prev_callback
        self.add_item(btn_prev)

        btn_edit = Button(label="Sửa", emoji="✏️", style=discord.ButtonStyle.primary)
        btn_edit.callback = self.edit_callback
        self.add_item(btn_edit)

        btn_del = Button(label="Xóa", emoji="🗑️", style=discord.ButtonStyle.danger)
        btn_del.callback = self.delete_callback
        self.add_item(btn_del)

        btn_next = Button(emoji="➡️", style=discord.ButtonStyle.secondary, disabled=(self.index == len(self.cards) - 1))
        btn_next.callback = self.next_callback
        self.add_item(btn_next)

    async def update_view(self, interaction):
        self.update_buttons()
        await interaction.edit_original_response(embed=self.get_embed(), view=self)

    async def prev_callback(self, interaction):
        self.index -= 1
        await interaction.response.defer()
        await self.update_view(interaction)

    async def next_callback(self, interaction):
        self.index += 1
        await interaction.response.defer()
        await self.update_view(interaction)

    async def delete_callback(self, interaction):
        deleted = self.cards.pop(self.index)
        self.cog.save_data()
        if self.index >= len(self.cards): self.index = max(0, len(self.cards) - 1)
        await interaction.response.defer()
        await self.update_view(interaction)
        await interaction.followup.send(f"🗑️ Đã xóa: **{deleted['q']}**", ephemeral=True)

    async def edit_callback(self, interaction):
        await interaction.response.send_modal(EditModal(self, self.index))


# --- [VIEW 2] ÔN TẬP (BẢO MẬT) ---
class ReviewView(View):
    def __init__(self, user_id, cards, topic):
        super().__init__(timeout=600)
        self.owner_id = str(user_id)  # Lưu ID chủ sở hữu
        self.cards = cards
        self.topic = topic
        self.index = 0
        self.is_showing_answer = False

    # --- [QUAN TRỌNG] HÀM KIỂM TRA QUYỀN ---
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.owner_id:
            await interaction.response.send_message("**Đừng bấm phá nha!** Đây là buổi ôn tập của người khác.",
                                                    ephemeral=True)
            return False
        return True

    async def send_initial_message(self, interaction):
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.send_message(embed=embed, view=self)

    def get_embed(self):
        card = self.cards[self.index]
        total = len(self.cards)
        if not self.is_showing_answer:
            embed = discord.Embed(title=f"🃏 Ôn tập: {self.topic} ({self.index + 1}/{total})",
                                  description=f"## ❓ {card['q']}", color=discord.Color.blue())
            embed.set_footer(text="Tự nhẩm câu trả lời rồi bấm 'Lật thẻ'")
        else:
            embed = discord.Embed(title=f"🃏 Ôn tập: {self.topic} ({self.index + 1}/{total})",
                                  description=f"**❓ {card['q']}**\n\n### 💡 {card['a']}", color=discord.Color.green())
        return embed

    def update_buttons(self):
        self.clear_items()
        if not self.is_showing_answer:
            btn = Button(label="Lật thẻ", emoji="🕵️", style=discord.ButtonStyle.primary)
            btn.callback = self.reveal_callback
            self.add_item(btn)
        else:
            btn = Button(label="Tiếp theo", emoji="➡️", style=discord.ButtonStyle.success)
            btn.callback = self.next_callback
            self.add_item(btn)

    async def reveal_callback(self, interaction):
        self.is_showing_answer = True
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def next_callback(self, interaction):
        self.index += 1
        if self.index >= len(self.cards):
            embed = discord.Embed(title="🎉 Hoàn thành!", description="Bạn đã ôn hết bộ thẻ này!",
                                  color=discord.Color.gold())
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            self.is_showing_answer = False
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)


async def setup(bot):
    await bot.add_cog(Flashcard(bot))