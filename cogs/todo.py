import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View, Button, Select
from datetime import datetime


# --- CẤU TRÚC DỮ LIỆU ---
class Task:
    def __init__(self, name, assignee, start_str, end_str):
        self.name = name
        self.assignee = assignee
        self.start_str = start_str
        self.end_str = end_str
        self.progress = "0%"
        self.notes = "Chưa có ghi chú"
        self.is_notified = False

    def get_end_time(self):
        try:
            return datetime.strptime(self.end_str, "%H:%M %d/%m/%Y")
        except:
            return None


class Plan:
    def __init__(self, name, description, start_str, end_str, creator_id, channel_id):
        self.name = name
        self.description = description
        self.start_str = start_str
        self.end_str = end_str
        self.creator_id = creator_id
        self.channel_id = channel_id
        self.tasks = []
        self.status = "DRAFT"  # DRAFT, RUNNING, COMPLETED
        # Lưu lịch sử dưới dạng dict để dễ format: {time, action, type}
        self.history = [{
            "time": datetime.now().strftime("%d/%m %H:%M"),
            "action": "Khởi tạo kế hoạch",
            "type": "INIT"
        }]

    def add_history(self, action, type="INFO"):
        # Type: INFO, ADD, UPDATE, DELETE, ALERT, DONE
        timestamp = datetime.now().strftime("%d/%m %H:%M")
        self.history.append({
            "time": timestamp,
            "action": action,
            "type": type
        })

    def get_end_time(self):
        try:
            return datetime.strptime(self.end_str, "%H:%M %d/%m/%Y")
        except:
            return None


# Kho lưu trữ dữ liệu tạm thời
plans_db = {}


# --- CÁC MODAL (BIỂU MẪU) ---

