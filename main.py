from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from handlers import *
from db import init_db
import asyncio

async def main():
    # Initialize database
    pool = await init_db()
    
    # Build application
    app = ApplicationBuilder() \
        .token(TELEGRAM_BOT_TOKEN) \
        .post_init(lambda _: print("Bot started")) \
        .build()

    # Store pool in bot data
    app.bot_data['pool'] = pool

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("join_room", join_room))
    app.add_handler(CommandHandler("rooms", list_rooms))
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(handle_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())