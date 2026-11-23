---
name: check-video
description: Slash action to run quality control on an existing mentor video. Use when the user types /check-video or uploads a rendered video and asks whether it is good enough to post. Needs the video, the voiceover, the plan.json and the target platform.
---

# /check-video

Follow `video-quality-control`. If `plan.json` or `work/manifest.json` is missing, say what is missing; do not guess provider names, and note that the provider-honesty check cannot run. Present the verdict and every FAIL and NEEDS_REVIEW line, send `review_sheet.jpg`, and give one concrete fix per failure.
