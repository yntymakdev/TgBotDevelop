import asyncio
import logging
from aiohttp import web  # ✅ aiohttp web server

from aiogram.webhook.aiohttp_server import SimpleRequestHandler
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

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота (замените на свой)
BOT_TOKEN = "8143610615:AAE7VnGdGCehu9dVhs_jxPysT3rHc8H3I7E"

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://yourdomain.com{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
# Система рангов
class Rank(Enum):
    E = "E"
    D = "D"
    C = "C"
    B = "B"
    A = "A"
    S = "S"
    SS = "SS"
    SSS = "SSS"
    NATIONAL = "National Level"
    MONARCH = "Monarch"


@dataclass
class RankInfo:
    rank: Rank
    name: str
    description: str
    emoji: str
    color: str
    min_level: int
    special_abilities: List[str]


# Система рангов с требованиями
class RankSystem:
    RANKS = {
        Rank.E: RankInfo(
            rank=Rank.E,
            name="E-Rank Hunter",
            description="Начинающий охотник",
            emoji="🟫",
            color="Brown",
            min_level=1,
            special_abilities=["Базовые навыки"]
        ),
        Rank.D: RankInfo(
            rank=Rank.D,
            name="D-Rank Hunter",
            description="Слабый охотник",
            emoji="🟪",
            color="Purple",
            min_level=5,
            special_abilities=["Усиленная выносливость", "Базовая интуиция"]
        ),
        Rank.C: RankInfo(
            rank=Rank.C,
            name="C-Rank Hunter",
            description="Средний охотник",
            emoji="🟦",
            color="Blue",
            min_level=10,
            special_abilities=["Улучшенная сила", "Быстрое восстановление", "Духовная защита"]
        ),
        Rank.B: RankInfo(
            rank=Rank.B,
            name="B-Rank Hunter",
            description="Сильный охотник",
            emoji="🟩",
            color="Green",
            min_level=25,
            special_abilities=["Высокая сила", "Лидерские качества", "Защита от сглаза"]
        ),
        Rank.A: RankInfo(
            rank=Rank.A,
            name="A-Rank Hunter",
            description="Элитный охотник",
            emoji="🟨",
            color="Yellow",
            min_level=50,
            special_abilities=["Экстремальная сила", "Тактическое мышление", "Баракат в делах"]
        ),
        Rank.S: RankInfo(
            rank=Rank.S,
            name="S-Rank Hunter",
            description="Легендарный охотник",
            emoji="🟧",
            color="Orange",
            min_level=100,
            special_abilities=["Невероятная сила", "Способность обучать", "Особая связь с Аллахом"]
        ),
        Rank.SS: RankInfo(
            rank=Rank.SS,
            name="SS-Rank Hunter",
            description="Мифический охотник",
            emoji="🟥",
            color="Red",
            min_level=250,
            special_abilities=["Сверхъестественные способности", "Влияние на сообщество", "Чудеса через дуа"]
        ),
        Rank.SSS: RankInfo(
            rank=Rank.SSS,
            name="SSS-Rank Hunter",
            description="Божественный охотник",
            emoji="⭐",
            color="Gold",
            min_level=500,
            special_abilities=["Божественная сила", "Изменение судеб", "Прямая связь с небесами"]
        ),
        Rank.NATIONAL: RankInfo(
            rank=Rank.NATIONAL,
            name="National Level Hunter",
            description="Охотник национального уровня",
            emoji="👑",
            color="Royal",
            min_level=1000,
            special_abilities=["Защита нации", "Массовое влияние", "Покровительство Аллаха"]
        ),
        Rank.MONARCH: RankInfo(
            rank=Rank.MONARCH,
            name="Monarch",
            description="Монарх - высший ранг",
            emoji="🔥",
            color="Divine",
            min_level=2000,
            special_abilities=["Абсолютная сила", "Контроль реальности", "Халиф на земле"]
        )
    }

    @staticmethod
    def get_rank_by_level(level: int) -> RankInfo:
        """Определяет ранг по уровню"""
        for rank in reversed(list(RankSystem.RANKS.values())):
            if level >= rank.min_level:
                return rank
        return RankSystem.RANKS[Rank.E]

    @staticmethod
    def get_next_rank(current_rank: Rank) -> Optional[RankInfo]:
        """Получает следующий ранг"""
        ranks_order = [Rank.E, Rank.D, Rank.C, Rank.B, Rank.A, Rank.S, Rank.SS, Rank.SSS, Rank.NATIONAL, Rank.MONARCH]
        try:
            current_index = ranks_order.index(current_rank)
            if current_index < len(ranks_order) - 1:
                next_rank = ranks_order[current_index + 1]
                return RankSystem.RANKS[next_rank]
        except ValueError:
            pass
        return None

    @staticmethod
    def get_rank_progress(level: int) -> tuple:
        """Возвращает прогресс до следующего ранга"""
        current_rank = RankSystem.get_rank_by_level(level)
        next_rank = RankSystem.get_next_rank(current_rank.rank)

        if next_rank:
            progress = level - current_rank.min_level
            required = next_rank.min_level - current_rank.min_level
            return progress, required, next_rank
        return 0, 0, None


