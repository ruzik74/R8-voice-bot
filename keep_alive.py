from flask import Flask
import os
from discord.ext import commands
import discord

app = Flask(__name__)

# Ваш бот
bot = commands.Bot(command_prefix="!")

@app.route('/')
def home():
    return 'Привет, мир!'

@app.route('/status')
def status():
    return 'Бот работает!'

# Запуск бота
@bot.event
async def on_ready():
    print(f'Бот {bot.user} подключен!')

def run_bot():
    bot.run(os.getenv('DISCORD_TOKEN'))  # Получение токена из переменных среды

if __name__ == '__main__':
    app.run(debug=True)
