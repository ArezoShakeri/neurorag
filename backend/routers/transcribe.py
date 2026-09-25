"""Thin route layer for voice input — parses the uploaded audio, delegates to
backend.services.transcription. No transcription logic lives here."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.schemas import TranscriptionResponse
from backend.services.transcription import transcribe_audio

router = APIRouter()


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscriptionResponse:
    try:
        audio_bytes = await audio.read()
        text = transcribe_audio(audio_bytes)
        return TranscriptionResponse(text=text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc
