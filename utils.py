import random
from telegram.ext import ContextTypes
from config import DEFAULT_ROLES

# Получить имя игрока
async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        user = await context.bot.get_chat(user_id)
        return user.first_name or user.username or "Игрок"
    except:
        return "Неизвестный"

# Назначить роли
async def assign_roles(pool, room_id):
    async with pool.acquire() as conn:
        players = await conn.fetch(
            "SELECT user_id FROM players WHERE room_id = $1", room_id
        )
        user_ids = [p["user_id"] for p in players]

        roles_rows = await conn.fetch(
            "SELECT role, count FROM room_roles WHERE room_id = $1", room_id
        )
        roles = {r["role"]: r["count"] for r in roles_rows} if roles_rows else DEFAULT_ROLES

        role_list = []
        for role, count in roles.items():
            role_list.extend([role] * count)
        while len(role_list) < len(user_ids):
            role_list.append("Мирный житель")

        random.shuffle(role_list)

        for user_id, role in zip(user_ids, role_list):
            await conn.execute(
                "UPDATE players SET role = $1 WHERE user_id = $2 AND room_id = $3",
                role, user_id, room_id
            )

# Отправить роль игроку
async def send_private_role(context: ContextTypes.DEFAULT_TYPE, user_id, role):
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Ваша роль: {role}"
    )

# Получить статус комнаты
async def get_room_status(pool, room_id):
    async with pool.acquire() as conn:
        players = await conn.fetch(
            "SELECT user_id, role, alive FROM players WHERE room_id = $1",
            room_id
        )
        return players
