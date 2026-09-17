"""TTS is supplied by the browser's speechSynthesis with localService voices only.
This interface is the seam for a later Piper or other backend engine.
"""
from typing import Protocol

class SpeechSynthesizer(Protocol):
    async def synthesize(self, text: str) -> bytes: ...
