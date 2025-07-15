import json
import os
import logging
from datetime import datetime
from typing import Dict
from dataclasses import asdict

from config import DATA_FILE
from models import UserStats, Task, Title
from level_system import RankSystem

logger = logging.getLogger(__name__)


class UserDatabase:
    """Класс для работы с базой данных пользователей"""

    def __init__(self):
        self.users: Dict[int, UserStats] = {}
        self.data_file = DATA_FILE
        self.load_data()

    def load_data(self):
        """Загрузить данные из JSON файла"""
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

                        # Создание пользователя
                        user_stats = UserStats(**user_data)

                        # Обновление ранга если его нет
                        if not hasattr(user_stats, 'rank') or not user_stats.rank:
                            user_stats.rank = RankSystem.get_rank_by_level(user_stats.level).code

                        self.users[int(user_id)] = user_stats

        except Exception as e:
            logger.error(f"Error loading data: {e}")

    def save_data(self):
        """Сохранить данные в JSON файл"""
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
        """Получить или создать пользователя"""
        if user_id not in self.users:
            user_stats = UserStats(user_id=user_id, username=username)
            # Устанавливаем начальный ранг
            user_stats.rank = RankSystem.get_rank_by_level(user_stats.level).code
            self.users[user_id] = user_stats
            self.save_data()
        return self.users[user_id]

    def update_user(self, user_stats: UserStats):
        """Обновить данные пользователя"""
        # Обновляем ранг при обновлении пользователя
        user_stats.rank = RankSystem.get_rank_by_level(user_stats.level).code
        self.users[user_stats.user_id] = user_stats
        self.save_data()

    def get_top_users(self, limit: int = 10) -> list:
        """Получить топ пользователей по уровню"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda x: (x.level, x.total_xp),
            reverse=True
        )
        return sorted_users[:limit]

    def get_users_by_rank(self, rank_code: str) -> list:
        """Получить пользователей определенного ранга"""
        return [user for user in self.users.values() if user.rank == rank_code]

    def get_user_rank_position(self, user_id: int) -> int:
        """Получить позицию пользователя в рейтинге"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda x: (x.level, x.total_xp),
            reverse=True
        )

        for i, user in enumerate(sorted_users):
            if user.user_id == user_id:
                return i + 1
        return len(sorted_users)

    # Методы для совместимости с handlers.py
    def register_user(self, user_id: int, username: str):
        """Регистрация пользователя"""
        self.get_user(user_id, username)

    def get_user_stats(self, user_id: int) -> UserStats:
        """Получить статистику пользователя"""
        return self.users.get(user_id)

    def add_task(self, task: Task) -> int:
        """Добавить задачу пользователю"""
        user = self.get_user(task.user_id)
        # Создаем простую задачу для daily_tasks
        task_dict = {
            'id': len(user.daily_tasks) + 1,
            'description': task.description,
            'completed': False,
            'completion_time': None
        }
        user.daily_tasks.append(Task(**task_dict))
        self.update_user(user)
        return task_dict['id']

    def get_user_tasks(self, user_id: int) -> list:
        """Получить все задачи пользователя"""
        user = self.get_user(user_id)
        return user.daily_tasks

    def get_user_active_tasks(self, user_id: int) -> list:
        """Получить активные задачи пользователя"""
        user = self.get_user(user_id)
        return [task for task in user.daily_tasks if not task.completed]

    def get_task(self, task_id: int):
        """Получить задачу по ID (упрощенная версия)"""
        for user in self.users.values():
            for task in user.daily_tasks:
                if task.id == task_id:
                    return task
        return None

    def complete_task(self, task_id: int):
        """Отметить задачу как выполненную"""
        for user in self.users.values():
            for task in user.daily_tasks:
                if task.id == task_id:
                    task.completed = True
                    task.completion_time = datetime.now()
                    self.update_user(user)
                    return True
        return False

    def add_experience(self, user_id: int, exp: int):
        """Добавить опыт пользователю"""
        user = self.get_user(user_id)
        user.total_xp += exp
        # Пересчитаем уровень
        user.level = self.calculate_level(user.total_xp)
        self.update_user(user)

    def calculate_level(self, total_xp: int) -> int:
        """Рассчитать уровень по опыту"""
        # Простая формула: каждые 100 очков = 1 уровень
        return total_xp // 100 + 1

    def update_level(self, user_id: int, new_level: int):
        """Обновить уровень пользователя"""
        user = self.get_user(user_id)
        user.level = new_level
        self.update_user(user)

    def apply_penalty(self, user_id: int, penalty: int):
        """Применить штраф к пользователю"""
        user = self.get_user(user_id)
        user.total_xp = max(0, user.total_xp - penalty)
        user.level = self.calculate_level(user.total_xp)
        self.update_user(user)

    def update_last_login(self, user_id: int):
        """Обновить время последнего входа"""
        user = self.get_user(user_id)
        user.last_reset = datetime.now()
        self.update_user(user)

    def get_top_users_by_level(self, limit: int = 10) -> list:
        """Получить топ пользователей по уровню"""
        return self.get_top_users(limit)

    def get_top_users_by_experience(self, limit: int = 10) -> list:
        """Получить топ пользователей по опыту"""
        sorted_users = sorted(
            self.users.values(),
            key=lambda x: x.total_xp,
            reverse=True
        )
        return sorted_users[:limit]

    def close(self):
        """Закрыть соединение с базой данных"""
        self.save_data()