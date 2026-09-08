"""Live radio stations and transcript teleprompter support."""

from __future__ import annotations

from app.schemas.assist import ConnectorHighlight, RadioStation, Transcript
from app.services.connectors import find_connectors
from app.services.deepgram import DeepgramProvider

RADIO_STATIONS: tuple[RadioStation, ...] = (
    RadioStation(
        id="npr",
        name="NPR News",
        stream_url="https://npr-ice.streamguys1.com/live.mp3",
        format="mp3",
    ),
    RadioStation(
        id="bloomberg",
        name="Bloomberg Radio",
        stream_url="https://playerservices.streamtheworld.com/api/livestream-redirect/WBBRAMAAC.aac",
        format="aac",
    ),
    RadioStation(
        id="cspan",
        name="C-SPAN Radio",
        stream_url="https://playerservices.streamtheworld.com/api/livestream-redirect/CSPANRADIO.mp3",
        format="mp3",
    ),
)


class RadioService:
    def __init__(self, deepgram: DeepgramProvider) -> None:
        self._deepgram = deepgram

    def stations(self) -> list[RadioStation]:
        return list(RADIO_STATIONS)

    async def transcribe(self, audio_url: str) -> Transcript:
        result = await self._deepgram.transcribe_url(audio_url)
        highlights = [
            ConnectorHighlight(connector=match.connector, index=match.index)
            for match in find_connectors(result.text)
        ]
        return Transcript(text=result.text, highlights=highlights)
