"""fal.ai adapter for ByteDance OmniHuman v1.5 (image + audio -> talking/gesturing human video).

What the public docs say (checked 2026-11-23 on fal.ai):
  * Queue API: POST https://queue.fal.run/{endpoint} with header `Authorization: Key $FAL_KEY`;
    response carries request_id, status_url, response_url. Poll status_url until COMPLETED, then GET response_url.
  * Endpoint `fal-ai/bytedance/omnihuman/v1.5` inputs: image_url (req), audio_url (req, <30s at 1080p, <60s at 720p),
    prompt, mask_url, resolution (720p|1080p), turbo_mode. Output: {video: {url}, duration}.

NOT verified: running this adapter against the live service. File inputs are sent as base64 data URIs;
fal's docs page I read did not describe file inputs, so if the service rejects data URIs, upload the
files elsewhere and pass URLs via `SceneJob.extra["image_url"]` / `["audio_url"]`.
Only the presenter (lip-sync) path is supported. It cannot make acted storytelling shots.
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

from .base import (Capabilities, Provider, ProviderError, ProviderNotConfigured, SceneJob, poll_until, to_data_uri)

DEFAULT_ENDPOINT = "fal-ai/bytedance/omnihuman/v1.5"


class FalOmniHuman(Provider):
    capabilities = Capabilities(
        name="fal-omnihuman", lipsync=True, image_to_video=False,
        max_audio_seconds={"720p": 60, "1080p": 30}, verified_live=False,
        notes="Presenter shots only. Schema taken from fal docs; adapter logic tested against a local fake of the queue protocol, not the live service.",
    )

    def __init__(self, endpoint: str | None = None, queue_base: str | None = None,
                 session: requests.Session | None = None, poll_interval: float = 5.0, sleep=None):
        self.endpoint = endpoint or os.environ.get("FAL_OMNIHUMAN_ENDPOINT", DEFAULT_ENDPOINT)
        self.queue_base = (queue_base or os.environ.get("FAL_QUEUE_BASE", "https://queue.fal.run")).rstrip("/")
        self.session = session or requests.Session()
        self.poll_interval = poll_interval
        self._sleep = sleep

    def _key(self) -> str:
        k = os.environ.get("FAL_KEY")
        if not k:
            raise ProviderNotConfigured(
                "FAL_KEY is not set. Create an API key at https://fal.ai/dashboard/keys and export FAL_KEY=<key>.")
        return k

    def check_config(self) -> tuple[bool, str]:
        try:
            self._key()
            return True, f"FAL_KEY present; endpoint {self.endpoint} (live service not verified)"
        except ProviderNotConfigured as e:
            return False, str(e)

    def generate(self, job: SceneJob) -> Path:
        if job.mode != "presenter" or not job.audio_path:
            raise ProviderError("fal-omnihuman only supports audio-driven presenter scenes")
        limit = self.max_seconds(job.resolution)
        if limit and job.duration > limit:
            raise ProviderError(f"scene {job.scene_id} is {job.duration:.1f}s; {job.resolution} limit is {limit:.0f}s. Split the scene.")
        headers = {"Authorization": f"Key {self._key()}", "Content-Type": "application/json"}
        body = {
            "image_url": job.extra.get("image_url") or to_data_uri(job.image_path),
            "audio_url": job.extra.get("audio_url") or to_data_uri(job.audio_path),
            "resolution": job.resolution,
        }
        if job.prompt:
            body["prompt"] = job.prompt
        if job.extra.get("turbo_mode") is not None:
            body["turbo_mode"] = bool(job.extra["turbo_mode"])
        r = self.session.post(f"{self.queue_base}/{self.endpoint}", json=body, headers=headers, timeout=120)
        if r.status_code >= 400:
            raise ProviderError(f"submit failed: HTTP {r.status_code}: {r.text[:500]}")
        sub = r.json()
        status_url, response_url = sub.get("status_url"), sub.get("response_url")
        if not status_url or not response_url:
            raise ProviderError(f"unexpected submit response (no status_url/response_url): {str(sub)[:300]}")

        def check():
            s = self.session.get(status_url, headers=headers, timeout=60)
            if s.status_code >= 400:
                raise ProviderError(f"status failed: HTTP {s.status_code}: {s.text[:300]}")
            js = s.json()
            st = js.get("status")
            if st == "COMPLETED":
                if js.get("error"):
                    raise ProviderError(f"generation failed: {js.get('error')} ({js.get('error_type')})")
                return True, js
            return False, js

        kw = {"interval": self.poll_interval}
        if self._sleep:
            kw["sleep"] = self._sleep
        poll_until(check, **kw)
        res = self.session.get(response_url, headers=headers, timeout=60)
        if res.status_code >= 400:
            raise ProviderError(f"result fetch failed: HTTP {res.status_code}: {res.text[:300]}")
        video = (res.json().get("video") or {}).get("url")
        if not video:
            raise ProviderError(f"result has no video.url: {res.text[:300]}")
        out = Path(job.out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with self.session.get(video, stream=True, timeout=300) as dl:
            if dl.status_code >= 400:
                raise ProviderError(f"video download failed: HTTP {dl.status_code}")
            with open(out, "wb") as f:
                for chunk in dl.iter_content(1 << 20):
                    f.write(chunk)
        return out
