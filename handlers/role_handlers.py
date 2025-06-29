from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import DEFAULT_ROLES

# Настройка ролей
async def set_roles_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await update.message.reply_text("Комната не найдена или уже началась.")
            return

        room_id = room["id"]
        roles = await conn.fetch(
            "SELECT role, count FROM room_roles WHERE room_id = $1", room_id
        )
        role_dict = {r["role"]: r["count"] for r in roles} if roles else DEFAULT_ROLES

        keyboard = [
            [InlineKeyboardButton(f"{role}: {count}", callback_data=f"edit_{role}")]
            for role, count in role_dict.items()
        ]
        keyboard.append([InlineKeyboardButton("✅ Подтвердить роли", callback_data="confirm_roles")])

        await update.message.reply_text(
            "Настройка ролей:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Изменение количества ролей
async def edit_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role = query.data.split("_", 1)[1]

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data=f"set_{role}_-1"),
            InlineKeyboardButton("➕", callback_data=f"set_{role}_1")
        ]
    ]
    await query.edit_message_text(
        f"Изменить количество роли: {role}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Сохранение изменения количества ролей
async def update_role_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, role, delta = query.data.split("_")
    delta = int(delta)
    user_id = query.from_user.id
    pool = context.bot_data['pool']

    async with pool.acquire() as conn:
        room = await conn.fetchrow(
            "SELECT id FROM rooms WHERE host_id = $1 AND started = FALSE ORDER BY id DESC LIMIT 1",
            user_id
        )
        if not room:
            await query.edit_message_text("Комната не найдена или уже началась.")
            return

        room_id = room["id"]
        current = await conn.fetchval(
            "SELECT count FROM room_roles WHERE room_id = $1 AND role = $2",
            room_id, role
        )
        new_count = (current or DEFAULT_ROLES.get(role, 0)) + delta
        new_count = max(0, new_count)

        await conn.execute(
            "INSERT INTO room_roles (room_id, role, count) VALUES ($1, $2, $3) "
            "ON CONFLICT (room_id, role) DO UPDATE SET count = EXCLUDED.count",
            room_id, role, new_count
        )

        await set_roles_start(update, context)

# Подтверждение
async def confirm_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ Роли сохранены.")
