"""Config-driven adapter for any REST video API with a submit -> poll -> download shape.

Use this for providers that have no built-in adapter (an image-to-video model for storytelling shots,
HeyGen, D-ID, Hedra, Sync, etc.). YOU supply the endpoint details from that provider's own docs in
config/providers.json; nothing about any specific vendor is assumed here.

Config shape (see config/providers.example.json):
{
  "name": "my-provider",
  "lipsync": true, "image_to_video": true,
  "submit": {"method": "POST", "url": "https://api.example.com/v1/jobs",
             "headers": {"Authorization": "Bearer ${ENV:MY_KEY}"},
             "json": {"image": "${IMAGE_DATA_URI}", "audio": "${AUDIO_DATA_URI}", "prompt": "${PROMPT}"}},
  "job_id_path": "id",
  "poll": {"method": "GET", "url": "https://api.example.com/v1/jobs/${JOB_ID}", "headers": {...},
           "status_path": "status", "done_values": ["done"], "failed_values": ["failed"], "error_path": "error"},
  "result": {"video_url_path": "output.video_url"}
}
Placeholders: ${PROMPT} ${IMAGE_DATA_URI} ${AUDIO_DATA_URI} ${DURATION} ${ASPECT} ${RESOLUTION} ${JOB_ID} ${ENV:NAME}.
Image/audio may be passed as URLs instead by setting SceneJob.extra["image_url"] / ["audio_url"]
and using ${IMAGE_URL} / ${AUDIO_URL}.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

from .base import (Capabilities, Provider, ProviderError, ProviderNotConfigured, SceneJob, poll_until, to_data_uri)

_PH = re.compile(r"\$\{([A-Z_]+)(?::([A-Za-z0-9_]+))?\}")


def dig(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


class GenericHTTP(Provider):
    def __init__(self, cfg: dict, session: requests.Session | None = None, poll_interval: float = 5.0, sleep=None):
        for k in ("name", "submit", "job_id_path", "poll", "result"):
            if k not in cfg:
                raise ProviderError(f"provider config missing '{k}'")
        self.cfg = cfg
        self.session = session or requests.Session()
        self.poll_interval = poll_interval
        self._sleep = sleep
        self.capabilities = Capabilities(
            name=cfg["name"], lipsync=bool(cfg.get("lipsync")), image_to_video=bool(cfg.get("image_to_video")),
            max_audio_seconds=cfg.get("max_audio_seconds"), verified_live=bool(cfg.get("verified_live", False)),
            notes=cfg.get("notes", "User-configured; behaviour depends on the vendor's actual API."))

    def _env_refs(self) -> set[str]:
        return {m.group(2) for m in _PH.finditer(json.dumps(self.cfg)) if m.group(1) == "ENV"}

    def check_config(self) -> tuple[bool, str]:
        missing = sorted(n for n in self._env_refs() if not os.environ.get(n))
        if missing:
            return False, "set environment variable(s): " + ", ".join(missing)
        return True, "all referenced environment variables are set (live service not verified)"

    def _fill(self, node: Any, ctx: dict[str, str]) -> Any:
        if isinstance(node, str):
            def sub(m):
                key, arg = m.group(1), m.group(2)
                if key == "ENV":
                    v = os.environ.get(arg or "")
                    if v is None:
                        raise ProviderNotConfigured(f"environment variable {arg} is not set")
                    return v
                if key not in ctx:
                    raise ProviderError(f"placeholder ${{{key}}} has no value for this job")
                return ctx[key]
            return _PH.sub(sub, node)
        if isinstance(node, dict):
            return {k: self._fill(v, ctx) for k, v in node.items()}
        if isinstance(node, list):
            return [self._fill(v, ctx) for v in node]
        return node

    def generate(self, job: SceneJob) -> Path:
        c = self.capabilities
        if job.audio_path and not c.lipsync:
            raise ProviderError(f"{c.name} is not configured as lip-sync capable")
        if not job.audio_path and not c.image_to_video:
            raise ProviderError(f"{c.name} is not configured for image-to-video")
        ctx = {"PROMPT": job.prompt, "DURATION": f"{job.duration:.2f}", "ASPECT": job.aspect, "RESOLUTION": job.resolution}
        ctx["IMAGE_URL"] = job.extra.get("image_url", "")
        ctx["AUDIO_URL"] = job.extra.get("audio_url", "")
        if not ctx["IMAGE_URL"]:
            ctx["IMAGE_DATA_URI"] = to_data_uri(job.image_path)
        if job.audio_path and not ctx["AUDIO_URL"]:
            ctx["AUDIO_DATA_URI"] = to_data_uri(job.audio_path)
        sub = self.cfg["submit"]
        r = self.session.request(sub.get("method", "POST"), self._fill(sub["url"], ctx),
                                 headers=self._fill(sub.get("headers", {}), ctx),
                                 json=self._fill(sub.get("json"), ctx) if "json" in sub else None, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"submit failed: HTTP {r.status_code}: {r.text[:500]}")
        try:
            ctx["JOB_ID"] = str(dig(r.json(), self.cfg["job_id_path"]))
        except (KeyError, IndexError, ValueError, TypeError):
            raise ProviderError(f"could not find job id at '{self.cfg['job_id_path']}' in: {r.text[:300]}")
        pol = self.cfg["poll"]

        def check():
            p = self.session.request(pol.get("method", "GET"), self._fill(pol["url"], ctx),
                                     headers=self._fill(pol.get("headers", {}), ctx), timeout=60)
            if p.status_code >= 400:
                raise ProviderError(f"poll failed: HTTP {p.status_code}: {p.text[:300]}")
            js = p.json()
            st = str(dig(js, pol["status_path"]))
            if st in pol.get("failed_values", []):
                err = ""
                if pol.get("error_path"):
                    try:
                        err = str(dig(js, pol["error_path"]))
                    except (KeyError, IndexError, TypeError):
                        pass
                raise ProviderError(f"generation failed (status={st}) {err}")
            return st in pol.get("done_values", []), js

        kw = {"interval": self.poll_interval}
        if self._sleep:
            kw["sleep"] = self._sleep
        final = poll_until(check, **kw)
        try:
            url = dig(final, self.cfg["result"]["video_url_path"])
        except (KeyError, IndexError, TypeError):
            raise ProviderError(f"no video url at '{self.cfg['result']['video_url_path']}'")
        out = Path(job.out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(url, stream=True, timeout=300) as dl:
            if dl.status_code >= 400:
                raise ProviderError(f"download failed: HTTP {dl.status_code}")
            with open(out, "wb") as f:
                for chunk in dl.iter_content(1 << 20):
                    f.write(chunk)
        return out
