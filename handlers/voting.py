from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from utils import get_alive_players

router = Router()

class VotingState(StatesGroup):
    waiting_for_vote = State()

@router.message(Command("voting"))
async def start_voting(message: Message, state: FSMContext):
    game_id = 1  # Здесь должен быть реальный ID игры
    await state.update_data(game_id=game_id)
    alive_players = await get_alive_players(game_id)

    text = "Голосование началось!\nЖивые игроки:\n"
    text += "\n".join(f"— {p.name}" for p in alive_players)

    await message.answer(text)
    await state.set_state(VotingState.waiting_for_vote)
