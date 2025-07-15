from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum


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
class Rank:
    code: str
    name: str
    color: str
    min_level: int
    max_level: int


@dataclass
class UserStats:
    user_id: int
    username: str
    level: int = 1
    xp: int = 0
    total_xp: int = 0
    rank: str = "E"
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


class BotStates(Enum):
    WAITING_FOR_TASK = "waiting_for_task"
    WAITING_FOR_XP = "waiting_for_xp"