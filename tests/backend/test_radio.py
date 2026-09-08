"""Unit tests for the radio service."""

from app.services.deepgram import DeepgramTranscript, DeepgramWord
from app.services.radio import RADIO_STATIONS, RadioService
from tests.backend.helpers import FakeDeepgram


def test_stations_are_non_empty() -> None:
    assert len(RADIO_STATIONS) >= 3
    service = RadioService(FakeDeepgram())
    assert service.stations() == list(RADIO_STATIONS)


async def test_transcribe_combines_transcript_and_highlights() -> None:
    deepgram = FakeDeepgram(
        transcript=DeepgramTranscript(
            text="However, this is important. Furthermore, we must act.",
            words=[DeepgramWord(word="However", start=0.0, end=0.5)],
        )
    )
    service = RadioService(deepgram)

    result = await service.transcribe("https://e.com/a.mp3")

    assert result.text.startswith("However")
    connectors = [h.connector for h in result.highlights]
    assert "however" in connectors
    assert "furthermore" in connectors
