"""Provider interface. Every video/lip-sync backend implements `Provider.generate`.

Capabilities are declared honestly: `verified_live` stays False until someone has run the adapter
against the real service with real credentials and recorded it in docs/PROVIDERS.md.
"""
from __future__ import annotations

import base64
import mimetypes
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


class ProviderError(RuntimeError):
    pass


class ProviderNotConfigured(ProviderError):
    """Credentials/config missing. The message says exactly what to set."""


class ManualStepRequired(ProviderError):
    """The provider is a human-in-the-loop hand-off; a job package was written for the user."""


@dataclass
class SceneJob:
    scene_id: int
    mode: str                      # presenter | storytelling
    image_path: str                # authoritative reference (or identity-preserving keyframe)
    prompt: str
    aspect: str
    duration: float
    out_path: str
    audio_path: Optional[str] = None   # voiceover clip for lip-sync scenes
    resolution: str = "720p"
    extra: dict = field(default_factory=dict)


@dataclass
class Capabilities:
    name: str
    lipsync: bool                  # audio-driven talking head with speech-matched mouth
    image_to_video: bool           # prompt-driven motion from a still, no audio
    max_audio_seconds: Optional[dict] = None   # e.g. {"720p": 60, "1080p": 30}
    verified_live: bool = False
    notes: str = ""


class Provider:
    capabilities: Capabilities

    def check_config(self) -> tuple[bool, str]:
        raise NotImplementedError

    def generate(self, job: SceneJob) -> Path:
        raise NotImplementedError

    def max_seconds(self, resolution: str) -> Optional[float]:
        m = self.capabilities.max_audio_seconds
        return float(m[resolution]) if m and resolution in m else None


def to_data_uri(path: str | Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if str(path).lower().endswith(".wav"):
        mime = "audio/wav"
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def poll_until(fn: Callable[[], tuple[bool, object]], interval: float = 5.0, timeout: float = 1800.0,
               sleep: Callable[[float], None] = time.sleep) -> object:
    """fn returns (done, value). Raises ProviderError on timeout."""
    waited = 0.0
    while True:
        done, val = fn()
        if done:
            return val
        if waited >= timeout:
            raise ProviderError(f"timed out after {timeout:.0f}s waiting for provider")
        sleep(interval)
        waited += interval
