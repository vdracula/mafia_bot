from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DEFAULT_ROLES

ROLE_MAP = {
    "mafia": "Мафия",
    "doctor": "Доктор",
    "sheriff": "Комиссар",
    "peaceful": "Мирный житель"
}

async def set_roles_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['pool']
    user_id = update.effective_user.id
    async with pool.acquire() as conn:
        room = await conn.fetchrow("SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if not room:
            await update.message.reply_text("Вы не являетесь ведущим или игра уже началась.")
            return

    keyboard = [
        [InlineKeyboardButton("Мафия", callback_data="edit_mafia")],
        [InlineKeyboardButton("Доктор", callback_data="edit_doctor")],
        [InlineKeyboardButton("Комиссар", callback_data="edit_sheriff")],
        [InlineKeyboardButton("Мирный житель", callback_data="edit_peaceful")],
        [InlineKeyboardButton("Подтвердить настройки", callback_data="confirm_roles")]
    ]
    await update.message.reply_text("Выберите роль для изменения:", reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role_key = query.data.replace("edit_", "")
    role = ROLE_MAP.get(role_key)
    if not role:
        return

    pool = context.bot_data['pool']
    user_id = query.from_user.id
    async with pool.acquire() as conn:
        room = await conn.fetchrow("SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if not room:
            return
        count = await conn.fetchval("SELECT count FROM room_roles WHERE room_id = $1 AND role = $2", room["id"], role)
        count = count or DEFAULT_ROLES.get(role, 0)

    buttons = [
        InlineKeyboardButton(str(max(0, count - 1)), callback_data=f"set_{role_key}_{max(0, count - 1)}"),
        InlineKeyboardButton(str(count), callback_data=f"set_{role_key}_{count}"),
        InlineKeyboardButton(str(count + 1), callback_data=f"set_{role_key}_{count + 1}")
    ]
    await query.edit_message_text(f"Выберите количество для роли '{role}':", reply_markup=InlineKeyboardMarkup([buttons]))

async def update_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, role_key, count_str = query.data.split("_")
    role = ROLE_MAP.get(role_key)
    count = int(count_str)

    pool = context.bot_data['pool']
    user_id = query.from_user.id
    async with pool.acquire() as conn:
        room = await conn.fetchrow("SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if not room:
            return
        await conn.execute("INSERT INTO room_roles (room_id, role, count) VALUES ($1, $2, $3) ON CONFLICT (room_id, role) DO UPDATE SET count = EXCLUDED.count", room["id"], role, count)

    await set_roles_start(update, context)

async def confirm_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pool = context.bot_data['pool']
    user_id = query.from_user.id
    async with pool.acquire() as conn:
        room = await conn.fetchrow("SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE", user_id)
        if not room:
            return
        roles = await conn.fetch("SELECT role, count FROM room_roles WHERE room_id = $1", room["id"])

    msg = "✅ Роли установлены:\n"
    total = 0
    for r in roles:
        msg += f"{r['role']}: {r['count']}\n"
        total += r['count']
    msg += f"\nОбщее количество игроков: {total}"
    await query.edit_message_text(msg)