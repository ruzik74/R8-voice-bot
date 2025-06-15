import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import os
from discord.ui import Select
from keep_alive import keep_alive # NEW

TOKEN = os.getenv("DISCORD_BOT_TOKEN") or "YOUR_BOT_TOKEN"

keep_alive() # NEW

GUILD_ID = 1355204242595516841
CATEGORY_ID = 1355204243191238851
TEMP_CHANNEL_ID = 1355208133709926643
CONTROL_CHANNEL_ID = 1357392366599802971

# Временные структуры
temp_channels = {}
channel_limits = {}
message_control_map = {}

# Интенты
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_blocked_role(guild: discord.Guild):
    role = discord.utils.get(guild.roles, name="Blocked")
    if not role:
        role = await guild.create_role(name="Blocked", permissions=discord.Permissions(connect=False))
    return role

class VoiceChannelCheck:
    @staticmethod
    async def check_user_in_channel(interaction, channel):
        vs = interaction.user.voice
        if not vs or vs.channel is None or vs.channel.id != channel.id:
            await interaction.response.send_message("❌ Вы должны находиться в этом канале!", ephemeral=True)
            return False
        return True

class NicknameInputModal(Modal):
    def __init__(self, action, voice_channel, user):
        super().__init__(title=action)
        self.voice_channel = voice_channel
        self.action = action
        self.user = user
        self.add_item(TextInput(label="Никнейм", placeholder="Username#0000 или имя", required=True, max_length=32))

    async def on_submit(self, interaction):
        if not await VoiceChannelCheck.check_user_in_channel(interaction, self.voice_channel):
            return
        query = self.children[0].value.lower()
        source = interaction.guild.members if self.action == "Разблокировать" else self.voice_channel.members
        target = discord.utils.find(lambda m: m.name.lower()==query or m.display_name.lower()==query, source)
        if not target:
            await interaction.response.send_message("❌ Не найден.", ephemeral=True)
            return
        if self.action == "Заблокировать":
            role = await get_blocked_role(interaction.guild)
            await target.add_roles(role)
            await self.voice_channel.set_permissions(target, connect=False)
            await asyncio.sleep(1)
            try: await target.move_to(None)
            except: pass
            await interaction.response.send_message(f"🔒 {target.mention}", ephemeral=True)
        elif self.action == "Разблокировать":
            role = await get_blocked_role(interaction.guild)
            await target.remove_roles(role)
            await self.voice_channel.set_permissions(target, overwrite=None)
            await interaction.response.send_message(f"🔓 {target.mention}", ephemeral=True)
        elif self.action == "Кикнуть":
            try: await target.move_to(None); await interaction.response.send_message(f"⚔️ {target.mention}", ephemeral=True)
            except: await interaction.response.send_message("❌", ephemeral=True)
        elif self.action == "Передать":
            try:
                await self.voice_channel.set_permissions(self.user, overwrite=None)
                await self.voice_channel.set_permissions(target, connect=True, manage_channels=True)
                panel = message_control_map.get(self.voice_channel.id)
                if panel and isinstance(panel.view, VoiceControlPanel):
                    panel.view.creator = target
                await interaction.response.send_message(f"👑 Теперь {target.mention} — владелец канала.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

class VoiceControlPanel(View):
    def __init__(self, channel, control_message_id=None, creator=None):
        super().__init__(timeout=None)
        self.channel = channel
        self.control_message_id = control_message_id
        self.is_locked = False
        self.is_hidden = False
        self.creator = creator

    async def interaction_check(self, interaction):
        if interaction.user != self.creator:
            await interaction.response.send_message("❌ У вас нет прав для управления этим каналом.", ephemeral=True)
            return False
        return await VoiceChannelCheck.check_user_in_channel(interaction, self.channel)

    @discord.ui.button(label="🔒", style=discord.ButtonStyle.gray)
    async def toggle_lock(self, interaction, button: Button):
        if not self.is_locked:
            await self.channel.set_permissions(interaction.guild.default_role, connect=False)
            button.label = "🔓"
            self.is_locked = True
        else:
            await self.channel.set_permissions(interaction.guild.default_role, connect=True)
            button.label = "🔒"
            self.is_locked = False
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="👻", style=discord.ButtonStyle.gray)
    async def toggle_hide(self, interaction, button: Button):
        if not self.is_hidden:
            await self.channel.set_permissions(interaction.guild.default_role, view_channel=False)
            button.label = "👀"
            self.is_hidden = True
        else:
            await self.channel.set_permissions(interaction.guild.default_role, view_channel=True)
            button.label = "👻"
            self.is_hidden = False
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="🔇", style=discord.ButtonStyle.gray)
    async def mute_all(self, interaction, button):
        for m in self.channel.members: await m.edit(mute=True)
        await interaction.response.send_message("🔇", ephemeral=True)

    @discord.ui.button(label="🔊", style=discord.ButtonStyle.gray)
    async def unmute_all(self, interaction, button):
        for m in self.channel.members: await m.edit(mute=False)
        await interaction.response.send_message("🔊", ephemeral=True)

    @discord.ui.button(label="🗑", style=discord.ButtonStyle.danger)
    async def delete(self, interaction, button):
        await interaction.response.send_message("🗑", ephemeral=True)
        try:
            if self.control_message_id:
                ctrl_channel = interaction.guild.get_channel(CONTROL_CHANNEL_ID)
                if ctrl_channel:
                    msg = await ctrl_channel.fetch_message(self.control_message_id)
                    await msg.delete()
                message_control_map.pop(self.channel.id, None)
            await self.channel.delete()
        except: pass

    @discord.ui.button(label="⚙️", style=discord.ButtonStyle.blurple)
    async def limit(self, interaction, button):
        class LimitSelect(Select):
            def __init__(self, parent):
                opts = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1,11)]
                super().__init__(placeholder="⚙️", min_values=1, max_values=1, options=opts)
                self.parent = parent
            async def callback(self2, inter):
                await self2.parent.channel.edit(user_limit=int(self2.values[0]))
                await inter.response.send_message("⚙️", ephemeral=True)
        view = View(); view.add_item(LimitSelect(self)); await interaction.response.send_message("Выберите лимит участников:", view=view, ephemeral=True)

    @discord.ui.button(label="✏️", style=discord.ButtonStyle.blurple)
    async def rename(self, interaction, button):
        await interaction.response.send_message("✏️ Введите новое название голосового канала в чат.", ephemeral=True)
        try:
            msg = await bot.wait_for('message', check=lambda m: m.author==interaction.user and m.channel==interaction.channel, timeout=60)
            if msg.content.strip():
                await self.channel.edit(name=msg.content.strip())
                await interaction.followup.send("✅ Канал переименован.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Название не может быть пустым.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Время ожидания истекло.", ephemeral=True)

    @discord.ui.button(label="🔄", style=discord.ButtonStyle.red)
    async def manage_block(self, interaction, button):
        class ActionSelect(View):
            def __init__(self, channel, user):
                super().__init__(timeout=None)
                self.channel, self.user = channel, user
            @discord.ui.select(placeholder="🔄", options=[discord.SelectOption(label="🔒", value="Заблокировать"), discord.SelectOption(label="🔓", value="Разблокировать")], min_values=1, max_values=1)
            async def select_callback(self2, inter, menu):
                await inter.response.send_modal(NicknameInputModal(menu.values[0], self2.channel, self2.user))
        view = ActionSelect(self.channel, interaction.user)
        await interaction.response.send_message("", view=view, ephemeral=True)

    @discord.ui.button(label="⚔️", style=discord.ButtonStyle.gray)
    async def kick(self, interaction, button):
        await interaction.response.send_modal(NicknameInputModal("Кикнуть", self.channel, interaction.user))

    @discord.ui.button(label="👑", style=discord.ButtonStyle.blurple)
    async def transfer(self, interaction, button):
        await interaction.response.send_modal(NicknameInputModal("Передать", self.channel, interaction.user))

