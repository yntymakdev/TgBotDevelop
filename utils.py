from datetime import datetime, timedelta
from config import LEVEL_SYSTEM_CONFIG


def is_new_day(last_reset: datetime) -> bool:
    """Проверить, начался ли новый день"""
    return datetime.now().date() > last_reset.date()


def time_until_reset() -> str:
    """Время до сброса задач"""
    now = datetime.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    time_left = tomorrow - now

    hours = int(time_left.total_seconds() // 3600)
    minutes = int((time_left.total_seconds() % 3600) // 60)

    return f"{hours}ч {minutes}м"


def should_apply_penalty(last_reset: datetime) -> bool:
    """Проверить, нужно ли применить штраф"""
    penalty_hours = LEVEL_SYSTEM_CONFIG["PENALTY_HOURS"]
    return datetime.now() - last_reset > timedelta(hours=penalty_hours)


def format_user_stats(user_stats, rank_info=None) -> str:
    """Форматировать статистику пользователя"""
    from level_system import LevelSystem, RankSystem

    if rank_info is None:
        rank_info = RankSystem.get_rank_progress(user_stats.level)

    current_rank = rank_info["current_rank"]
    next_rank = rank_info["next_rank"]

    completed_tasks = sum(1 for task in user_stats.daily_tasks if task.completed)
    total_tasks = len(user_stats.daily_tasks)

    # Прогресс до следующего ранга
    rank_progress = ""
    if next_rank:
        rank_progress = f"\n🎯 До ранга {next_rank.color} **{next_rank.code}**: {rank_info['levels_to_next']} уровней"

    return f"""
🎮 **СИСТЕМА УРОВНЕЙ SOLO LEVELING**

👤 **Игрок**: {user_stats.username or "Неизвестный"}
🆙 **Level**: {user_stats.level}
🎖️ **Ранг**: {current_rank.color} **{current_rank.code}** - {current_rank.name}
⭐️ **XP**: {user_stats.xp}/{LevelSystem.get_xp_for_next_level(user_stats.level)}
🎯 **Общий XP**: {user_stats.total_xp}
{rank_progress}

📅 **Дата**: {datetime.now().strftime('%d.%m.%Y')}
✅ **Задачи выполнены**: {completed_tasks}/{total_tasks}
📊 **XP за день**: {sum(task.xp_reward for task in user_stats.daily_tasks if task.completed)}

⏰ **Время до сброса**: {time_until_reset()}

🏆 **Достижения**: {sum(1 for title in user_stats.titles if title.achieved)}/{len(user_stats.titles)}
"""


def format_detailed_stats(user_stats) -> str:
    """Форматировать детальную статистику"""
    from level_system import RankSystem

    rank_info = RankSystem.get_rank_progress(user_stats.level)
    current_rank = rank_info["current_rank"]

    days_active = (datetime.now() - user_stats.last_reset).days + 1
    avg_xp_per_day = user_stats.total_xp / max(days_active, 1)

    stats_text = f"""
📈 **ПОДРОБНАЯ СТАТИСТИКА**

🎮 **Прогресс в системе**:
• Уровень: {user_stats.level}
• Ранг: {current_rank.color} **{current_rank.code}** - {current_rank.name}
• Текущий XP: {user_stats.xp}
• Общий XP: {user_stats.total_xp}
• Среднее XP в день: {avg_xp_per_day:.1f}

📊 **Задачи сегодня**:
"""

    for task in user_stats.daily_tasks:
        status = "✅" if task.completed else "❌"
        time_completed = task.completion_time.strftime("%H:%M") if task.completion_time else "—"
        stats_text += f"• {status} {task.name} ({time_completed})\n"

    stats_text += f"""
🏆 **Достижения**:
• Получено титулов: {sum(1 for title in user_stats.titles if title.achieved)}
• Всего титулов: {len(user_stats.titles)}

⏰ **Время**:
• Дней в системе: {days_active}
• Время до сброса: {time_until_reset()}
"""

    return stats_text


def format_top_users(users_list, title="🏆 ТОП ИГРОКОВ") -> str:
    """Форматировать список топ пользователей"""
    from level_system import RankSystem

    if not users_list:
        return "📝 Пока нет данных для отображения."

    text = f"**{title}**\n\n"

    for i, user in enumerate(users_list, 1):
        rank = RankSystem.get_rank_by_level(user.level)
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."

        text += f"{emoji} **{user.username or 'Неизвестный'}**\n"
        text += f"   {rank.color} {rank.code} • Level {user.level} • {user.total_xp} XP\n\n"

    return text


def calculate_penalty(user_stats) -> int:
    """Рассчитать штраф за невыполненные задачи"""
    penalty_xp = 0
    for task in user_stats.daily_tasks:
        if not task.completed:
            penalty_xp += LEVEL_SYSTEM_CONFIG["PENALTY_XP_PER_TASK"]
    return penalty_xp