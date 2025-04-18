import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio

# ✅ ВСТАВЬ СЮДА СВОЙ ТОКЕН ДЛЯ ЛОКАЛЬНОГО ЗАПУСКА
GUILD_ID = 1355204242595516841
CATEGORY_ID = 1355204243191238851
TEMP_CHANNEL_ID = 1355208133709926643
CONTROL_CHANNEL_ID = 1357392366599802971

temp_channels = {}
channel_limits = {}
message_control_map = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

class VoiceControlPanel(View):
    def __init__(self, channel, control_message_id=None):
        super().__init__(timeout=None)
        self.channel = channel
        self.control_message_id = control_message_id

    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.gray)
    async def lock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Канал закрыт", ephemeral=True)

    @discord.ui.button(label="🔓 Открыть", style=discord.ButtonStyle.gray)
    async def unlock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Канал открыт", ephemeral=True)

    @discord.ui.button(label="👻 Скрыть", style=discord.ButtonStyle.gray)
    async def hide(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("👻 Канал скрыт", ephemeral=True)

    @discord.ui.button(label="👀 Показать", style=discord.ButtonStyle.gray)
    async def unhide(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, view_channel=True)
        await interaction.response.send_message("👀 Канал видим для всех", ephemeral=True)

    @discord.ui.button(label="🔇 Мьют всех", style=discord.ButtonStyle.gray)
    async def mute(self, interaction: discord.Interaction, button: Button):
        for member in self.channel.members:
            await member.edit(mute=True)
        await interaction.response.send_message("🔇 Все участники замьючены", ephemeral=True)

    @discord.ui.button(label="🔊 Анмьют всех", style=discord.ButtonStyle.gray)
    async def unmute(self, interaction: discord.Interaction, button: Button):
        for member in self.channel.members:
            await member.edit(mute=False)
        await interaction.response.send_message("🔊 Все участники размьючены", ephemeral=True)

    @discord.ui.button(label="🗑 Удалить", style=discord.ButtonStyle.danger)
    async def delete_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🗑️ Удаляем канал и сообщение...", ephemeral=True)
        try:
            await self.channel.delete()
            if self.control_message_id:
                message = await interaction.channel.fetch_message(self.control_message_id)
                await message.delete()
        except Exception as e:
            print(f"Ошибка при удалении: {e}")

    @discord.ui.button(label="✏ Переименовать", style=discord.ButtonStyle.blurple)
    async def rename_channel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Введите новое название для голосового канала:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', check=check, timeout=60)
            new_name = msg.content.strip()
            if new_name:
                await self.channel.edit(name=new_name)
                await interaction.followup.send(f"✅ Название канала изменено на: **{new_name}**", ephemeral=True)
            else:
                await interaction.followup.send("❌ Пустое имя не разрешено.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Время ожидания истекло.", ephemeral=True)

    @discord.ui.button(label="🎚 Выбрать лимит", style=discord.ButtonStyle.blurple)
    async def choose_limit(self, interaction: discord.Interaction, button: Button):
        class LimitSelect(discord.ui.Select):
            def __init__(self):
                options = [discord.SelectOption(label=str(i), value=str(i)) for i in range(1, 11)]
                super().__init__(placeholder="Выберите лимит участников", options=options)

            async def callback(self, select_interaction: discord.Interaction):
                limit = int(self.values[0])
                await self.view.channel.edit(user_limit=limit)
                channel_limits[self.view.channel.id] = limit
                await select_interaction.response.send_message(f"✅ Лимит установлен: {limit}", ephemeral=True)

        class LimitView(View):
            def __init__(self, channel):
                super().__init__(timeout=30)
                self.channel = channel
                self.add_item(LimitSelect())

        await interaction.response.send_message(
            "Выберите лимит участников из выпадающего меню:", 
            view=LimitView(self.channel), 
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f"Бот {bot.user.name} запущен!")

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == TEMP_CHANNEL_ID:
        guild = bot.get_guild(GUILD_ID)
        category = guild.get_channel(CATEGORY_ID)
        if not category:
            return

        try:
            temp_channel = await guild.create_voice_channel(
                name=f"🔊 {member.display_name}",
                category=category
            )
            await member.move_to(temp_channel)
            temp_channels[temp_channel.id] = temp_channel
            channel_limits[temp_channel.id] = 10

            control_channel = guild.get_channel(CONTROL_CHANNEL_ID)
            if control_channel:
                message = await control_channel.send(
                    content=f"🎛 Управление каналом {temp_channel.mention}",
                    view=VoiceControlPanel(temp_channel)
                )
                message_control_map[temp_channel.id] = message
                view = VoiceControlPanel(temp_channel, control_message_id=message.id)
                await message.edit(view=view)
        except Exception as e:
            print(f"Ошибка при создании канала: {e}")

    if before.channel and before.channel.id in temp_channels:
        if len(before.channel.members) == 0:
            try:
                await before.channel.delete()
                del temp_channels[before.channel.id]
                del channel_limits[before.channel.id]

                if before.channel.id in message_control_map:
                    await message_control_map[before.channel.id].delete()
                    del message_control_map[before.channel.id]
            except Exception as e:
                print(f"Ошибка при удалении канала: {e}")

bot.run(TOKEN)
