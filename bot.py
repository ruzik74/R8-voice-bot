import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import os
from keep_alive import keep_alive  # Импортируем web-сервер

# Конфигурация (переменные окружения)
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Токен берём из переменных окружения
GUILD_ID = int(os.getenv("GUILD_ID", 1355204242595516841))
CATEGORY_ID = int(os.getenv("CATEGORY_ID", 1355204243191238851))
TEMP_CHANNEL_ID = int(os.getenv("TEMP_CHANNEL_ID", 1355208133709926643))
CONTROL_CHANNEL_ID = int(os.getenv("CONTROL_CHANNEL_ID", 1357392366599802971))

temp_channels = {}
channel_limits = {}
message_control_map = {}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

class VoiceControlPanel(View):
    def __init__(self, channel):
        super().__init__(timeout=None)
        self.channel = channel
    
    @discord.ui.button(label="Lock", style=discord.ButtonStyle.gray)
    async def lock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Канал закрыт", ephemeral=True)
    
    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.gray)
    async def unlock(self, interaction: discord.Interaction, button: Button):
        await self.channel.set_permissions(interaction.guild.default_role, connect=True)
        await interaction.response.send_message("🔓 Канал открыт", ephemeral=True)

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
            channel_limits[temp_channel.id] = 10  # По умолчанию 10
            
            control_channel = guild.get_channel(CONTROL_CHANNEL_ID)
            if control_channel:
                control_panel = VoiceControlPanel(temp_channel)
                message = await control_channel.send(
                    content=f"🎛️ Управление каналом {temp_channel.mention}",
                    view=control_panel
                )
                message_control_map[temp_channel.id] = message
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

# Запуск веб-сервера (чтобы Render не выключал бота)
keep_alive()

bot.run(TOKEN)