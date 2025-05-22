# /app/app/workers/tasks.py (Адаптированная задача ачивок)

# ... (импорты: asyncio, logging, sa, Celery, Ignore, get_task_logger) ...
# ... (импорты: settings) ...
# --- ИСПРАВЛЕНИЕ: Убираем AchievementRule ---
from app.core.achievements.models import Achievement # Только Achievement
# ------------------------------------------
from app.core.llm.client import LLMClient
from app.db.base import async_session_context, AsyncSession
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from typing import Optional, List, Sequence, Any
from sqlalchemy.sql import func

log = get_task_logger(__name__)
celery_app = Celery(...) # Полное определение

async def _run_generate_achievement_logic(
    task_instance, user_id: str, achievement_code: str, theme: str | None
    ) -> str:
    task_id = task_instance.request.id
    log.info(f">>> [_run_achv_logic START] Task ID: {task_id} for user '{user_id}', code '{achievement_code}', theme: '{theme}'")
    achievement_status = "FAILED_PREPARATION"
    try:
        llm = LLMClient()
        # ... (инициализация gcs_client) ...

        async with async_session_context() as session:
            # --- УБИРАЕМ ПОИСК AchievementRule ---
            # stmt_rule = sa.select(AchievementRule).where(AchievementRule.code == achievement_code)
            # rule = (await session.execute(stmt_rule)).scalar_one_or_none()
            # if not rule:
            #      log.error(f"Rule '{achievement_code}' not found. Ignoring.") # Это не должно случиться, если код зашит
            #      raise Ignore()
            # ------------------------------------

            stmt_ach = sa.select(Achievement).where(Achievement.user_id == user_id, Achievement.code == achievement_code)
            achievement = (await session.execute(stmt_ach)).scalar_one_or_none()
            if not achievement:
                 log.error(f"Achievement record '{achievement_code}' for user '{user_id}' not found. Ignoring.")
                 raise Ignore()
            if achievement.status == "COMPLETED": # Проверяем статус
                 log.warning(f"Achievement '{achievement_code}' for user '{user_id}' already COMPLETED. Skipping.")
                 return f"ALREADY_COMPLETED:{achievement.id}"

            achievement_status = "PROCESSING"
            actual_theme = theme or "a significant accomplishment" # Дефолтная тема, если None

            # Генерация Названия
            log.info(f"[_run_achv_logic {task_id}] Generating title using theme: '{actual_theme}'")
            name_style_id = "default_game_style"
            name_tone_hint = "Exciting, Short, Memorable"
            name_style_examples = "1. First Blood!\n2. Level Up!\n3. Treasure Hunter"
            generated_names = await llm.generate_achievement_name(
                context=actual_theme, style_id=name_style_id, tone_hint=name_tone_hint, style_examples=name_style_examples
            )
            achievement_title = generated_names[0] if generated_names else f"Achievement: {achievement_code.replace('_', ' ').title()}"
            log.info(f"[_run_achv_logic {task_id}] Title generated: '{achievement_title}'")

            # Генерация Иконки
            log.info(f"[_run_achv_logic {task_id}] Generating icon using theme: '{actual_theme}'")
            # ... (параметры стиля для иконки) ...
            icon_png_bytes = await llm.generate_achievement_icon(
                context=actual_theme, style_id="flat_badge_icon", ... # Передаем параметры
            )
            # ... (логика загрузки в GCS) ...
            badge_png_url = "http://example.com/temp_badge.png" # Заглушка, если GCS или Imagen не сработали

            # Обновление БД
            achievement.title = achievement_title
            achievement.badge_png_url = badge_png_url
            achievement.status = "COMPLETED" # Устанавливаем статус
            achievement.updated_at = func.now()
            session.add(achievement)
            await session.commit()
            log.info(f"[_run_achv_logic {task_id}] Achievement '{achievement_code}' for user '{user_id}' set to COMPLETED.")
            achievement_status = "COMPLETED"
    # ... (обработка Ignore, Exception, finally) ...
    except Ignore: achievement_status = "IGNORED"; log.warning(...)
    except Exception as exc: achievement_status = "ERROR_IN_LOGIC"; log.exception(...); raise
    finally: log.debug(...)
    return f"{achievement_status}:{achievement_code}:{user_id}"

# Основная задача (без изменений)
@celery_app.task(...)
async def generate_achievement_task(...):
    return await _run_generate_achievement_logic(...)

__all__ = ["celery_app", "generate_achievement_task"]
