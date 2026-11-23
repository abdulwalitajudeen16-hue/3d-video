---
name: studio-setup
description: Slash action to check the environment and walk through provider credentials and optional dependencies. Use when the user types /studio-setup or asks what they need to install or configure, which API keys are required, or why generation does not work.
---

# /studio-setup

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ymm_cli.py doctor` and summarise it in plain language.
2. Explain the gaps using `docs/PROVIDERS.md`: a lip-sync provider account and API key (for the built-in adapter: `FAL_KEY` from fal.ai), optional `faster-whisper` for real word timestamps, optional `face_recognition` for automated identity scoring.
3. Never ask the user to paste secrets into chat. Tell them to set environment variables locally (`export FAL_KEY=...`).
4. Point out that an acceptable first test is `--provider mock` (pipeline only, not a real video) and that real output needs a real provider.
5. Remind about likeness rights and platform AI-disclosure rules.
