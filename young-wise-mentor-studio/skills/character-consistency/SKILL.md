---
name: character-consistency
description: Rules and checks that keep the Young Wise Mentor's identity locked to the reference photograph. Use whenever generating, prompting for, reviewing or approving any image or video of the mentor, or when a user asks to change his look, make him a cartoon/illustration, restyle him, or swap him for another person.
---

# Character consistency

## Source of truth

- Authoritative reference: `${CLAUDE_PLUGIN_ROOT}/assets/mentor-reference.jpg` (original, photorealistic, never edited, never overwritten).
- Prompt anchors and negative terms: `${CLAUDE_PLUGIN_ROOT}/assets/character-profile.json`. If the JSON and the photo disagree, the photo wins. Read the photo itself when judging, not only the JSON.

## Hard rules

Never: cartoonise or illustrate him (2D or 3D); change his face, hairstyle, skin tone or clothing; apply an appearance-altering filter; make a different-looking version; replace him with someone else. The black pullover hoodie stays on in every scene (`wardrobe_lock`), including bedroom and street scenes.

If the user asks for any of the above, explain that the plugin's character rules forbid it and offer a compliant alternative (different environment, lighting, camera, action). Do not bypass the rule.

## How identity is preserved in practice

1. Always pass the reference image itself to the provider. A text description alone does not preserve identity.
2. Prefix every prompt with the identity lock from the profile (`prompts.build_prompt` does this).
3. 9:16: the original photo is sent unchanged. 16:9: an unedited face-centred crop is used, or an approved wide reference at `assets/derived/mentor-reference-16x9.jpg`. A derived reference must be human-approved against the original before use. Never replace the original.
4. Storytelling shots: if the provider supports start-frame input, use identity-preserving start frames; otherwise accept that identity drift risk is higher and review those scenes first.
5. Reject and regenerate any clip showing: different face shape, eye/brow change, hair change, skin tone shift, plastic/CGI skin, cartoon look, changed or missing hoodie, extra or warped fingers.

## Checking

Compare `qc/review_sheet.jpg` (reference tile first) to each scene tile. Automated face similarity runs only if `face_recognition` is installed; otherwise mark identity NEEDS_REVIEW and ask the user to confirm. Never write "identity verified" without one of those two.
