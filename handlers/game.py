from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards import join_game_keyboard, start_game_keyboard, kill_player_keyboard
from utils import create_game, add_player_to_game, start_game, kill_player

router = Router()

@router.message(F.text == "/create")
async def create_new_game(message: Message):
    game = await create_game(message.chat.id)
    await message.answer(
        f"<b>🃏 Игра #{game.id} создана!</b>\n"
        "Пригласите игроков присоединиться.",
        reply_markup=join_game_keyboard(game.id)
    )

@router.callback_query(F.data.startswith("join_"))
async def handle_join(query: CallbackQuery):
    game_id = int(query.data.split("_")[1])
    await add_player_to_game(game_id, query.from_user.id, query.from_user.first_name)
    await query.message.edit_text(
        f"✅ <b>{query.from_user.first_name}</b> присоединился к игре!",
        reply_markup=query.message.reply_markup
    )

@router.callback_query(F.data.startswith("start_"))
async def handle_start(query: CallbackQuery):
    game_id = int(query.data.split("_")[1])
    players = await start_game(game_id)
    await query.message.edit_text(
        "🚀 <b>Игра началась!</b>\n"
        "Всем игрокам розданы роли.\n"
        "Желаем удачи!"
    )

@router.message(F.text.startswith("/kill"))
async def kill_command(message: Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Укажите ID игрока для убийства: /kill <player_id>")
        return
    player_id = int(parts[1])
    await kill_player(player_id)
    await message.answer(f"💀 Игрок с ID {player_id} был убит.")
