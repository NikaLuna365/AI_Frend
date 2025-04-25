# app/api/v1/audio.py

from fastapi import APIRouter, File, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse
from app.config import settings
from google.cloud import speech, texttospeech
from io import BytesIO

router = APIRouter(prefix="/v1/chat_audio", tags=["ChatAudio"])

@router.post("/", response_class=StreamingResponse)
async def chat_audio(user_id: str, file: UploadFile = File(...)):
    """
    Принимает WAV, распознаёт текст, прогоняет через LLM, синтезирует ответ в WAV.
    """
    # 1) Speech-to-Text
    data = await file.read()
    try:
        speech_client = speech.SpeechClient.from_service_account_file(
            settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        )
        audio_req = speech.RecognitionAudio(content=data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=settings.SPEECH_LANGUAGE,
        )
        stt_resp = speech_client.recognize(config=config, audio=audio_req)
        text = " ".join([r.alternatives[0].transcript for r in stt_resp.results])
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"STT error: {e}")

    # 2) LLM
    from app.core.llm.client import LLMClient, Message
    from app.core.users.service import UsersService
    users_svc = UsersService()
    users_svc.save_message(user_id, Message(role="user", content=text))
    llm = LLMClient()
    reply = llm.generate(text, context=users_svc.get_context(user_id))
    users_svc.save_message(user_id, Message(role="assistant", content=reply))

    # 3) Text-to-Speech
    try:
        tts_client = texttospeech.TextToSpeechClient.from_service_account_file(
            settings.GOOGLE_CALENDAR_CREDENTIALS_JSON
        )
        tts_input = texttospeech.SynthesisInput(text=reply)
        voice = texttospeech.VoiceSelectionParams(name=settings.TTS_VOICE)
        audio_cfg = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16)
        tts_resp = tts_client.synthesize_speech(input=tts_input, voice=voice, audio_config=audio_cfg)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"TTS error: {e}")

    return StreamingResponse(BytesIO(tts_resp.audio_content), media_type="audio/wav")
