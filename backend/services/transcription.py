"""Local speech-to-text for voice input, via faster-whisper. Runs fully on-device — no audio
ever leaves the machine, consistent with the local/free-tools approach used for the LLM and
embeddings elsewhere in this project."""

import io
from functools import lru_cache

from faster_whisper import WhisperModel

from settings import get_settings


@lru_cache
def get_whisper_model() -> WhisperModel:
    settings = get_settings()
    return WhisperModel(settings.whisper_model_size, device="cpu", compute_type="int8")


def transcribe_audio(audio_bytes: bytes) -> str:
    model = get_whisper_model()
    segments, _info = model.transcribe(io.BytesIO(audio_bytes), beam_size=1)
    return " ".join(segment.text.strip() for segment in segments).strip()
