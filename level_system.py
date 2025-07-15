from config import LEVEL_SYSTEM_CONFIG, RANK_SYSTEM_CONFIG
from models import Rank
from typing import Dict, Optional, List

class LevelSystem:
    """Система уровней как в Solo Leveling"""

    XP_REQUIREMENTS = LEVEL_SYSTEM_CONFIG["XP_REQUIREMENTS"]

    @staticmethod
    def get_xp_for_next_level(current_level: int) -> int:
        """Получить XP необходимый для следующего уровня"""
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
        """Рассчитать уровень по общему XP"""
        level = 1
        xp_needed = 0

        for lvl in sorted(LevelSystem.XP_REQUIREMENTS.keys()):
            xp_needed += LevelSystem.XP_REQUIREMENTS[lvl]
            if total_xp >= xp_needed:
                level = lvl
            else:
                break

        # Для уровней выше 100
        if total_xp >= xp_needed:
            additional_levels = (total_xp - xp_needed) // 5000
            level = 100 + additional_levels

        return level


class RankSystem:
    """Система рангов для классификации игроков"""

    RANKS = RANK_SYSTEM_CONFIG["RANKS"]

    @staticmethod
    def get_rank_by_level(level: int) -> Rank:
        """Получить ранг по уровню"""
        for rank_code, rank_data in RankSystem.RANKS.items():
            if rank_data["min_level"] <= level <= rank_data["max_level"]:
                return Rank(
                    code=rank_code,
                    name=rank_data["name"],
                    color=rank_data["color"],
                    min_level=rank_data["min_level"],
                    max_level=rank_data["max_level"]
                )

        # Если не найден, возвращаем E ранг
        return Rank(
            code="E",
            name="Новичок",
            color="🟫",
            min_level=1,
            max_level=10
        )

    @staticmethod
    def get_rank_progress(level: int) -> dict:
        """Получить прогресс до следующего ранга"""
        current_rank = RankSystem.get_rank_by_level(level)

        # Найти следующий ранг
        next_rank = None
        rank_codes = list(RankSystem.RANKS.keys())

        try:
            current_index = rank_codes.index(current_rank.code)
            if current_index < len(rank_codes) - 1:
                next_rank_code = rank_codes[current_index + 1]
                next_rank_data = RankSystem.RANKS[next_rank_code]
                next_rank = Rank(
                    code=next_rank_code,
                    name=next_rank_data["name"],
                    color=next_rank_data["color"],
                    min_level=next_rank_data["min_level"],
                    max_level=next_rank_data["max_level"]
                )
        except (ValueError, IndexError):
            pass

        if next_rank:
            levels_to_next = next_rank.min_level - level
            progress_percentage = ((level - current_rank.min_level) /
                                   (current_rank.max_level - current_rank.min_level)) * 100
        else:
            levels_to_next = 0
            progress_percentage = 100

        return {
            "current_rank": current_rank,
            "next_rank": next_rank,
            "levels_to_next": levels_to_next,
            "progress_percentage": min(progress_percentage, 100)
        }

    @staticmethod
    def get_all_ranks() -> List[Rank]:
        """Получить все ранги"""
        ranks = []
        for rank_code, rank_data in RankSystem.RANKS.items():
            ranks.append(Rank(
                code=rank_code,
                name=rank_data["name"],
                color=rank_data["color"],
                min_level=rank_data["min_level"],
                max_level=rank_data["max_level"]
            ))
        return ranks

    @staticmethod
    def format_rank_display(rank: Rank) -> str:
        """Форматировать отображение ранга"""
        max_level_text = "∞" if rank.max_level == float('inf') else str(rank.max_level)
        return f"{rank.color} **{rank.code}** - {rank.name} ({rank.min_level}-{max_level_text})"