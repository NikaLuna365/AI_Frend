# app/api/v1/audio.py

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse
from io import BytesIO

from app.config import settings
from google.cloud import speech, texttospeech

from app.core.users.service import UsersService
from app.core.llm.client import LLMClient, Message

router = APIRouter(prefix="/v1/chat_audio", tags=["ChatAudio"])


@router.post("/", response_class=StreamingResponse)
async def chat_audio(user_id: str, file: UploadFile = File(...)):
    """
    Принимает WAV (LINEAR16), распознаёт текст через Google STT,
    передаёт его в LLM, сохраняет сообщения, синтезирует ответ через Google TTS
    и отдает обратно WAV-поток.
    """
    # 1) Прочитать байты
    data = await file.read()

    # 2) Speech-to-Text
    try:
        stt_client = speech.SpeechClient.from_service_account_file(
            settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        )
        audio_req = speech.RecognitionAudio(content=data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=settings.SPEECH_LANGUAGE,
        )
        stt_resp = stt_client.recognize(config=config, audio=audio_req)
        text = " ".join(r.alternatives[0].transcript for r in stt_resp.results)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"STT error: {e}"
        )

    # 3) LLM → чат
    users_svc = UsersService()
    users_svc.save_message(user_id, Message(role="user", content=text))

    llm = LLMClient()
    reply = llm.generate(text, context=users_svc.get_context(user_id))

    users_svc.save_message(user_id, Message(role="assistant", content=reply))

    # 4) Text-to-Speech
    try:
        tts_client = texttospeech.TextToSpeechClient.from_service_account_file(
            settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        )
        input_text = texttospeech.SynthesisInput(text=reply)
        voice_params = texttospeech.VoiceSelectionParams(name=settings.TTS_VOICE)
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )
        tts_resp = tts_client.synthesize_speech(
            input=input_text, voice=voice_params, audio_config=audio_config
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS error: {e}"
        )

    return StreamingResponse(
        BytesIO(tts_resp.audio_content),
        media_type="audio/wav"
    )
