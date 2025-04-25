# app/workers/__init__.py
"""
Пакет для фоновых задач Celery.
Ничего импортировать автоматически не нужно —
Celery сам загрузит app.workers.tasks по флагу «-A».
"""
__all__: list[str] = ["tasks"]
