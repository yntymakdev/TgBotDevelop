from typing import List
import math
from typing import Dict, Optional
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from models import Task, Title, Rank


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой Статус"), KeyboardButton(text="✅ Задачи")],
            [KeyboardButton(text="🏆 Титулы"), KeyboardButton(text="🎖️ Ранги")],
            [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="🏁 Рейтинг")],
            [KeyboardButton(text="➕ Добавить Задачу"), KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_tasks_keyboard(tasks: List[Task]) -> InlineKeyboardMarkup:
    """Клавиатура для задач"""
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task.completed else "⏳"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {task.name} (+{task.xp_reward}XP)",
            callback_data=f"task_{i}"
        )])

    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_titles_keyboard(titles: List[Title]) -> InlineKeyboardMarkup:
    """Клавиатура для титулов"""
    keyboard = []
    for i, title in enumerate(titles):
        status = "🏆" if title.achieved else "🔒"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {title.name}",
            callback_data=f"title_{i}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_ranks_keyboard(ranks: List[Rank]) -> InlineKeyboardMarkup:
    """Клавиатура для рангов"""
    keyboard = []
    for i, rank in enumerate(ranks):
        max_level_text = "∞" if rank.max_level == float('inf') else str(rank.max_level)
        keyboard.append([InlineKeyboardButton(
            text=f"{rank.color} {rank.code} - {rank.name} ({rank.min_level}-{max_level_text})",
            callback_data=f"rank_{i}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для рейтинга"""
    keyboard = [
        [InlineKeyboardButton(text="🏆 Топ по уровню", callback_data="rating_level")],
        [InlineKeyboardButton(text="⭐ Топ по XP", callback_data="rating_xp")],
        [InlineKeyboardButton(text="🎖️ По рангам", callback_data="rating_ranks")],
        [InlineKeyboardButton(text="📊 Моя позиция", callback_data="rating_position")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_rank_users_keyboard(rank_code: str) -> InlineKeyboardMarkup:
    """Клавиатура для пользователей определенного ранга"""
    keyboard = [
        [InlineKeyboardButton(text="👥 Показать игроков", callback_data=f"rank_users_{rank_code}")],
        [InlineKeyboardButton(text="🔙 Назад к рангам", callback_data="back_to_ranks")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)