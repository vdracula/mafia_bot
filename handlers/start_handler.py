from telegram import Update
from telegram.ext import ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕹 Команды:\n"
        "/start — Главное меню\n"
        "/start_game — Запустить игру\n"
        "/set_roles — Назначить роли\n"
        "/start_vote — Начать голосование\n"
        "/end_game — Завершить игру\n"
        "\nИспользуйте кнопки для управления."
    )
