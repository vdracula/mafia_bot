# config.py
import os

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/mafia_bot')

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
YOUR_ADMIN_ID = int(os.getenv('YOUR_ADMIN_ID', 775424515))

# Game settings
MAX_PLAYERS_PER_ROOM = 20
MIN_PLAYERS_TO_START = 4
DEFAULT_ROLES = {
    'Мафия': 1,
    'Доктор': 1,
    'Комиссар': 1,
    'Мирный житель': 4
}