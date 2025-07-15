import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Task:
    name: str
    xp_reward: int
    completed: bool = False
    completion_time: Optional[datetime] = None

@dataclass
class Title:
    name: str
    description: str
    achieved: bool = False
    achieved_date: Optional[datetime] = None

@dataclass
class UserStats:
    user_id: int
    username: str
    level: int = 1
    xp: int = 0
    total_xp: int = 0
    daily_tasks: List[Task] = None
    titles: List[Title] = None
    last_reset: datetime = None
    penalty_applied: bool = False

    def __post_init__(self):
        if self.daily_tasks is None:
            self.daily_tasks = self.get_default_tasks()
        if self.titles is None:
            self.titles = self.get_default_titles()
        if self.last_reset is None:
            self.last_reset = datetime.now()

    def get_default_tasks(self) -> List[Task]:
        return [
            Task("Коран 2 аят + перевод + 4 аята", 4),
            Task("Арабский текст 10 слов", 5),
            Task("Английский 10 слов", 4),
            Task("Тахаджуд (ночной намаз)", 5),
            Task("Помощь родителям", 5),
            Task("Зикр минимум 100 раз", 3),
            Task("Даават (призыв к Исламу)", 5),
            Task("Обучение другого человека", 5),
        ]

    def get_default_titles(self) -> List[Title]:
        return [
            Title("Хафиз", "Весь Коран наизусть"),
            Title("Строитель мечети", "Участвовал в строительстве мечети"),
            Title("Учитель поколений", "Научил 100+ человек"),
            Title("Радующий родителей", "Родители довольны"),
            Title("Постоянный", "40 дней подряд выполнял дело ради Аллаха"),
            Title("Чистый в омовении", "Не пропускает тахарат"),
            Title("Мустаид", "Сохраняет здоровье ради поклонения"),
            Title("Зикрящий", "Делает зикр каждый день минимум 100 раз"),
        ]
# Система уровней (как в Solo Leveling
# )
@dataclass

class LevelSystem:
    XP_REQUIREMENTS = {
        1: 10, 2: 30, 3: 50, 4: 100, 5: 500,
        10: 1000, 25: 2500, 50: 5000, 100: 10000
    }

    @staticmethod
    def get_xp_for_next_level(current_level: int) -> int:
        if current_level < 5:
            return LevelSystem.XP_REQUIREMENTS.get(current_level + 1, 100)
        elif current_level < 10:
            return 500
        elif current_level < 25:
            return 1000
        elif current_level < 50:
            return 2500
        else:
            return 5000

    @staticmethod
    def calculate_level(total_xp: int) -> int:
        level = 1
        xp_needed = 0

        for lvl in sorted(LevelSystem.XP_REQUIREMENTS.keys()):
            xp_needed += LevelSystem.XP_REQUIREMENTS[lvl]
            if total_xp >= xp_needed:
                level = lvl
            else:
                break

        return level

@dataclass
# Хранилище данных пользователей
class UserDatabase:
    def __init__(self):
        self.users: Dict[int, UserStats] = {}
        self.data_file = "users_data.json"
        self.load_data()

    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, user_data in data.items():
                        # Конвертация datetime строк обратно в datetime объекты
                        if user_data.get('last_reset'):
                            user_data['last_reset'] = datetime.fromisoformat(user_data['last_reset'])

                        # Конвертация задач
                        tasks = []
                        for task_data in user_data.get('daily_tasks', []):
                            task = Task(**task_data)
                            if task.completion_time:
                                task.completion_time = datetime.fromisoformat(task.completion_time)
                            tasks.append(task)
                        user_data['daily_tasks'] = tasks

                        # Конвертация титулов
                        titles = []
                        for title_data in user_data.get('titles', []):
                            title = Title(**title_data)
                            if title.achieved_date:
                                title.achieved_date = datetime.fromisoformat(title.achieved_date)
                            titles.append(title)
                        user_data['titles'] = titles

                        self.users[int(user_id)] = UserStats(**user_data)
        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def save_data(self):
        try:
            data = {}
            for user_id, user_stats in self.users.items():
                user_dict = asdict(user_stats)

                # Конвертация datetime в строки
                if user_dict.get('last_reset'):
                    user_dict['last_reset'] = user_dict['last_reset'].isoformat()

                # Конвертация задач
                for task in user_dict.get('daily_tasks', []):
                    if task.get('completion_time'):
                        task['completion_time'] = task['completion_time'].isoformat()

                # Конвертация титулов
                for title in user_dict.get('titles', []):
                    if title.get('achieved_date'):
                        title['achieved_date'] = title['achieved_date'].isoformat()

                data[str(user_id)] = user_dict

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def get_user(self, user_id: int, username: str = "") -> UserStats:
        if user_id not in self.users:
            self.users[user_id] = UserStats(user_id=user_id, username=username)
            self.save_data()
        return self.users[user_id]

    def update_user(self, user_stats: UserStats):
        self.users[user_stats.user_id] = user_stats
        self.save_data()

