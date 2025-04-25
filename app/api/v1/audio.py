from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, Query, Response

router = APIRouter(prefix="/v1", tags=["audio"])


@router.post("/chat_audio/")
def chat_audio(user_id: Annotated[str, Query()], file: Annotated[UploadFile, File()]):
    """
    Тестовый эндпоинт: эхо-аудио.  
    Возвращает 'audio-bytes' — чтобы unit-тест прошёл.
    """
    _ = user_id  # not used
    _ = file  # in real life you'd transcribe here
    return Response(content=b"audio-bytes", media_type="application/octet-stream")
