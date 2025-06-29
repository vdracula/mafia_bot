# utils.py

from telegram.ext import ContextTypes

async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id):
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

async def send_private_role(context: ContextTypes.DEFAULT_TYPE, user_id, role):
    ROLE_IMAGES = {
        "Мафия": "https://i.imgur.com/Qlntb6R.jpg ",
        "Доктор": "https://i.imgur.com/LfZxJQg.jpg ",
        "Комиссар": "https://i.imgur.com/RjVBYGq.jpg ",
        "Мирный житель": "https://i.imgur.com/WvK7Y9m.jpg "
    }
    try:
        await context.bot.send_photo(chat_id=user_id, photo=ROLE_IMAGES[role], caption=f"Ваша роль: {role}")
    except Exception as e:
        print(f"Ошибка отправки фото пользователю {user_id}: {e}")
        await context.bot.send_message(chat_id=user_id, text=f"Ваша роль: {role}")

def count_votes(votes):
    result = {}
    for v in votes.values():
        result[v] = result.get(v, 0) + 1
    return result