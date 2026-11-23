---
name: produce-video
description: Slash action to produce a mentor video end to end from a script and voiceover. Use when the user types /produce-video or says "produce this video", "make the video now". Arguments - script, voiceover path, platform (youtube, youtube-shorts, instagram-reels, tiktok), optional provider and subtitles flag.
---

# /produce-video

Follow the `mentor-studio-production` skill start to finish with the arguments given. Minimum needed: script and voiceover file. If either is missing, ask for it in one short message.

1. Run `doctor`; if no real provider is ready, say what is missing, still produce the plan and subtitles, and stop before generation.
2. timing -> plan -> validate -> show scene table -> generate -> assemble -> QC.
3. Deliver: final video (only if QC verdict is not FAILED, otherwise deliver it clearly labelled as a draft with the failures listed), `.srt`, `plan.json`, `qc_report.md`, `review_sheet.jpg`.
4. Finish with the QC verdict and the human-review items still open.
