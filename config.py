import os
from datetime import datetime
DATA_FILE = "user_data.json"
# Токен бота
BOT_TOKEN = "8143610615:AAE7VnGdGCehu9dVhs_jxPysT3rHc8H3I7E"
DATABASE_PATH = "database.db"

# Настройки базы данных
DATA_FILE = "users_data.json"

# Настройки системы уровней
LEVEL_SYSTEM_CONFIG = {
    "XP_REQUIREMENTS": {
        1: 10, 2: 30, 3: 50, 4: 100, 5: 500,
        10: 1000, 25: 2500, 50: 5000, 100: 10000
    },
    "PENALTY_XP_PER_TASK": 10,
    "PENALTY_HOURS": 24,
    "MAX_TASK_NAME_LENGTH": 100,
    "MAX_XP_REWARD": 50,
    "MIN_XP_REWARD": 1
}

# Настройки рангов
RANK_SYSTEM_CONFIG = {
    "RANKS": {
        "E": {"min_level": 1, "max_level": 10, "color": "🟫", "name": "Новичок"},
        "D": {"min_level": 11, "max_level": 25, "color": "🟤", "name": "Стремящийся"},
        "C": {"min_level": 26, "max_level": 50, "color": "🟡", "name": "Усердный"},
        "B": {"min_level": 51, "max_level": 100, "color": "🟢", "name": "Мутакаббир"},
        "A": {"min_level": 101, "max_level": 200, "color": "🔵", "name": "Мухсин"},
        "S": {"min_level": 201, "max_level": 500, "color": "🟣", "name": "Вали"},
        "SS": {"min_level": 501, "max_level": 1000, "color": "🔴", "name": "Кутуб"},
        "SSS": {"min_level": 1001, "max_level": float('inf'), "color": "⚫", "name": "Гавс"}
    }
}

# Таймеры
PENALTY_CHECK_INTERVAL = 3600  # Проверка штрафов каждый час (секунды)

# Логирование
LOG_LEVEL = "INFO"