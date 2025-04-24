# app/core/achievements/__init__.py

"""
Achievements package.

Экспортируем основные элементы, чтобы внешние модули могли писать
`from app.core.achievements import AchievementsService`
или использовать полный путь `app.core.achievements.service`.
"""

from .service import AchievementsService  # noqa: F401

__all__: list[str] = ["AchievementsService"]
