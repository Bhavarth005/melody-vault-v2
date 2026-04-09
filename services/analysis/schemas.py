from pydantic import BaseModel
from typing import Optional


class RMSFrame(BaseModel):
    t_ms: float
    rms: float


class OnsetEvent(BaseModel):
    onset_ms: float


class NoteEvent(BaseModel):
    onset_ms: float
    pitch_midi: int
    pitch_hz: float
    duration_ms: float


class ChromaFrame(BaseModel):
    t_ms: float
    energy: dict[str, float]


class StemAnalysisResult(BaseModel):
    stem: str
    duration_ms: float
    rms_timeline: list[RMSFrame]
    onsets: Optional[list[OnsetEvent]] = None
    notes: Optional[list[NoteEvent]] = None
    chroma_timeline: Optional[list[ChromaFrame]] = None