class SearchPlanModal(Modal, title="Tìm kiếm Kế hoạch"):
    query = TextInput(label="Nhập tên kế hoạch cần tìm", placeholder="Vd: Web...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        keyword = self.query.value.lower()
        # Lọc danh sách
        filtered_plans = {k: v for k, v in plans_db.items() if keyword in k.lower()}

        if not filtered_plans:
            await interaction.response.send_message(f"❌ Không tìm thấy kế hoạch nào chứa từ khóa '**{keyword}**'.",
                                                    ephemeral=True)
            return

        view = TodoListView(filtered_plans=filtered_plans)
        await interaction.response.send_message(f"🔍 Kết quả tìm kiếm cho '**{keyword}**':", view=view, ephemeral=True)


class PlanSetupModal(Modal, title="Khởi tạo Kế hoạch Mới"):
    name = TextInput(label="Tên Kế hoạch (ID)", placeholder="Vd: DuAnWebsite_v1", required=True)
    desc = TextInput(label="Mô tả tổng quan", style=discord.TextStyle.paragraph, required=True)
    time_start = TextInput(label="Thời gian bắt đầu", placeholder="HH:MM dd/mm/yyyy", required=True)
    time_end = TextInput(label="Thời gian kết thúc", placeholder="HH:MM dd/mm/yyyy", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        plan_name = self.name.value.strip()
        if plan_name in plans_db:
            await interaction.response.send_message("⚠️ Tên kế hoạch này đã tồn tại!", ephemeral=True)
            return

        new_plan = Plan(plan_name, self.desc.value, self.time_start.value, self.time_end.value, interaction.user.id,
                        interaction.channel_id)
        plans_db[plan_name] = new_plan

        embed = create_plan_embed(new_plan)
        view = DraftView(plan_name)
        await interaction.response.send_message(embed=embed, view=view)


class TaskAddModal(Modal, title="Thêm Task Mới"):
    def __init__(self, plan_name):
        super().__init__()
        self.plan_name = plan_name

    t_name = TextInput(label="Nội dung công việc", required=True)
    assignee = TextInput(label="Người thực hiện", placeholder="@Ten hoặc Tên", required=True)
    t_start = TextInput(label="Bắt đầu", placeholder="HH:MM dd/mm/yyyy", required=True)
    t_end = TextInput(label="Kết thúc", placeholder="HH:MM dd/mm/yyyy", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        plan = plans_db.get(self.plan_name)
        if not plan: return

        new_task = Task(self.t_name.value, self.assignee.value, self.t_start.value, self.t_end.value)
        plan.tasks.append(new_task)
        plan.add_history(f"Thêm task: **{new_task.name}** ({new_task.assignee})", "ADD")

        embed = create_plan_embed(plan)
        view = RunningView(self.plan_name) if plan.status == "RUNNING" else DraftView(self.plan_name)
        await interaction.response.edit_message(embed=embed, view=view)


class UpdateTaskModal(Modal, title="Cập nhật Tiến độ"):
    def __init__(self, plan_name, task_index):
        super().__init__()
        self.plan_name = plan_name
        self.task_index = task_index

    progress = TextInput(label="Tiến độ (%)", placeholder="Vd: 50%", required=True)
    note = TextInput(label="Ghi chú thêm", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        plan = plans_db.get(self.plan_name)
        if plan and 0 <= self.task_index < len(plan.tasks):
            task = plan.tasks[self.task_index]
            old_prog = task.progress
            task.progress = self.progress.value
            if self.note.value: task.notes = self.note.value

            plan.add_history(f"Task '{task.name}': {old_prog} -> **{task.progress}**", "UPDATE")

            embed = create_plan_embed(plan)
            await interaction.response.edit_message(embed=embed, view=RunningView(self.plan_name))


class ExtendPlanModal(Modal, title="Gia hạn Kế hoạch"):
    def __init__(self, plan_name):
        super().__init__()
        self.plan_name = plan_name

    new_end_time = TextInput(label="Thời gian kết thúc mới", placeholder="HH:MM dd/mm/yyyy", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        plan = plans_db.get(self.plan_name)
        if plan:
            old_time = plan.end_str
            plan.end_str = self.new_end_time.value
            plan.add_history(f"Gia hạn: {old_time} -> **{plan.end_str}**", "ALERT")

            embed = create_plan_embed(plan)
            await interaction.response.edit_message(embed=embed, view=RunningView(self.plan_name))


# --- HÀM HELPER & EMBED ---

def create_plan_embed(plan):
    color = discord.Color.blue() if plan.status == "DRAFT" else discord.Color.green()
    if plan.status == "COMPLETED": color = discord.Color.greyple()

    embed = discord.Embed(title=f"📋 Kế hoạch: {plan.name}", description=f"*{plan.description}*", color=color)
    embed.add_field(name="📅 Thời gian", value=f"Start: `{plan.start_str}`\nEnd: `{plan.end_str}`", inline=True)
    embed.add_field(name="⚙️ Trạng thái", value=f"**{plan.status}**", inline=True)
    embed.add_field(name="👤 Quản lý", value=f"<@{plan.creator_id}>", inline=True)

    if not plan.tasks:
        embed.add_field(name="Danh sách Task", value="*(Chưa có task nào)*", inline=False)
    else:
        tasks_str = ""
        for i, task in enumerate(plan.tasks):
            # Icon trạng thái task
            status_icon = "🔵"
            if task.progress == "100%":
                status_icon = "✅"
            elif task.progress != "0%":
                status_icon = "🔄"

            tasks_str += f"{status_icon} **{i + 1}. {task.name}** (`{task.assignee}`)\n"
            tasks_str += f"   └─ ⏳ `{task.end_str}` | 📊 `{task.progress}`\n"

        if len(tasks_str) > 1024: tasks_str = tasks_str[:1020] + "..."
        embed.add_field(name=f"Danh sách Task ({len(plan.tasks)})", value=tasks_str, inline=False)

    embed.set_footer(text=f"Cập nhật lần cuối: {datetime.now().strftime('%H:%M %d/%m')}")
    return embed


def create_history_embed(plan):
    embed = discord.Embed(title=f"📜 Lịch sử hoạt động: {plan.name}", color=discord.Color.gold())

    # Mapping icon
    icons = {
        "INIT": "🆕", "ADD": "➕", "UPDATE": "🔄",
        "DELETE": "🗑️", "ALERT": "⚠️", "DONE": "✅", "INFO": "ℹ️"
    }

    history_text = ""
    # Lấy 15 dòng mới nhất, đảo ngược để mới nhất lên đầu
    for entry in reversed(plan.history[-15:]):
        icon = icons.get(entry['type'], "▪️")
        history_text += f"`{entry['time']}` {icon} {entry['action']}\n"

    if not history_text: history_text = "(Chưa có lịch sử)"

    embed.description = history_text
    return embed


# --- VIEWS (GIAO DIỆN) ---

# View Mới: Danh sách tổng quan (Dashboard)
class TodoListView(View):
    def __init__(self, filtered_plans=None):
        super().__init__(timeout=None)
        # Nếu có danh sách lọc (từ tìm kiếm) thì dùng, không thì dùng toàn bộ db
        self.plans_source = filtered_plans if filtered_plans is not None else plans_db

        # Tạo Select Menu động
        options = []
        if not self.plans_source:
            options.append(
                discord.SelectOption(label="Không có kế hoạch nào", value="none", description="Tạo mới đi bạn ơi!"))
        else:
            # Lấy tối đa 25 kế hoạch (giới hạn Discord)
            for name, plan in list(self.plans_source.items())[:25]:
                status_emoji = "🟢" if plan.status == "RUNNING" else "📝" if plan.status == "DRAFT" else "⚫"
                options.append(discord.SelectOption(
                    label=name,
                    value=name,
                    description=f"{status_emoji} {plan.description[:50]}...",
                    emoji=status_emoji
                ))

        self.select_menu = Select(placeholder="📂 Chọn kế hoạch để xem chi tiết...", options=options, row=0)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        if self.select_menu.values[0] == "none":
            await interaction.response.send_message("Hãy bấm nút 'Tạo Kế hoạch Mới' bên dưới 👇", ephemeral=True)
            return

        plan_name = self.select_menu.values[0]
        plan = plans_db.get(plan_name)
        if plan:
            embed = create_plan_embed(plan)
            view = DraftView(plan_name) if plan.status == "DRAFT" else RunningView(plan_name)
            if plan.status == "COMPLETED": view = None  # Hoặc view xem lại
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Kế hoạch không tồn tại (có thể đã bị xóa).", ephemeral=True)

    @discord.ui.button(label="✨ Tạo Kế hoạch Mới", style=discord.ButtonStyle.primary, row=1)
    async def create_new(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(PlanSetupModal())

    @discord.ui.button(label="🔍 Tìm kiếm", style=discord.ButtonStyle.secondary, row=1)
    async def search_plan(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SearchPlanModal())


# View: Soạn thảo
class DraftView(View):
    def __init__(self, plan_name):
        super().__init__(timeout=None)
        self.plan_name = plan_name

    @discord.ui.button(label="➕ Thêm Task", style=discord.ButtonStyle.primary)
    async def add_task(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TaskAddModal(self.plan_name))

    @discord.ui.button(label="🚀 Chạy Kế hoạch", style=discord.ButtonStyle.success)
    async def start_plan(self, interaction: discord.Interaction, button: Button):
        plan = plans_db.get(self.plan_name)
        if not plan: return
        if not plan.tasks:
            await interaction.response.send_message("⚠️ Cần ít nhất 1 Task!", ephemeral=True)
            return

        plan.status = "RUNNING"
        plan.add_history("Bắt đầu chạy kế hoạch.", "DONE")
        embed = create_plan_embed(plan)
        await interaction.response.edit_message(content="✅ Kế hoạch đang chạy!", embed=embed,
                                                view=RunningView(self.plan_name))

    @discord.ui.button(label="❌ Xóa", style=discord.ButtonStyle.danger)
    async def cancel_plan(self, interaction: discord.Interaction, button: Button):
        if self.plan_name in plans_db:
            del plans_db[self.plan_name]
        await interaction.response.edit_message(content="🗑️ Kế hoạch đã bị hủy.", embed=None, view=None)


# View: Đang chạy
class RunningView(View):
    def __init__(self, plan_name):
        super().__init__(timeout=None)
        self.plan_name = plan_name

    @discord.ui.button(label="📝 Cập nhật Tiến độ", style=discord.ButtonStyle.primary, row=0)
    async def update_progress(self, interaction: discord.Interaction, button: Button):
        plan = plans_db.get(self.plan_name)
        if not plan or not plan.tasks: return

        options = [discord.SelectOption(label=f"{i + 1}. {t.name[:20]}...", value=str(i), description=t.progress) for
                   i, t in enumerate(plan.tasks[:25])]

        select = Select(placeholder="Chọn Task...", options=options)

        async def cb(inter):
            await inter.response.send_modal(UpdateTaskModal(self.plan_name, int(select.values[0])))

        select.callback = cb

        view = View()
        view.add_item(select)
        await interaction.response.send_message("Chọn task cần cập nhật:", view=view, ephemeral=True)

    @discord.ui.button(label="➕ Thêm Task", style=discord.ButtonStyle.secondary, row=0)
    async def add_more_task(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TaskAddModal(self.plan_name))

    @discord.ui.button(label="🗑️ Xóa Task", style=discord.ButtonStyle.secondary, row=1)
    async def delete_task(self, interaction: discord.Interaction, button: Button):
        plan = plans_db.get(self.plan_name)
        if not plan: return

        options = [discord.SelectOption(label=f"{i + 1}. {t.name[:20]}...", value=str(i)) for i, t in
                   enumerate(plan.tasks[:25])]
        select = Select(placeholder="Chọn Task xóa...", options=options)

        async def cb(inter):
            idx = int(select.values[0])
            t_name = plan.tasks[idx].name
            del plan.tasks[idx]
            plan.add_history(f"Đã xóa task: {t_name}", "DELETE")
            embed = create_plan_embed(plan)
            # Cập nhật lại view chính nếu có thể, hoặc báo user refresh
            await inter.response.edit_message(content=f"🗑️ Đã xóa task **{t_name}**.", embed=None, view=None)

        select.callback = cb
        view = View()
        view.add_item(select)
        await interaction.response.send_message("Chọn task xóa vĩnh viễn:", view=view, ephemeral=True)

    @discord.ui.button(label="⏳ Gia hạn", style=discord.ButtonStyle.secondary, row=1)
    async def extend_plan(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ExtendPlanModal(self.plan_name))

    # --- NÚT LỊCH SỬ ĐẸP MẮT HƠN ---
    @discord.ui.button(label="📜 Lịch sử", style=discord.ButtonStyle.gray, row=2)
    async def view_history(self, interaction: discord.Interaction, button: Button):
        plan = plans_db.get(self.plan_name)
        if plan:
            embed = create_history_embed(plan)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Kết thúc", style=discord.ButtonStyle.danger, row=2)
    async def finish_plan(self, interaction: discord.Interaction, button: Button):
        plan = plans_db.get(self.plan_name)
        if plan:
            plan.status = "COMPLETED"
            plan.add_history("Hoàn thành kế hoạch.", "DONE")
            embed = create_plan_embed(plan)
            await interaction.response.edit_message(content="🎉 Kế hoạch đã hoàn thành!", embed=embed, view=None)


# --- COG CHÍNH ---

class TodoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_deadlines.start()

    def cog_unload(self):
        self.check_deadlines.cancel()

    @app_commands.command(name="todo", description="Mở Dashboard quản lý Kế hoạch/Dự án")
    async def todo(self, interaction: discord.Interaction):
        # Hiển thị Dashboard thay vì Modal ngay lập tức
        embed = discord.Embed(
            title="🗂️ QUẢN LÝ DỰ ÁN & TODO",
            description="Chào mừng! Bạn muốn làm gì hôm nay?\nHãy chọn kế hoạch từ danh sách hoặc tạo mới.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Thống kê", value=f"Tổng số kế hoạch: **{len(plans_db)}**", inline=False)

        view = TodoListView()
        await interaction.response.send_message(embed=embed, view=view)

    # Các command view_plan khác có thể giữ lại hoặc bỏ tùy nhu cầu

    @tasks.loop(minutes=1)
    async def check_deadlines(self):
        now = datetime.now()
        for name, plan in list(plans_db.items()):
            if plan.status != "RUNNING": continue

            # Check Plan Deadline
            p_end = plan.get_end_time()
            if p_end and now > p_end:
                plan.status = "COMPLETED"
                plan.add_history("Hết thời gian. Tự động đóng.", "DONE")
                channel = self.bot.get_channel(plan.channel_id)
                if channel: await channel.send(f"🔔 **{plan.name}** đã hết thời gian!", embed=create_plan_embed(plan))
                continue

            # Check Task Deadline
            creator = self.bot.get_user(plan.creator_id)
            for task in plan.tasks:
                if task.is_notified: continue
                t_end = task.get_end_time()
                if t_end and now > t_end:
                    task.is_notified = True
                    plan.add_history(f"Task quá hạn: {task.name}", "ALERT")
                    channel = self.bot.get_channel(plan.channel_id)
                    if channel:
                        msg = f"⚠️ **DEADLINE ALERT**\n📌 Plan: {plan.name}\n🔥 Task: {task.name} ({task.assignee})"
                        await channel.send(f"{creator.mention if creator else ''} {msg}")

    @check_deadlines.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(TodoCog(bot))