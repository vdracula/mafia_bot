from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards import voting_keyboard
from utils import get_alive_players, save_vote, finish_voting

router = Router()

# FSM-состояния
class VotingStates(StatesGroup):
    choosing_candidates = State()
    collecting_votes = State()

@router.message(F.text == "/vote")
async def start_voting(message: Message, state: FSMContext):
    # Сохраним ID игры, если нужно
    await state.set_state(VotingStates.choosing_candidates)
    await message.answer(
        "🔍 <b>Выберите кандидатов на голосование.</b>\n"
        "Отправьте ID игроков через пробел."
    )

@router.message(VotingStates.choosing_candidates)
async def choose_candidates(message: Message, state: FSMContext):
    ids = message.text.strip().split()
    if not ids:
        await message.answer("❌ Укажите хотя бы одного кандидата.")
        return

    candidate_ids = [int(x) for x in ids]
    # Запоминаем кандидатов
    await state.update_data(candidates=candidate_ids)
    await state.set_state(VotingStates.collecting_votes)

    # Получаем список живых игроков
    alive_players = await get_alive_players()

    # Рассылка живым игрокам кнопок
    for player in alive_players:
        await message.bot.send_message(
            player.telegram_id,
            "🗳️ <b>Голосование началось!</b>\nВыберите игрока для голосования:",
            reply_markup=voting_keyboard(
                [(c, f"Игрок {c}") for c in candidate_ids]
            )
        )

    await message.answer("✅ Голосование запущено. Ожидаем голоса.")

@router.callback_query(F.data.startswith("vote_"))
async def receive_vote(query: CallbackQuery):
    voter_id = query.from_user.id
    voted_player_id = int(query.data.split("_")[1])

    await save_vote(voter_id, voted_player_id)

    await query.answer("✅ Ваш голос учтён.", show_alert=True)
    await query.message.edit_text("Спасибо! Ваш голос принят.")

@router.message(F.text == "/endvote")
async def end_voting(message: Message):
    results = await finish_voting()
    text = "📊 <b>Результаты голосования:</b>\n"
    for player_id, count in results.items():
        text += f"Игрок {player_id}: {count} голосов\n"
    await message.answer(text)
