from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="menu_play")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")],
        [InlineKeyboardButton("🚪 Комнаты", callback_data="menu_rooms")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для игры в Мафию.", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
    ❓ Список команд:
/start - Запустить бота
/help - Показать список команд
/create_room - Создать комнату
/start_game - Начать игру
"""
    await update.message.reply_text(text)