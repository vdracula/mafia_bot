import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# === Импорт базы данных (замените на реальную реализацию при необходимости) ===
def init_db():
    print("База данных инициализирована")

# === Хранение комнат ===
rooms = {}

# === Роли и изображения ===
ROLE_IMAGES = {
    "Мафия": "https://i.imgur.com/Qlntb6R.jpg", 
    "Доктор": "https://i.imgur.com/LfZxJQg.jpg", 
    "Комиссар": "https://i.imgur.com/RjVBYGq.jpg", 
    "Мирный житель": "https://i.imgur.com/WvK7Y9m.jpg" 
}

DEFAULT_ROLE_COUNTS = {
    "Мафия": 1,
    "Доктор": 1,
    "Комиссар": 1,
    "Мирный житель": 5
}

# === Вспомогательные функции ===
async def get_user_name(context, user_id):
    try:
        user = await context.bot.get_chat(user_id)
        return user.first_name or user.username or "Игрок"
    except:
        return "Неизвестный"


def assign_roles(room):
    role_list = []
    for role, count in room["roles"].items():
        role_list.extend([role] * count)
    players = room["players"]
    random.shuffle(role_list)
    while len(role_list) < len(players):
        role_list.append("Мирный житель")
    room["assigned_roles"] = dict(zip(players, role_list))


async def send_private_role(context, user_id, role):
    try:
        await context.bot.send_photo(chat_id=user_id, photo=ROLE_IMAGES[role], caption=f"Ваша роль: {role}")
    except Exception as e:
        print(f"Ошибка отправки фото пользователю {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"Ваша роль: {role}")


# === Команды бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Играть", callback_data="menu_play")],
        [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")],
        [InlineKeyboardButton("🚪 Комнаты", callback_data="menu_rooms")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Я бот для игры в Мафию.", reply_markup=reply_markup)


# === Главное меню ===
async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "menu_play":
        keyboard = [
            [InlineKeyboardButton("🆕 Создать комнату", callback_data="create_room_prompt")],
            [InlineKeyboardButton("🚪 Присоединиться к комнате", callback_data="join_room_prompt")],
            [InlineKeyboardButton("🔄 Автоприсоединение", callback_data="auto_join_prompt")],
            [InlineKeyboardButton("🎮 Начать игру", callback_data="start_game_prompt")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите действие:", reply_markup=reply_markup)
    elif data == "menu_help":
        text = """
        ❓ Помощь:
        /create_room - Создать комнату
        /join_room - Присоединиться к комнате
        /rooms - Посмотреть список комнат
        /start_game - Начать игру
        /set_roles - Настроить роли
        /admin - Админ-панель
        """
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
    elif data == "menu_rooms":
        if not rooms:
            await query.answer("Нет доступных комнат.")
            return
        keyboard = []
        for room_name in rooms:
            keyboard.append([InlineKeyboardButton(room_name, callback_data=f"room_info_{room_name}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Список комнат:", reply_markup=reply_markup)
    elif data.startswith("room_info_"):
        room_name = data.replace("room_info_", "")
        if room_name not in rooms:
            await query.answer("Комната не найдена.")
            return
        room = rooms[room_name]
        player_names = "\n".join([await get_user_name(context, pid) for pid in room["players"]])
        msg = f"📌 Информация о комнате '{room_name}':\n"
        msg += f"Статус: {'🎮 В игре' if room['started'] else '🕒 Ожидает'}\n"
        msg += f"Игроков: {len(room['players'])}/8\n"
        msg += f"Участники:\n{player_names}"
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="menu_rooms")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(msg, reply_markup=reply_markup)
    elif data == "auto_join_prompt":
        await find_game(query, context)
        await query.edit_message_text("Вы автоматически присоединились к комнате.")
    elif data == "menu_back":
        keyboard = [
            [InlineKeyboardButton("🎮 Играть", callback_data="menu_play")],
            [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")],
            [InlineKeyboardButton("🚪 Комнаты", callback_data="menu_rooms")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Главное меню:", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
    ❓ Список команд:
/start - Запустить бота
/help - Показать список команд
/create_room [название] - Создать комнату
/join_room [название] - Присоединиться к комнате
/start_game - Начать игру
/set_roles - Настроить роли
/find_game - Автоприсоединение
/admin - Админ-панель
"""
    await update.message.reply_text(text)


# === Команды ===
async def create_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(update, Update):
        await update.message.reply_text("Введите название новой комнаты:")
    else:
        await update.edit_message_text("Введите название новой комнаты:")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    # Создание комнаты
    if context.user_data.get('waiting_for_room_name'):
        room_name = text
        if room_name in rooms:
            await update.message.reply_text("Комната с таким названием уже существует.")
            return
        rooms[room_name] = {
            "host": user_id,
            "chat_id": update.effective_chat.id,  # <-- сохраняем chat_id
            "players": [],
            "roles": DEFAULT_ROLE_COUNTS.copy(),
            "assigned_roles": {},
            "started": False,
            "stage": None,
            "votes": {}
        }
        await update.message.reply_text(f"✅ Комната '{room_name}' успешно создана!")
        context.user_data.pop('waiting_for_room_name', None)
        rooms[room_name]["players"].append(user_id)
        await update.message.reply_text(f"Вы автоматически присоединились к комнате '{room_name}'.")
        await show_current_roles(update, context, room_name, rooms[room_name])


# === Присоединение к комнате через выбор ===
async def join_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rooms:
        await update.message.reply_text("Нет доступных комнат.")
        return
    keyboard = [[InlineKeyboardButton(room_name, callback_data=f"select_join_{room_name}")] for room_name in rooms]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите комнату, к которой хотите присоединиться:", reply_markup=reply_markup)


# === Обработчик выбора комнаты ===
async def select_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("select_join_"):
        room_name = data.replace("select_join_", "")
        if room_name in rooms:
            room = rooms[room_name]
            if query.from_user.id in room["players"]:
                await query.edit_message_text("Вы уже состоите в этой комнате.")
                return
            room["players"].append(query.from_user.id)
            await query.edit_message_text(f"✅ Вы присоединились к комнате '{room_name}'.")
            await show_current_roles(query, context, room_name, room)


# === Показ списка комнат ===
async def list_rooms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not rooms:
        await update.message.reply_text("Пока нет активных комнат.")
        return
    msg = "🚪 Доступные комнаты:\n"
    for room_name, room in rooms.items():
        status = "🎮 В игре" if room["started"] else "🕒 Ожидает игроков"
        players_count = len(room["players"])
        msg += f"• {room_name} ({players_count} игроков) — {status}\n"
    await update.message.reply_text(msg)


# === Прочие команды ===
async def set_roles_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    for room_name, room in rooms.items():
        if user_id == room["host"] and not room["started"]:
            keyboard = [
                [InlineKeyboardButton("Мафия", callback_data="edit_mafia")],
                [InlineKeyboardButton("Доктор", callback_data="edit_doctor")],
                [InlineKeyboardButton("Комиссар", callback_data="edit_sheriff")],
                [InlineKeyboardButton("Мирный житель", callback_data="edit_peaceful")],
                [InlineKeyboardButton("Подтвердить настройки", callback_data="confirm_roles")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Выберите роль для изменения:", reply_markup=reply_markup)
            return
    await update.message.reply_text("Вы не являетесь ведущим или игра уже началась.")


# === Обработчики ролей (редактирование) ===
async def edit_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role_key = query.data.replace("edit_", "")
    role_map = {
        "mafia": "Мафия",
        "doctor": "Доктор",
        "sheriff": "Комиссар",
        "peaceful": "Мирный житель"
    }
    role = role_map.get(role_key)
    if not role:
        return
    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return
    room = rooms[room_name]
    current_count = room["roles"][role]
    buttons = []
    for delta in [-1, 0, +1]:
        new_count = max(0, current_count + delta)
        buttons.append(
            InlineKeyboardButton(f"{new_count}", callback_data=f"set_{role_key}_{new_count}")
        )
    keyboard = [[*buttons]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"Выберите количество для роли '{role}':", reply_markup=reply_markup)


async def update_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    role_key = data[1]
    count = int(data[2])
    role_map = {
        "mafia": "Мафия",
        "doctor": "Доктор",
        "sheriff": "Комиссар",
        "peaceful": "Мирный житель"
    }
    role = role_map.get(role_key)
    if not role:
        return
    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return
    room = rooms[room_name]
    room["roles"][role] = count
    keyboard = [
        [InlineKeyboardButton("Мафия", callback_data="edit_mafia")],
        [InlineKeyboardButton("Доктор", callback_data="edit_doctor")],
        [InlineKeyboardButton("Комиссар", callback_data="edit_sheriff")],
        [InlineKeyboardButton("Мирный житель", callback_data="edit_peaceful")],
        [InlineKeyboardButton("Подтвердить настройки", callback_data="confirm_roles")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите роль для изменения:", reply_markup=reply_markup)


async def confirm_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    room_name = None
    for rn, r in rooms.items():
        if r["host"] == query.from_user.id:
            room_name = rn
            break
    if not room_name:
        return
    room = rooms[room_name]
    total_players = sum(room["roles"].values())
    msg = f"✅ Роли установлены:\n"
    for role, count in room["roles"].items():
        msg += f"{role}: {count}\n"
    msg += f"\nОбщее количество игроков: {total_players}"
    await query.edit_message_text(msg)


async def show_current_roles(update: Update, context: ContextTypes.DEFAULT_TYPE, room_name=None, room=None):
    if not room_name or not room:
        user_id = update.effective_user.id
        for rn, r in rooms.items():
            if user_id in r["players"]:
                room_name = rn
                room = r
                break
        else:
            return
    msg = "🎭 Текущие роли:\n"
    for role, count in room["roles"].items():
        msg += f"{role}: {count}\n"
    total = sum(room["roles"].values())
    msg += f"\nОбщее количество игроков: {total}"
    await update.message.reply_text(msg)


# === Голосование днём ===
async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("vote_"):
        voted_player_id = int(data.split("_")[1])
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        for room_name, room in rooms.items():
            if chat_id == room["chat_id"] and room["stage"] == "day":  # Теперь сравниваем chat_id
                room["votes"][user_id] = voted_player_id
                voter_name = await get_user_name(context, user_id)
                target_name = await get_user_name(context, voted_player_id)
                await query.edit_message_text(text=f"{voter_name}, вы проголосовали за {target_name}")
                if len(room["votes"]) == len(room["players"]):
                    result = count_votes(room["votes"])
                    kicked = max(result, key=result.get)
                    kicked_name = await get_user_name(context, kicked)
                    await context.bot.send_message(chat_id=chat_id, text=f"❌ Игрок {kicked_name} был изгнан.")
                    room["players"].remove(kicked)
                    room["stage"] = "night"
                    room["votes"] = {}


def count_votes(votes):
    result = {}
    for v in votes.values():
        result[v] = result.get(v, 0) + 1
    return result


# === Запуск игры ===
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    for room_name, room in rooms.items():
        if user_id == room["host"] and not room["started"]:
            if len(room["players"]) < 4:
                await update.message.reply_text("Нужно минимум 4 игрока.")
                return
            assign_roles(room)
            room["started"] = True
            room["stage"] = "night"
            room["votes"] = {}
            for player_id in room["players"]:
                role = room["assigned_roles"][player_id]
                await send_private_role(context, player_id, role)
            await update.message.reply_text("🎮 Игра началась!\n🌙 Ночь. Все закрывают глаза...")
            return
    await update.message.reply_text("Вы не являетесь ведущим или игра уже начата.")


# === Автоприсоединение к игре ===
async def find_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    found = False
    for room_name, room in rooms.items():
        if not room["started"] and len(room["players"]) < 8:
            room["players"].append(user_id)
            await update.message.reply_text(f"✅ Вы присоединились к комнате '{room_name}'!")
            found = True
            break
    if not found:
        new_room = f"room_{len(rooms) + 1}"
        rooms[new_room] = {
            "host": user_id,
            "chat_id": update.effective_chat.id,  # <-- сохраняем chat_id
            "players": [user_id],
            "roles": {"Мафия": 1, "Доктор": 1, "Комиссар": 1, "Мирный житель": 5},
            "assigned_roles": {},
            "started": False,
            "stage": None,
            "votes": {}
        }
        await update.message.reply_text(f"✅ Создана новая комната: {new_room}")


# === Админ-панель ===
YOUR_ADMIN_ID = 775424515  # Замени на свой Telegram ID
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("🔒 У вас нет доступа.")
        return
    text = "🛠 Админ-панель:\n"
    for room_name, room in rooms.items():
        text += f"Комната: {room_name}\n Игроков: {len(room['players'])}\n Статус: {'🎮 В игре' if room['started'] else '🕒 Ожидает'}\n"
    keyboard = [
        [InlineKeyboardButton("Завершить игру", callback_data="end_game_admin")],
        [InlineKeyboardButton("Перезапустить игру", callback_data="restart_game_admin")],
        [InlineKeyboardButton("Посмотреть историю игр", callback_data="view_history")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)


# === Обработчик кнопок админ-панели ===
async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "restart_game_admin":
        keyboard = []
        for room_name in rooms:
            keyboard.append([InlineKeyboardButton(room_name, callback_data=f"restart_room_{room_name}")])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="menu_back_admin")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите комнату для перезапуска:", reply_markup=reply_markup)
    elif data.startswith("restart_room_"):
        room_name = data.replace("restart_room_", "")
        if room_name in rooms:
            room = rooms[room_name]
            room["started"] = False
            room["stage"] = None
            room["votes"] = {}
            room["assigned_roles"] = {}
            await query.edit_message_text(f"🔄 Игра в комнате '{room_name}' перезапущена.")
    elif data == "menu_back_admin":
        await admin_panel(update, context)


# === Центральный обработчик кнопок ===
async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    print(f"[DEBUG] Получен callback: {data}")

     if data == "menu_play":
        from main import create_play_menu
        await create_play_menu(query)
    elif data.startswith("room_info_"):
        await show_room_info(update, context, data)
    elif data == "menu_help":
        await show_help_menu(update, context)
    elif data == "auto_join_prompt":
        await auto_join_game(update, context)
    elif data == "menu_back":
        await back_to_main_menu(update, context)
    elif data.startswith("select_join_"):
        await select_room_handler(update, context)
    elif data.startswith("edit_"):
        await edit_role_count(update, context)
    elif data.startswith("set_"):
        await update_role_count(update, context)
    elif data == "confirm_roles":
        await confirm_roles(update, context)
    elif data.startswith("vote_"):
        await vote_handler(update, context)
    elif data in ["restart_game_admin", "end_game_admin", "view_history"]:
        await admin_button_handler(update, context)
    elif data.startswith("restart_room_"):
        await admin_button_handler(update, context)
    elif data == "menu_back_admin":
        await admin_panel(update, context)


# === Запуск бота ===
if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("create_room", create_room))
    app.add_handler(CommandHandler("join_room", join_room))
    app.add_handler(CommandHandler("rooms", list_rooms))
    app.add_handler(CommandHandler("start_game", start_game))
    app.add_handler(CommandHandler("set_roles", set_roles_start))
    app.add_handler(CommandHandler("find_game", find_game))
    app.add_handler(CommandHandler("admin", admin_panel))

    app.add_handler(CallbackQueryHandler(handle_callbacks))  # <-- один обработчик

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("Бот запущен...")
    app.run_polling()