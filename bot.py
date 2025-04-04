import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os
from keep_alive import keep_alive  # Поддержка работы на Render

# Конфигурация (переменные окружения)
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 1355204242595516841))
CATEGORY_ID = int(os.getenv("CATEGORY_ID", 1355204243191238851))
TEMP_CHANNEL_ID = int(os.getenv("TEMP_CHANNEL_ID", 1355208133709926643))
CONTROL_CHANNEL_ID = int(os.getenv("CONTROL_CHANNEL_ID", 1357392366599802971))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

class VoiceControlPanel(View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel
    
    @discord.ui.button(label="+ Слот", style=discord.ButtonStyle.blurple)
    async def add_slot(self, interaction: discord.Interaction, button: Button):
        if self.channel.user_limit < 10:
            await self.channel.edit(user_limit=self.channel.user_limit + 1)
            await interaction.response.send_message("✅ Добавлен 1 слот", ephemeral=True)
    
    @discord.ui.button(label="- Слот", style=discord.ButtonStyle.blurple)
    async def remove_slot(self, interaction: discord.Interaction, button: Button):
        if self.channel.user_limit > 1:
            await self.channel.edit(user_limit=self.channel.user_limit - 1)
            await interaction.response.send_message("✅ Убран 1 слот", ephemeral=True)
    
    @discord.ui.button(label="🔒 Закрыть", style=discord.ButtonStyle.gray)
    async def lock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Канал закрыт", ephemeral=True)
    
    @discord.ui.button(label="🔓 Открыть", style=discord.ButtonStyle.gray)
    async def unlock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Канал открыт", ephemeral=True)
    
    @discord.ui.button(label="🔇 Мьют всех", style=discord.ButtonStyle.gray)
    async def mute_all(self, interaction: discord.Interaction, button: Button):
        for member in self.channel.members:
            await member.edit(mute=True)
        await interaction.response.send_message("🔇 Все участники замьючены", ephemeral=True)
    
    @discord.ui.button(label="🔊 Размьют всех", style=discord.ButtonStyle.gray)
    async def unmute_all(self, interaction: discord.Interaction, button: Button):
        for member in self.channel.members:
            await member.edit(mute=False)
        await interaction.response.send_message("🔊 Все участники размьючены", ephemeral=True)
    
    @discord.ui.button(label="🚪 Кикнуть", style=discord.ButtonStyle.red)
    async def kick_user(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Введите @упоминание пользователя для кика:", ephemeral=True)
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', check=check, timeout=30)
            member = msg.mentions[0]
            await member.move_to(None)
            await interaction.followup.send(f"🚪 {member.mention} кикнут из канала.", ephemeral=True)
        except:
            await interaction.followup.send("❌ Ошибка: неверный пользователь или таймаут.", ephemeral=True)

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
            
            control_channel = guild.get_channel(CONTROL_CHANNEL_ID)
            if control_channel:
                control_panel = VoiceControlPanel(temp_channel)
                await control_channel.send(
                    content=f"🎛️ Управление {temp_channel.mention}",
                    view=control_panel
                )
        except Exception as e:
            print(f"Ошибка при создании канала: {e}")

keep_alive()
bot.run(TOKEN)
