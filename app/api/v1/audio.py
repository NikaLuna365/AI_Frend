from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from google.cloud import speech_v1 as speech, texttospeech_v1 as tts
import io
from app.core.llm.client import LLMClient, Message
from app.core.users.service import UsersService

router = APIRouter()
svc = UsersService()
llm = LLMClient()

@router.post("/", response_class=StreamingResponse)
async def chat_audio(user_id: str, file: UploadFile = File(...)):
    # STT
    content = await file.read()
    speech_client = speech.SpeechClient()
    audio_req = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code=settings.SPEECH_LANGUAGE
    )
    res = speech_client.recognize(config=config, audio=audio_req)
    if not res.results:
        raise HTTPException(400, "Could not transcribe audio")
    transcript = " ".join(r.alternatives[0].transcript for r in res.results)

    # Save user message
    svc.save_message(user_id, Message(role='user', content=transcript))

    # Generate reply
    context = svc.get_recent_messages(user_id)
    reply = llm.generate(transcript, context)
    svc.save_message(user_id, Message(role='assistant', content=reply))

    # TTS
    tts_client = tts.TextToSpeechClient()
    synthesis_input = tts.SynthesisInput(text=reply)
    voice_params = tts.VoiceSelectionParams(language_code=settings.SPEECH_LANGUAGE,
                                            name=settings.TTS_VOICE)
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3)
    tts_resp = tts_client.synthesize_speech(input=synthesis_input,
                                             voice=voice_params,
                                             audio_config=audio_config)
    return StreamingResponse(io.BytesIO(tts_resp.audio_content), media_type="audio/mpeg")
