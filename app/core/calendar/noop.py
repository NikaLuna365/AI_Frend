# app/core/calendar/noop.py
"""
No-op провайдер календаря: ничего не делает. Используется в тестах.
"""

from typing import Any, List


class NoOpProvider:
    def add_event(
        self,
        user_id: str,
        title: str,
        start_dt: Any,
        end_dt: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def list_events(
        self,
        user_id: str,
        from_dt: Any,
        to_dt: Any,
    ) -> List[Any]:
        return []
