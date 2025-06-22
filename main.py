import random
import asyncio
import logging
import os
import tempfile
from collections import deque
from typing import Optional

from config import *
from resources.strings import Strings

from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import F

# FSM states
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# Utils
from ai_utils.use_model import generate_midi


class StateMachine(StatesGroup):
    start = State()
    generating = State()


# Global vars
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Dictionary to store user language preferences
user_languages = {}

# Queue for MIDI generation
midi_queue = deque()
is_generating = False
current_generation_task = None

# Dictionary to track user processing states
user_processing = {}


@router.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in user_languages:
        user_languages[user_id] = "ru"
    await state.set_state(StateMachine.start)
    lang = user_languages[user_id]
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=Strings.get("start_dialog", lang),
        callback_data="generate_midi")
    )
    # Language switch button
    lang_switch = "en" if lang == "ru" else "ru"
    lang_text = "🇬🇧 English" if lang == "ru" else "🇷🇺 Русский"
    builder.add(types.InlineKeyboardButton(
        text=lang_text,
        callback_data=f"set_language_{lang_switch}")
    )
    await message.answer(
        Strings.get("greeting", lang),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("set_language_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = callback.data.split("_")[-1]  # 'ru' or 'en'
    user_languages[user_id] = lang
    # Re-show main menu in new language
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=Strings.get("start_dialog", lang),
        callback_data="generate_midi")
    )
    lang_switch = "en" if lang == "ru" else "ru"
    lang_text = "🇬🇧 English" if lang == "ru" else "🇷🇺 Русский"
    builder.add(types.InlineKeyboardButton(
        text=lang_text,
        callback_data=f"set_language_{lang_switch}")
    )
    await callback.message.edit_text(
        Strings.get("greeting", lang),
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data == "generate_midi")
async def start_midi_generation(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = user_languages.get(user_id, "ru")
    await state.set_state(StateMachine.generating)
    if user_id not in midi_queue:
        midi_queue.append(user_id)
    position = list(midi_queue).index(user_id) + 1
    await callback.message.answer(
        Strings.get("queue_position", lang).format(position=position)
    )
    if not is_generating:
        asyncio.create_task(process_midi_queue())
    await callback.answer()


@router.message(StateMachine.generating)
async def handle_generation_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_languages.get(user_id, "ru")
    if user_id not in midi_queue:
        midi_queue.append(user_id)
        position = len(midi_queue)
        await message.answer(
            Strings.get("queue_position", lang).format(position=position)
        )
    if not is_generating:
        asyncio.create_task(process_midi_queue())


def get_file_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=Strings.get("start_dialog", lang),
        callback_data="generate_midi")
    )
    lang_switch = "en" if lang == "ru" else "ru"
    lang_text = "🇬🇧 English" if lang == "ru" else "🇷🇺 Русский"
    builder.add(types.InlineKeyboardButton(
        text=lang_text,
        callback_data=f"set_language_{lang_switch}")
    )
    return builder.as_markup()


async def process_midi_queue():
    global is_generating, current_generation_task
    while midi_queue:
        is_generating = True
        user_id = midi_queue.popleft()
        try:
            lang = user_languages.get(user_id, "ru")
            status_message = await bot.send_message(
                user_id, 
                Strings.get("waiting_message_1", lang)
            )
            animation_frames = [
                Strings.get("waiting_message_1", lang),
                Strings.get("waiting_message_2", lang),
                Strings.get("waiting_message_3", lang),
                Strings.get("waiting_message_4", lang)
            ]
            animation_task = asyncio.create_task(
                animate_status_message(status_message, animation_frames)
            )
            current_generation_task = asyncio.create_task(
                generate_midi_async()
            )
            midi_data = await current_generation_task
            animation_task.cancel()
            await status_message.edit_text(
                Strings.get("generation_complete", lang)
            )
            with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as temp_file:
                midi_data.write(temp_file.name)
                temp_file_path = temp_file.name
            try:
                await bot.send_document(
                    user_id,
                    types.FSInputFile(temp_file_path),
                    caption=Strings.get("caption", lang),
                    reply_markup=get_file_keyboard(lang)
                )
            finally:
                os.unlink(temp_file_path)
        except Exception as e:
            logging.error(f"Error generating MIDI for user {user_id}: {e}")
            lang = user_languages.get(user_id, "ru")
            await bot.send_message(
                user_id,
                Strings.get("generation_error", lang)
            )
        finally:
            current_generation_task = None
    is_generating = False


async def generate_midi_async():
    """Async wrapper for MIDI generation"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_midi)


async def animate_status_message(message: types.Message, frames: list):
    """Animate status message with frames"""
    frame = 0
    while True:
        try:
            await message.edit_text(frames[frame % len(frames)])
            frame += 1
            await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Animation error: {e}")
            break


def get_main_menu_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text=Strings.get("start_dialog", lang),
        callback_data="generate_midi")
    )
    lang_switch = "en" if lang == "ru" else "ru"
    lang_text = "🇬🇧 English" if lang == "ru" else "🇷🇺 Русский"
    builder.add(types.InlineKeyboardButton(
        text=lang_text,
        callback_data=f"set_language_{lang_switch}")
    )
    return builder.as_markup()


# Функция запуска бота
async def main():
    await dp.start_polling(bot)


# Точка входа
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
