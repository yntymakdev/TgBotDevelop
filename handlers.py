import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from models import Task, BotStates
from level_system import LevelSystem, RankSystem
from database import UserDatabase
from keyboards import (
    get_main_keyboard, get_tasks_keyboard, get_titles_keyboard,
    get_ranks_keyboard, get_rating_keyboard, get_rank_users_keyboard
)
from utils import (
    is_new_day, should_apply_penalty, format_user_stats,
    format_detailed_stats, format_top_users, calculate_penalty
)
from config import LEVEL_SYSTEM_CONFIG

logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Глобальная база данных (будет инициализирована в main.py)
db: UserDatabase = None


class BotStatesGroup(StatesGroup):
    waiting_for_task = State()


# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Регистрируем пользователя в базе данных
    db.register_user(user_id, username)

    # Проверяем, новый ли день для пользователя
    if is_new_day(user_id, db):
        # Применяем штраф за пропуск дня, если необходимо
        if should_apply_penalty(user_id, db):
            penalty = calculate_penalty(user_id, db)
            db.apply_penalty(user_id, penalty)
            await message.answer(
                f"⚠️ Вы пропустили день! Применен штраф: {penalty} очков опыта."
            )

        # Обновляем дату последнего входа
        db.update_last_login(user_id)

    user_stats = db.get_user_stats(user_id)
    welcome_text = f"""
🎯 Добро пожаловать в систему задач и достижений!

👤 {username}
📊 Ваши текущие показатели:
{format_user_stats(user_stats)}

Выберите действие:
    """

    await message.answer(welcome_text, reply_markup=get_main_keyboard())


# Обработчик кнопки "Задачи"
@router.callback_query(F.data == "tasks")
async def show_tasks(callback: CallbackQuery):
    """Показать меню задач"""
    await callback.answer()

    text = "📋 Выберите тип задачи:"
    await callback.message.edit_text(text, reply_markup=get_tasks_keyboard())


# Обработчик кнопки "Добавить задачу"
@router.callback_query(F.data == "add_task")
async def add_task(callback: CallbackQuery, state: FSMContext):
    """Начать процесс добавления задачи"""
    await callback.answer()

    await state.set_state(BotStatesGroup.waiting_for_task)

    text = """
📝 Введите описание задачи:

Пример: "Изучить Python в течение 2 часов"
    """

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())


# Обработчик ввода задачи
@router.message(StateFilter(BotStatesGroup.waiting_for_task))
async def process_task_input(message: Message, state: FSMContext):
    """Обработка введенной задачи"""
    user_id = message.from_user.id
    task_description = message.text.strip()

    if not task_description:
        await message.answer("❌ Описание задачи не может быть пустым!")
        return

    # Создаем задачу
    task = Task(
        user_id=user_id,
        description=task_description,
        created_at=datetime.now()
    )

    # Сохраняем в базу данных
    task_id = db.add_task(task)

    # Очищаем состояние
    await state.clear()

    await message.answer(
        f"✅ Задача добавлена!\n\n📝 {task_description}\n\n"
        f"ID задачи: {task_id}",
        reply_markup=get_main_keyboard()
    )


# Обработчик кнопки "Мои задачи"
@router.callback_query(F.data == "my_tasks")
async def show_my_tasks(callback: CallbackQuery):
    """Показать задачи пользователя"""
    await callback.answer()

    user_id = callback.from_user.id
    tasks = db.get_user_tasks(user_id)

    if not tasks:
        text = "📋 У вас нет активных задач."
    else:
        text = "📋 Ваши задачи:\n\n"
        for task in tasks:
            status = "✅" if task.completed else "⏳"
            text += f"{status} {task.id}. {task.description}\n"
            text += f"   📅 Создана: {task.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if task.completed:
                text += f"   🎉 Выполнена: {task.completed_at.strftime('%d.%m.%Y %H:%M')}\n"
            text += "\n"

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())


