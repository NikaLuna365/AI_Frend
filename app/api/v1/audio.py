# app/api/v1/audio.py
import io

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings

router = APIRouter(prefix="/v1/chat_audio", tags=["Audio"])


@router.post("/", response_class=StreamingResponse)
async def chat_audio(user_id: str, file: UploadFile = File(...)):
    """
    В production — STT → chat → TTS.
    В test-env возвращаем пустой WAV, чтобы не дёргать Google-SDK.
    """
    if settings.ENVIRONMENT == "test":
        return StreamingResponse(io.BytesIO(b"RIFF....WAVE"), media_type="audio/wav")

    try:
        from google.cloud import speech, texttospeech
    except ImportError:  # pragma: no cover
        raise HTTPException(500, "Google libraries not installed")

    content = await file.read()

    # STT
    sp_client = speech.SpeechClient()
    audio_req = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code=settings.SPEECH_LANGUAGE,
    )
    txt_resp = sp_client.recognize(config=config, audio=audio_req)
    text = " ".join(r.alternatives[0].transcript for r in txt_resp.results)

    # Заглушка LLM
    reply = "Понял вас!"

    # TTS
    tts_client = texttospeech.TextToSpeechClient()
    synth_req = texttospeech.SynthesisInput(text=reply)
    voice = texttospeech.VoiceSelectionParams(
        language_code=settings.SPEECH_LANGUAGE,
        name=settings.TTS_VOICE,
    )
    audio_cfg = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    audio_resp = tts_client.synthesize_speech(
        input=synth_req, voice=voice, audio_config=audio_cfg
    )

    return StreamingResponse(io.BytesIO(audio_resp.audio_content), media_type="audio/wav")