# Состояния для FSM
class BotStates(StatesGroup):
    waiting_for_task = State()
    waiting_for_xp = State()


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
    current_rank: str = "E"  # Добавлено поле для ранга
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
            Task("Коран 2 аят + перевод ", 4),
            Task("Арабский текст 10 слов", 5),
            Task("Английский 10 слов", 4),
            Task("100 отжимание", 5),
            Task("100 пресидание", 5),
            Task("100 пресс", 5),
            Task("100 турник", 5),
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

    def update_rank(self):
        """Обновляет ранг пользователя на основе уровня"""
        new_rank = RankSystem.get_rank_by_level(self.level)
        old_rank = self.current_rank
        self.current_rank = new_rank.rank.value
        return old_rank != self.current_rank, new_rank

    def get_rank_info(self) -> RankInfo:
        """Получает информацию о текущем ранге"""
        try:
            rank_enum = Rank(self.current_rank)
            return RankSystem.RANKS[rank_enum]
        except ValueError:
            return RankSystem.RANKS[Rank.E]


# Система уровней (как в Solo Leveling)
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
                        if 'rank' in user_data and 'current_rank' not in user_data:
                            user_data['current_rank'] = user_data.pop('rank')
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

                        # Добавляем поле current_rank если его нет
                        if 'current_rank' not in user_data:
                            user_data['current_rank'] = 'E'

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


# Глобальная база данных
db = UserDatabase()

# Создание бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# Клавиатуры
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Мой Статус"), KeyboardButton(text="✅ Задачи")],
            [KeyboardButton(text="🎖️ Мой Ранг"), KeyboardButton(text="🏆 Титулы")],
            [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="➕ Добавить Задачу")],
            [KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_tasks_keyboard(tasks: List[Task]):
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if task.completed else "⏳"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {task.name} (+{task.xp_reward}XP)",
            callback_data=f"task_{i}"
        )])

    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_titles_keyboard(titles: List[Title]):
    keyboard = []
    for i, title in enumerate(titles):
        status = "🏆" if title.achieved else "🔒"
        keyboard.append([InlineKeyboardButton(
            text=f"{status} {title.name}",
            callback_data=f"title_{i}"
        )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_rank_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="📊 Способности ранга", callback_data="rank_abilities")],
        [InlineKeyboardButton(text="🎯 Следующий ранг", callback_data="next_rank")],
        [InlineKeyboardButton(text="📈 Все ранги", callback_data="all_ranks")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Функции для работы с временем
def is_new_day(last_reset: datetime) -> bool:
    return datetime.now().date() > last_reset.date()


def time_until_reset() -> str:
    now = datetime.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_left = tomorrow - now

    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)

    return f"{hours}ч {minutes}м"


def should_apply_penalty(last_reset: datetime) -> bool:
    """Проверяет, прошло ли более 24 часов с последнего сброса"""
    return datetime.now() - last_reset > timedelta(hours=24)


