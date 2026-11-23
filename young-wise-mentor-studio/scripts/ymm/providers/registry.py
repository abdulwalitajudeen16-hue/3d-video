"""Provider lookup. Presenter and storytelling scenes may use different providers."""
from __future__ import annotations

import json
from pathlib import Path

from .base import Provider, ProviderError
from .fal_omnihuman import FalOmniHuman
from .generic_http import GenericHTTP
from .manual import Manual
from .mock import Mock

BUILTIN = {"fal-omnihuman": FalOmniHuman, "manual": Manual, "mock": Mock}


def load_provider(name: str, config_path: str | None = None) -> Provider:
    if name in BUILTIN:
        return BUILTIN[name]()
    if config_path and Path(config_path).exists():
        cfgs = json.loads(Path(config_path).read_text(encoding="utf-8")).get("providers", [])
        for c in cfgs:
            if c.get("name") == name:
                return GenericHTTP(c)
    raise ProviderError(
        f"unknown provider '{name}'. Built-in: {', '.join(BUILTIN)}. "
        f"Custom providers are defined in config/providers.json (see config/providers.example.json).")


def describe_all(config_path: str | None = None) -> list[dict]:
    rows = []
    names = list(BUILTIN)
    if config_path and Path(config_path).exists():
        names += [c["name"] for c in json.loads(Path(config_path).read_text()).get("providers", [])]
    for n in names:
        p = load_provider(n, config_path)
        ok, msg = p.check_config()
        c = p.capabilities
        rows.append({"name": n, "ready": ok, "detail": msg, "lipsync": c.lipsync, "image_to_video": c.image_to_video,
                     "verified_live": c.verified_live, "notes": c.notes})
    return rows
