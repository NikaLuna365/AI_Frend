"""
❗️ Back-compat shim для старых импортов.

Раньше get_calendar_provider находился здесь, теперь он живёт в
app.core.calendar.__init__.py.  Пока тесты и часть кода не обновили импорты,
оставляем тонкий прокси.
"""

from __future__ import annotations

from app.core.calendar import get_calendar_provider, BaseCalendarProvider  # noqa: F401

__all__: list[str] = ["get_calendar_provider", "BaseCalendarProvider"]