# Обработчики команд
@router.message(Command("start"))
async def cmd_start(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")
    rank_info = user_stats.get_rank_info()

    welcome_text = f"""
🕌 **Мусульманская система Развития**
♾️ Цель: Улучшение до самой смерти

🎮 Добро пожаловать в систему уровней, {message.from_user.first_name}!

📊 Ваш текущий статус:
🆙 Level: {user_stats.level}
{rank_info.emoji} Ранг: {rank_info.name}
⭐️ XP: {user_stats.xp}/{LevelSystem.get_xp_for_next_level(user_stats.level)}
🎯 Общий XP: {user_stats.total_xp}

⏰ Время до сброса: {time_until_reset()}

📌 Важно:
• Level — не финал, а "температура души"
• Ранг — показатель вашей силы как мусульманина
• XP — собирается за искренние действия
• Грехи, показуха, лень — снижают XP
• Каждый день — это шанс расти ради Аллаха

🌟 Путь до смерти — путь служения и развития

Используйте кнопки ниже для навигации:
"""

    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")


@router.message(F.text == "📊 Мой Статус")
async def show_status(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")

    # Проверка на новый день и применение штрафов
    if is_new_day(user_stats.last_reset):
        if should_apply_penalty(user_stats.last_reset) and not user_stats.penalty_applied:
            # Применяем штрафы за невыполненные задачи
            penalty_xp = 0
            for task in user_stats.daily_tasks:
                if not task.completed:
                    penalty_xp += 10

            user_stats.xp = max(0, user_stats.xp - penalty_xp)  # ✅ теперь правильно

            user_stats.penalty_applied = True

            if penalty_xp > 0:
                await message.answer(f"⚠️ Штраф применен! -{penalty_xp}XP за невыполненные задачи вчера",
                                     parse_mode="Markdown")

        # Сброс ежедневных задач
        user_stats.daily_tasks = user_stats.get_default_tasks()
        user_stats.last_reset = datetime.now()
        user_stats.penalty_applied = False
        db.update_user(user_stats)

    # Пересчет уровня
    new_level = LevelSystem.calculate_level(user_stats.total_xp)
    if new_level != user_stats.level:
        user_stats.level = new_level

        # Проверка повышения ранга
        rank_up, new_rank_info = user_stats.update_rank()
        if rank_up:
            await message.answer(f"🎉 RANK UP! Вы достигли ранга {new_rank_info.emoji} {new_rank_info.name}!\n"
                                 f"🔥 Новые способности разблокированы!", parse_mode="Markdown")

        db.update_user(user_stats)
        await message.answer(f"🎉 LEVEL UP! Вы достигли уровня {new_level}!", parse_mode="Markdown")

    completed_tasks = sum(1 for task in user_stats.daily_tasks if task.completed)
    total_tasks = len(user_stats.daily_tasks)
    rank_info = user_stats.get_rank_info()

    status_text = f"""
🎮 СИСТЕМА УРОВНЕЙ SOLO LEVELING

👤 Игрок: {message.from_user.first_name}
🆙 Level: {user_stats.level}
{rank_info.emoji} Ранг: {rank_info.name}
⭐️ XP: {user_stats.xp}/{LevelSystem.get_xp_for_next_level(user_stats.level)}
🎯 Общий XP: {user_stats.total_xp}

📅 Дата: {datetime.now().strftime('%d.%m.%Y')}
✅ Задачи выполнены: {completed_tasks}/{total_tasks}
📊 XP за день: {sum(task.xp_reward for task in user_stats.daily_tasks if task.completed)}

⏰ Время до сброса: {time_until_reset()}

🏆 Достижения: {sum(1 for title in user_stats.titles if title.achieved)}/{len(user_stats.titles)}
"""

    await message.answer(status_text, parse_mode="Markdown")


@router.message(F.text == "🎖️ Мой Ранг")
async def show_rank(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")
    rank_info = user_stats.get_rank_info()

    # Получаем прогресс до следующего ранга
    progress, required, next_rank = RankSystem.get_rank_progress(user_stats.level)

    progress_text = ""
    if next_rank:
        progress_bar = "▓" * (progress * 10 // required) + "░" * (10 - (progress * 10 // required))
        progress_text = f"""
📈 Прогресс до следующего ранга:
{next_rank.emoji} {next_rank.name}
[{progress_bar}] {progress}/{required} уровней

💡 Нужно достичь {next_rank.min_level} уровня
"""
    else:
        progress_text = "\n🔥 Вы достигли максимального ранга!"

    abilities_text = "\n".join([f"• {ability}" for ability in rank_info.special_abilities])

    rank_text = f"""
🎖️ ИНФОРМАЦИЯ О РАНГЕ

{rank_info.emoji} **{rank_info.name}**
📝 {rank_info.description}

🔥 Специальные способности:
{abilities_text}

📊 Требования:
• Минимальный уровень: {rank_info.min_level}
• Ваш уровень: {user_stats.level}
{progress_text}

💪 Чем выше ранг, тем больше баракат в ваших делах!
"""

    await message.answer(rank_text, reply_markup=get_rank_keyboard(), parse_mode="Markdown")


@router.message(F.text == "✅ Задачи")
async def show_tasks(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")

    tasks_text = f"""
📋 ЕЖЕДНЕВНЫЕ ЗАДАЧИ

⏰ Время до сброса: {time_until_reset()}

Нажмите на задачу чтобы отметить как выполненную:
"""

    await message.answer(tasks_text, reply_markup=get_tasks_keyboard(user_stats.daily_tasks), parse_mode="Markdown")


@router.message(F.text == "🏆 Титулы")
async def show_titles(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")

    titles_text = f"""
🏆 ТИТУЛЫ И ДОСТИЖЕНИЯ

Ваши титулы: {sum(1 for title in user_stats.titles if title.achieved)}/{len(user_stats.titles)}

Нажмите на титул чтобы узнать подробности:
"""

    await message.answer(titles_text, reply_markup=get_titles_keyboard(user_stats.titles), parse_mode="Markdown")


@router.message(F.text == "📈 Статистика")
async def show_statistics(message: Message):
    user_stats = db.get_user(message.from_user.id, message.from_user.username or "")
    rank_info = user_stats.get_rank_info()

    days_active = (datetime.now() - user_stats.last_reset).days + 1
    avg_xp_per_day = user_stats.total_xp / max(days_active, 1)

    stats_text = f"""
📈 ПОДРОБНАЯ СТАТИСТИКА

🎮 Прогресс в системе:
• Уровень: {user_stats.level}
• Ранг: {rank_info.emoji} {rank_info.name}
• Текущий XP: {user_stats.xp}
• Общий XP: {user_stats.total_xp}
• Среднее XP в день: {avg_xp_per_day:.1f}

📊 Задачи сегодня:
"""

    for task in user_stats.daily_tasks:
        status = "✅" if task.completed else "❌"
        time_completed = task.completion_time.strftime("%H:%M") if task.completion_time else "—"
        stats_text += f"• {status} {task.name} ({time_completed})\n"

    stats_text += f"""
🏆 Достижения:
• Получено титулов: {sum(1 for title in user_stats.titles if title.achieved)}
• Всего титулов: {len(user_stats.titles)}

⏰ Время:
• Дней в системе: {days_active}
• Время до сброса: {time_until_reset()}
"""

    await message.answer(stats_text, parse_mode="Markdown")


@router.message(F.text == "➕ Добавить Задачу")
async def add_task_start(message: Message, state: FSMContext):
    await message.answer("📝 Введите название новой задачи:", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_for_task)


@router.message(StateFilter(BotStates.waiting_for_task))
async def add_task_name(message: Message, state: FSMContext):
    task_name = message.text.strip()
    if len(task_name) > 100:
        await message.answer("❌ Название задачи слишком длинное. Максимум 100 символов.")
        return

    await state.update_data(task_name=task_name)
    await message.answer("🎯 Введите количество XP за выполнение (1-50):", parse_mode="Markdown")
    await state.set_state(BotStates.waiting_for_xp)


@router.message(StateFilter(BotStates.waiting_for_xp))
async def add_task_xp(message: Message, state: FSMContext):
    try:
        xp_reward = int(message.text.strip())
        if xp_reward < 1 or xp_reward > 50:
            await message.answer("❌ XP должно быть от 1 до 50.")
            return

        data = await state.get_data()
        task_name = data['task_name']

        user_stats = db.get_user(message.from_user.id, message.from_user.username or "")
        user_stats.daily_tasks.append(Task(name=task_name, xp_reward=xp_reward))
        db.update_user(user_stats)

        await message.answer(f"✅ Задача добавлена!**\n📝 {task_name}\n🎯 +{xp_reward}XP", parse_mode="Markdown")
        await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректное число.")


@router.message(F.text == "ℹ️ Помощь")
async def show_help(message: Message):
    help_text = """
🎮 **ПОМОЩЬ ПО СИСТЕМЕ УРОВНЕЙ

🎯 Основные принципы:
• Выполняйте ежедневные задачи для получения XP
• Накапливайте XP для повышения уровня
• Система сбрасывается каждые 24 часа
• За невыполненные задачи применяются штрафы

📊 Система XP:
• 1-2 уровень: 10XP
• 2-3 уровень: 30XP
• 3-4 уровень: 50XP
• 4-5 уровень: 100XP
• 5-10 уровень: 500XP каждый
• 10-25 уровень: 1000XP каждый

⚠️ Штрафы:
• За каждую невыполненную задачу: -10XP
• Штрафы применяются через 24 часа после сброса

🎮 Кнопки:
• 📊 Мой Статус - текущий уровень и XP
• ✅ Задачи - список ежедневных задач
• 🏆 Титулы - достижения и награды
• 📈 Статистика - подробная статистика
• ➕ Добавить Задачу - создать новую задачу

🤲 Помните: Это система для духовного роста ради Аллаха!
"""

    await message.answer(help_text, parse_mode="Markdown")


# Обработчики callback-запросов
@router.callback_query(F.data.startswith("task_"))
async def handle_task_completion(callback: CallbackQuery):
    try:
        task_index = int(callback.data.split("_")[1])
        user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")

        if 0 <= task_index < len(user_stats.daily_tasks):
            task = user_stats.daily_tasks[task_index]

            if not task.completed:
                task.completed = True
                task.completion_time = datetime.now()
                user_stats.xp += task.xp_reward
                user_stats.total_xp += task.xp_reward

                # Проверка повышения уровня
                new_level = LevelSystem.calculate_level(user_stats.total_xp)
                level_up_text = ""
                if new_level > user_stats.level:
                    user_stats.level = new_level
                    level_up_text = f"\n🎉 LEVEL UP! Уровень {new_level}!"

                db.update_user(user_stats)

                await callback.answer(f"✅ +{task.xp_reward}XP!" + level_up_text, show_alert=True)

                # Обновление клавиатуры
                await callback.message.edit_reply_markup(reply_markup=get_tasks_keyboard(user_stats.daily_tasks))
            else:
                await callback.answer("✅ Задача уже выполнена!", show_alert=True)
        else:
            await callback.answer("❌ Задача не найдена!", show_alert=True)

    except Exception as e:
        logger.error(f"Error in task completion: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@router.callback_query(F.data == "refresh_tasks")
async def refresh_tasks(callback: CallbackQuery):
    user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")
    await callback.message.edit_reply_markup(reply_markup=get_tasks_keyboard(user_stats.daily_tasks))
    await callback.answer("🔄 Обновлено!")


@router.callback_query(F.data.startswith("title_"))
async def handle_title_info(callback: CallbackQuery):
    try:
        title_index = int(callback.data.split("_")[1])
        user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")

        if 0 <= title_index < len(user_stats.titles):
            title = user_stats.titles[title_index]
            status = "🏆 Получен" if title.achieved else "🔒 Заблокирован"
            date_text = f"\n📅 Получен: {title.achieved_date.strftime('%d.%m.%Y')}" if title.achieved_date else ""

            title_info = f"""
🏆 {title.name}

📝 Описание: {title.description}
🎯 Статус: {status}{date_text}

💡 Совет: Продолжайте выполнять задачи для получения титулов!
"""

            await callback.answer(title_info, show_alert=True)
        else:
            await callback.answer("❌ Титул не найден!", show_alert=True)

    except Exception as e:
        logger.error(f"Error in title info: {e}")
        await callback.answer("❌ Произошла ошибка!", show_alert=True)


@router.callback_query(F.data == "rank_abilities")
async def show_rank_abilities(callback: CallbackQuery):
    user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")
    rank_info = user_stats.get_rank_info()

    abilities_text = "\n".join([f"• {ability}" for ability in rank_info.special_abilities])

    abilities_info = f"""
🔥 СПОСОБНОСТИ РАНГА {rank_info.emoji} {rank_info.name}

{abilities_text}

💡 Эти способности помогают в духовном развитии!
"""

    await callback.answer(abilities_info, show_alert=True)


@router.callback_query(F.data == "next_rank")
async def show_next_rank(callback: CallbackQuery):
    user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")
    current_rank_info = user_stats.get_rank_info()

    next_rank = RankSystem.get_next_rank(current_rank_info.rank)

    if next_rank:
        levels_needed = next_rank.min_level - user_stats.level

        next_rank_info = f"""
🎯 СЛЕДУЮЩИЙ РАНГ: {next_rank.emoji} {next_rank.name}

📊 Требования:
- Нужный уровень: {next_rank.min_level}
- Ваш уровень: {user_stats.level}
- Осталось: {levels_needed} ур.

💪 Продолжайте выполнять задачи!
"""
    else:
        next_rank_info = f"""
🔥 МАКСИМАЛЬНЫЙ РАНГ!

{current_rank_info.emoji} Вы достигли высшего ранга: {current_rank_info.name}

👑 Поздравляем!
"""

    await callback.answer(next_rank_info, show_alert=True)


@router.callback_query(F.data == "all_ranks")
async def show_all_ranks(callback: CallbackQuery):
    user_stats = db.get_user(callback.from_user.id, callback.from_user.username or "")

    # Отправляем как обычное сообщение, а не alert
    ranks_text = "🎖️ **ВСЕ РАНГИ В СИСТЕМЕ:**\n\n"

    for rank_enum in [Rank.E, Rank.D, Rank.C, Rank.B, Rank.A, Rank.S, Rank.SS, Rank.SSS, Rank.NATIONAL, Rank.MONARCH]:
        rank_info = RankSystem.RANKS[rank_enum]

        current_mark = " ← ВЫ" if user_stats.current_rank == rank_enum.value else ""

        ranks_text += f"{rank_info.emoji} **{rank_info.name}** (Ур.{rank_info.min_level}+){current_mark}\n"

    ranks_text += "\n💡 Повышайте уровень для новых рангов!"

    # Отправляем как новое сообщение вместо alert
    await callback.message.answer(ranks_text, parse_mode="Markdown")
    await callback.answer()
# Регистрация роутера
dp.include_router(router)


# Функция для периодической проверки штрафов
async def check_penalties():
    while True:
        try:
            current_time = datetime.now()
            for user_id, user_stats in db.users.items():
                # Проверяем, что день сменился
                if is_new_day(user_stats.last_reset):
                    # Сбрасываем задачи и состояние пользователя
                    user_stats.daily_tasks = user_stats.get_default_tasks()
                    user_stats.last_reset = current_time
                    user_stats.penalty_applied = False
                    # Можно сбросить другие поля, если нужно

                    db.update_user(user_stats)

                # Проверяем и применяем штрафы, если есть невыполненные задачи
                if should_apply_penalty(user_stats.last_reset) and not user_stats.penalty_applied:
                    penalty_xp = 0
                    for task in user_stats.daily_tasks:
                        if not task.completed:
                            penalty_xp += 10
                    user_stats.xp = max(0, user_stats.xp - penalty_xp)
                    user_stats.penalty_applied = True
                    db.update_user(user_stats)

                    # Уведомление пользователя (если нужно)
                    try:
                        await bot.send_message(
                            user_id,
                            f"⚠️ Штраф применен! -{penalty_xp}XP за невыполненные задачи.\n"
                            f"⏰ У вас было более 24 часов на выполнение задач.\n"
                            f"🎯 Сегодня новый день - новые возможности!",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send penalty notification to {user_id}: {e}")

            await asyncio.sleep(3600)  # Проверяем каждый час

        except Exception as e:
            logger.error(f"Error in penalty check: {e}")
            await asyncio.sleep(3600)


async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    app["penalty_task"] = asyncio.create_task(check_penalties())  # ✅ ЗАПУСКАЕМ фоновую задачу

async def on_shutdown(app):
    await bot.delete_webhook()
    await app["penalty_task"]  # ✅ Завершаем задачу
    await bot.session.close()
async def main():
    app = web.Application()
    app["bot"] = bot
    # Webhook handler
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    # aiohttp сам запускает сервер
    await web._run_app(app, host="0.0.0.0", port=3000)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