@bot.event
async def on_ready(): print(f"✅ {bot.user.name} запущен!")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TEMP_CHANNEL_ID:
        guild = bot.get_guild(GUILD_ID); category = guild.get_channel(CATEGORY_ID)
        if category:
            overwrites = {guild.default_role: discord.PermissionOverwrite(connect=True, view_channel=True), member: discord.PermissionOverwrite(connect=True, manage_channels=True)}
            temp = await guild.create_voice_channel(name=f"🔊 {member.display_name}", category=category, overwrites=overwrites)
            await member.move_to(temp); temp_channels[temp.id]=temp; channel_limits[temp.id]=10
            ctrl = guild.get_channel(CONTROL_CHANNEL_ID)
            if ctrl:
                embed = discord.Embed(
                    title="🎛 Управление голосовым каналом",
                    description=(
                        "🔒 Закрыть / открыть доступ    ┃     👻 Скрыть / показать канал\n"
                        "🔇 Заглушить всех             ┃     🔊 Разглушить всех\n"
                        "🗑 Удалить канал               ┃    ⚙️ Ограничение участников\n"
                        "✏️ Переименовать канал        ┃    🔄 Заблокировать / разблокировать\n"
                        "⚔️ Кикнуть участника          ┃    👑 Передать права"
                    ),
                    color=discord.Color.dark_embed()
                )
                msg = await ctrl.send(embed=embed, view=VoiceControlPanel(temp, creator=member))
                message_control_map[temp.id]=msg
    if before.channel and before.channel.id in temp_channels and not before.channel.members:
        try:
            if before.channel.id in message_control_map:
                try:
                    await message_control_map[before.channel.id].delete()
                except: pass
                del message_control_map[before.channel.id]
            await before.channel.delete()
            del temp_channels[before.channel.id]
            del channel_limits[before.channel.id]
        except: pass

bot.run(TOKEN)