# Обработчик кнопки "Выполнить задачу"
@router.callback_query(F.data == "complete_task")
async def complete_task_menu(callback: CallbackQuery):
    """Показать меню выполнения задач"""
    await callback.answer()

    user_id = callback.from_user.id
    active_tasks = db.get_user_active_tasks(user_id)

    if not active_tasks:
        text = "📋 У вас нет активных задач для выполнения."
        await callback.message.edit_text(text, reply_markup=get_main_keyboard())
        return

    text = "✅ Выберите задачу для выполнения:\n\n"
    for task in active_tasks:
        text += f"⏳ {task.id}. {task.description}\n\n"

    # Создаем клавиатуру с активными задачами
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"✅ {task.id}. {task.description[:30]}...",
            callback_data=f"complete_task_{task.id}"
        )] for task in active_tasks
    ])
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="tasks")
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)


# Обработчик выполнения конкретной задачи
@router.callback_query(F.data.startswith("complete_task_"))
async def complete_specific_task(callback: CallbackQuery):
    """Выполнить конкретную задачу"""
    await callback.answer()

    user_id = callback.from_user.id
    task_id = int(callback.data.split("_")[-1])

    # Проверяем, что задача принадлежит пользователю
    task = db.get_task(task_id)
    if not task or task.user_id != user_id:
        await callback.message.edit_text(
            "❌ Задача не найдена или не принадлежит вам.",
            reply_markup=get_main_keyboard()
        )
        return

    if task.completed:
        await callback.message.edit_text(
            "✅ Эта задача уже выполнена!",
            reply_markup=get_main_keyboard()
        )
        return

    # Выполняем задачу
    db.complete_task(task_id)

    # Получаем опыт за выполнение
    exp_gained = LEVEL_SYSTEM_CONFIG["task_completion_exp"]
    db.add_experience(user_id, exp_gained)

    # Проверяем повышение уровня
    user_stats = db.get_user_stats(user_id)
    level_system = LevelSystem()
    new_level = level_system.get_level(user_stats.experience)

    if new_level > user_stats.level:
        db.update_level(user_id, new_level)
        level_up_text = f"\n🎉 Поздравляем! Вы достигли {new_level} уровня!"
    else:
        level_up_text = ""

    await callback.message.edit_text(
        f"✅ Задача выполнена!\n\n"
        f"📝 {task.description}\n\n"
        f"🎯 Получено опыта: +{exp_gained}\n"
        f"📊 Текущий опыт: {user_stats.experience + exp_gained}"
        f"{level_up_text}",
        reply_markup=get_main_keyboard()
    )


