import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class FakeSpeechClient:
    def recognize(self, config, audio):
        class Alt: transcript = 'hello'
        class Res: alternatives=[Alt()]
        return type('R', (), {'results':[Res()]})

class FakeTTSClient:
    def synthesize_speech(self, input, voice, audio_config):
        return type('X', (), {'audio_content': b'audio-bytes'})

@pytest.fixture(autouse=True)
def patch_speech(monkeypatch):
    import google.cloud.speech_v1 as speech
    import google.cloud.texttospeech_v1 as tts
    monkeypatch.setattr(speech, 'SpeechClient', lambda: FakeSpeechClient())
    monkeypatch.setattr(tts, 'TextToSpeechClient', lambda: FakeTTSClient())
    yield

def test_chat_audio_endpoint():
    # передаём пустой WAV-заглушку
    dummy = io.BytesIO(b'RIFF....WAVE')
    dummy.name = 'test.wav'
    res = client.post('/v1/chat_audio/?user_id=u1', files={'file':('test.wav', dummy, 'audio/wav')})
    assert res.status_code == 200
    assert res.content == b'audio-bytes'
