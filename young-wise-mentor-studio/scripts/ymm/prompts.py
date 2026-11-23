"""Builds provider prompts from a Scene, always prefixed with the identity lock from the character profile."""
from __future__ import annotations

import json
from pathlib import Path

from .models import Scene

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = PLUGIN_ROOT / "assets" / "character-profile.json"
REFERENCE_PATH = PLUGIN_ROOT / "assets" / "mentor-reference.jpg"


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def identity_lock(profile: dict | None = None) -> str:
    p = profile or load_profile()
    return " ".join(p["identity_lock_lines"])


def build_prompt(scene: Scene, aspect: str, profile: dict | None = None) -> str:
    p = profile or load_profile()
    parts = [
        identity_lock(p),
        f"Photorealistic live-action footage, {p['style']['look']}.",
        f"Action: {scene.action}.",
        f"Facial expression: {scene.expression}.",
    ]
    if scene.hands:
        parts.append(f"Hands: {scene.hands}.")
    if scene.body:
        parts.append(f"Body: {scene.body}.")
    parts += [
        f"Environment: {scene.environment}.",
        f"Camera: {scene.camera_angle}, {scene.camera_movement}, {aspect} frame.",
        f"Emotional tone: {scene.emotion}.",
    ]
    if scene.mode == "presenter":
        parts.append("He looks directly into the camera lens while speaking.")
    parts.append("Negative: " + ", ".join(p["negative_prompt_terms"]) + ".")
    return " ".join(parts)