# Обработчик кнопки "Статистика"
@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику пользователя"""
    await callback.answer()

    user_id = callback.from_user.id
    user_stats = db.get_user_stats(user_id)

    text = f"📊 Ваша статистика:\n\n{format_detailed_stats(user_stats)}"

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())


# Обработчик кнопки "Рейтинг"
@router.callback_query(F.data == "rating")
async def show_rating(callback: CallbackQuery):
    """Показать рейтинг пользователей"""
    await callback.answer()

    text = "🏆 Выберите тип рейтинга:"
    await callback.message.edit_text(text, reply_markup=get_rating_keyboard())


# Обработчик кнопки "Топ по уровням"
@router.callback_query(F.data == "top_levels")
async def show_top_levels(callback: CallbackQuery):
    """Показать топ пользователей по уровням"""
    await callback.answer()

    top_users = db.get_top_users_by_level(10)

    if not top_users:
        text = "📊 Рейтинг пока пуст."
    else:
        text = "🏆 Топ пользователей по уровням:\n\n"
        text += format_top_users(top_users, "level")

    await callback.message.edit_text(text, reply_markup=get_rating_keyboard())


# Обработчик кнопки "Топ по опыту"
@router.callback_query(F.data == "top_exp")
async def show_top_experience(callback: CallbackQuery):
    """Показать топ пользователей по опыту"""
    await callback.answer()

    top_users = db.get_top_users_by_experience(10)

    if not top_users:
        text = "📊 Рейтинг пока пуст."
    else:
        text = "🏆 Топ пользователей по опыту:\n\n"
        text += format_top_users(top_users, "experience")

    await callback.message.edit_text(text, reply_markup=get_rating_keyboard())


# Обработчик кнопки "Звания"
@router.callback_query(F.data == "titles")
async def show_titles(callback: CallbackQuery):
    """Показать меню званий"""
    await callback.answer()

    text = "🏅 Система званий:"
    await callback.message.edit_text(text, reply_markup=get_titles_keyboard())


# Обработчик кнопки "Мое звание"
@router.callback_query(F.data == "my_title")
async def show_my_title(callback: CallbackQuery):
    """Показать звание пользователя"""
    await callback.answer()

    user_id = callback.from_user.id
    user_stats = db.get_user_stats(user_id)

    rank_system = RankSystem()
    current_rank = rank_system.get_rank(user_stats.level)
    next_rank = rank_system.get_next_rank(user_stats.level)

    text = f"🏅 Ваше текущее звание:\n\n"
    text += f"🎖️ {current_rank['name']}\n"
    text += f"📋 {current_rank['description']}\n\n"
    text += f"📊 Уровень: {user_stats.level}\n"

    if next_rank:
        text += f"\n🎯 Следующее звание: {next_rank['name']}\n"
        text += f"📈 Требуется уровень: {next_rank['min_level']}\n"
        text += f"🔥 Осталось уровней: {next_rank['min_level'] - user_stats.level}"
    else:
        text += f"\n🏆 Вы достигли максимального звания!"

    await callback.message.edit_text(text, reply_markup=get_titles_keyboard())


# Обработчик кнопки "Все звания"
@router.callback_query(F.data == "all_titles")
async def show_all_titles(callback: CallbackQuery):
    """Показать все доступные звания"""
    await callback.answer()

    rank_system = RankSystem()
    all_ranks = rank_system.get_all_ranks()

    text = "🏅 Все звания:\n\n"
    for rank in all_ranks:
        text += f"🎖️ {rank['name']}\n"
        text += f"📋 {rank['description']}\n"
        text += f"📊 Требуется уровень: {rank['min_level']}\n\n"

    await callback.message.edit_text(text, reply_markup=get_titles_keyboard())


# Обработчик кнопки "Пользователи по званиям"
@router.callback_query(F.data == "rank_users")
async def show_rank_users_menu(callback: CallbackQuery):
    """Показать меню пользователей по званиям"""
    await callback.answer()

    text = "🏆 Выберите звание для просмотра пользователей:"
    await callback.message.edit_text(text, reply_markup=get_rank_users_keyboard())


# Обработчик кнопки "Назад в главное меню"
@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery):
    """Вернуться в главное меню"""
    await callback.answer()

    user_id = callback.from_user.id
    user_stats = db.get_user_stats(user_id)
    username = callback.from_user.username or callback.from_user.first_name

    text = f"""
🎯 Главное меню

👤 {username}
📊 Ваши показатели:
{format_user_stats(user_stats)}

Выберите действие:
    """

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())


# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку"""
    help_text = """
🆘 Справка по боту

📋 Основные команды:
/start - Запустить бота
/help - Показать эту справку
/stats - Показать статистику

🎯 Функции:
• Добавление и выполнение задач
• Система уровней и опыта
• Рейтинги пользователей
• Система званий
• Ежедневные штрафы за неактивность

📊 Система опыта:
• За выполнение задачи: +{task_exp} опыта
• Штраф за пропуск дня: -{penalty} опыта

🏆 Звания получаются автоматически при достижении определенного уровня.
    """.format(
        task_exp=LEVEL_SYSTEM_CONFIG["task_completion_exp"],
        penalty=LEVEL_SYSTEM_CONFIG["daily_penalty"]
    )

    await message.answer(help_text, reply_markup=get_main_keyboard())


# Обработчик команды /stats
@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать статистику через команду"""
    user_id = message.from_user.id
    user_stats = db.get_user_stats(user_id)

    if not user_stats:
        await message.answer("❌ Пользователь не найден. Используйте /start для регистрации.")
        return

    text = f"📊 Ваша статистика:\n\n{format_detailed_stats(user_stats)}"
    await message.answer(text, reply_markup=get_main_keyboard())


# Обработчик неизвестных callback_query
@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    """Обработчик неизвестных callback запросов"""
    await callback.answer("❌ Неизвестная команда", show_alert=True)


# Обработчик всех остальных сообщений
@router.message()
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    await message.answer(
        "❓ Неизвестная команда. Используйте /help для получения справки.",
        reply_markup=get_main_keyboard()
    )