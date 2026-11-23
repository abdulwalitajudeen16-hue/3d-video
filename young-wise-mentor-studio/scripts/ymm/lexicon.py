"""Keyword lexicons used by the deterministic baseline analyser/planner.

The baseline is intentionally conservative: it only proposes a storytelling action when the
narration contains a trigger phrase for it. Claude (via the plan-video skill) refines the plan;
validate_plan() enforces the same "no invented visuals" rule on whatever plan results.
"""

# action key -> (trigger regex alternatives, action description, environment, expression, body, camera)
STORY_ACTIONS = {
    "waking": {
        "triggers": [r"\bwake(?:s)? up\b", r"\bwoke up\b", r"\balarm\b", r"\bin bed\b", r"\bmorning\b.*\b(?:wake|alarm|bed)\b"],
        "action": "wakes in bed, slowly sits up and rubs his eyes",
        "environment": "dim bedroom, soft early-morning window light",
        "expression": "groggy, heavy-eyed",
        "body": "pushes himself upright, shoulders slumped",
        "camera": ("medium shot, slightly high angle", "slow push-in"),
    },
    "phone": {
        "triggers": [r"\bcheck(?:s|ed|ing)? (?:his |your |my )?phone\b", r"\bpick(?:s|ed)? up (?:his |your |my )?phone\b", r"\breach(?:es|ed)? for (?:his |your |my )?phone\b", r"\bnotification"],
        "action": "picks up his phone and looks at the screen, thumb moving",
        "environment": "dim room lit by the phone's glow",
        "expression": "drawn, absorbed",
        "body": "head bowed toward the phone, shoulders curled",
        "camera": ("close-up over the shoulder", "subtle handheld drift"),
    },
    "scrolling": {
        "triggers": [r"\bscroll(?:s|ed|ing)?\b", r"\bsocial media\b", r"\binstagram\b", r"\btiktok\b", r"\bfeed\b"],
        "action": "scrolls through his phone with his thumb, face lit by the screen",
        "environment": "dim room lit by the phone's glow",
        "expression": "blank, numb",
        "body": "slouched, head forward",
        "camera": ("close-up, eye level", "slow push-in"),
    },
    "clock": {
        "triggers": [r"\bclock\b", r"\bwatch(?:es|ed)? the time\b", r"\blooks? at (?:the |his |a )?(?:time|clock|watch)\b", r"\bhours? (?:pass|slip|vanish)"],
        "action": "glances at a wall clock, then looks away tight-jawed",
        "environment": "home interior, wall clock visible",
        "expression": "uneasy, aware of time slipping",
        "body": "head turns toward the clock, shoulders tense",
        "camera": ("medium shot, eye level", "slow lateral slide"),
    },
    "desk": {
        "triggers": [r"\bsit(?:s|ting)? (?:at|down at) (?:a |his |your |the )?desk\b", r"\bat (?:a |his |your |the )?desk\b", r"\bdesk\b"],
        "action": "sits at a desk, hands resting on the surface",
        "environment": "dim home office, desk lamp, bookshelf",
        "expression": "focused but weary",
        "body": "seated upright, forearms on desk",
        "camera": ("medium shot, eye level", "slow push-in"),
    },
    "laptop": {
        "triggers": [r"\blaptop\b", r"\btyp(?:es|ing)\b", r"\bwork(?:s|ing)? on (?:a |his |your |the )?(?:laptop|computer)\b", r"\bcomputer\b", r"\bemails?\b"],
        "action": "works on a laptop, fingers on the keys, eyes on the screen",
        "environment": "dim home office, laptop glow on his face",
        "expression": "concentrated",
        "body": "leaning toward the screen, hands typing",
        "camera": ("medium close-up, three-quarter angle", "slow orbit"),
    },
    "frustrated": {
        "triggers": [r"\bfrustrat\w*", r"\bstuck\b", r"\bgive up\b", r"\bangry\b", r"\bfed up\b", r"\bhopeless\b"],
        "action": "exhales hard, runs a hand over his face and head",
        "environment": "dim home office",
        "expression": "frustrated, jaw tight",
        "body": "slumps back, shoulders drop then tense",
        "camera": ("close-up, eye level", "handheld micro-shake"),
    },
    "thinking": {
        "triggers": [r"\bthink(?:s|ing)? (?:deeply|hard|about)\b", r"\bwonder(?:s|ed|ing)?\b", r"\breflect\w*", r"\bask(?:s|ed)? (?:himself|yourself)\b", r"\bsilence\b", r"\bpause\b"],
        "action": "stills, gaze drifts to the middle distance, hand resting near his chin",
        "environment": "dim room with window light",
        "expression": "pensive, inward",
        "body": "very slight lean back, breathing visible",
        "camera": ("close-up, slightly low angle", "very slow push-in"),
    },
    "walking": {
        "triggers": [r"\bwalk(?:s|ed|ing)?\b", r"\bstroll\w*", r"\bstreet\b", r"\bpath\b", r"\bjourney\b", r"\bone step\b"],
        "action": "walks forward through the space at an unhurried pace",
        "environment": "quiet urban street at dusk",
        "expression": "resolved, forward-looking",
        "body": "steady stride, arms swinging loosely",
        "camera": ("tracking medium shot, eye level", "tracking backward ahead of him"),
    },
}

# emotion -> (regex words, expression, intensity)
EMOTIONS = {
    "frustrated": (r"\b(frustrat\w*|stuck|angry|tired of|sick of|fed up|hate|wasted)\b", "frustrated, tight jaw"),
    "sad": (r"\b(lonely|alone|sad|lost|empty|regret|miss(?:ed)?|failed|failure)\b", "downcast, softened eyes"),
    "urgent": (r"\b(now|today|stop|never|right now|before it'?s too late|wake up|must)\b", "intense, direct"),
    "hopeful": (r"\b(hope|possible|change|better|grow|begin|start|future|dream|can)\b", "warm, quietly hopeful"),
    "proud": (r"\b(proud|win|won|achiev\w*|succe\w*|built|finish\w*)\b", "composed pride, slight smile"),
    "curious": (r"\b(why|how|what if|imagine|wonder|ever noticed)\b", "curious, raised brow"),
    "calm": (r"\b(breathe|slow|patient|steady|quiet|simple)\b", "calm, relaxed"),
}

PRESENTER_CUES = r"\b(let me tell you|here'?s the truth|listen|i want you to|you need to|remember this|the lesson|here'?s what|my advice|so what do you do)\b"
STORY_CUES = r"\b(imagine|picture this|it'?s (?:6|7|8)\s?am|one morning|you wake|you open|you sit|you pick|you scroll|you check|he wakes|he opens)\b"

EMPHASIS_WORDS = {"never", "always", "must", "stop", "now", "only", "every", "nothing", "everything", "truth", "remember", "listen", "exactly", "real", "no one", "nobody"}
CONTRAST_WORDS = {"but", "however", "instead", "yet", "although", "except"}
ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "one": 1, "two": 2, "three": 3}
