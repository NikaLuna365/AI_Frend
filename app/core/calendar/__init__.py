# app/core/calendar/__init__.py
"""
Calendar package.

Задача пакета ― предоставить абстрактный интерфейс CalendarProvider и конкретные
реализации (Google, Outlook, iCal…), а также фабричную функцию
`get_calendar_provider`, чтобы верхние слои приложения могли получить
нужный провайдер, не зная деталей импорта.

Структура пакета:
    base.py         ― интерфейс CalendarProvider и фабрика get_calendar_provider
    google.py       ― реализация для Google Calendar API
    outlook.py      ― (плейсхолдер для будущей реализации)
    models.py       ― Pydantic-схемы событий
    __init__.py     ― экспорт публичных объектов пакета

Экспортируем здесь только то, что действительно нужно снаружи.
"""

from __future__ import annotations

# Экспортируем фабрику, чтобы можно было писать
# `from app.core.calendar import get_calendar_provider`
from .base import get_calendar_provider  # noqa: F401

# При желании можно экспортировать и интерфейс, и схемы
# from .base import CalendarProvider           # noqa: F401
# from .models import EventOut, EventIn        # noqa: F401

__all__: list[str] = ["get_calendar_provider"]
