---
name: script-analysis
description: Analyses a self-improvement video script into beats with emotion, intent and literal on-screen action triggers. Use when the user shares a script, asks what visuals fit it, or before scene planning.
---

# Script analysis

Goal: turn prose into beats the planner can place on a timeline, without inventing visuals.

## Method

1. Split into sentences/beats (`scripts/ymm/script_analysis.py`, or by hand for unusual formats). Keep the user's wording exactly; never rewrite narration.
2. For each beat note:
   - **Emotion** (frustrated, sad, urgent, hopeful, proud, curious, calm, neutral) and a matching facial expression.
   - **Intent:** direct advice to camera, rhetorical question, list item, contrast ("but"), call to action, story setup.
   - **Literal action trigger:** the exact words that describe something he could physically do (wake up, check phone, scroll, look at clock, sit at desk, work on laptop, frustration, deep thought, walk). Quote the words.
3. Decide mode per beat:
   - Storytelling only when the narration contains an action trigger or an explicit scene setup ("imagine you wake up...").
   - Everything else is presenter. Abstract advice ("discipline is a habit") stays presenter even if it feels like it needs b-roll.
4. Flag problems to the user: very long unbroken passages (hard on lip-sync providers with length limits), ambiguous pronouns, content that needs visuals the character cannot plausibly act (crowds, other people), and any claims in the script that look factually shaky for a self-improvement channel.

## Output

A short table: beat #, text, emotion, mode, action trigger (quoted). Then proceed to `scene-planning`.

## Do not

Invent actions with no trigger in the text. Add narration. Change tone to be more dramatic than the script.
