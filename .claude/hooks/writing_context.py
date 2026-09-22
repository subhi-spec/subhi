#!/usr/bin/env python3
"""Inject the human-facing writing rules when a prompt is actually about writing.

UserPromptSubmit hook. Anything printed on stdout with exit 0 is added to the
context for that turn. It stays quiet on coding prompts so it costs nothing on
the turns where it would only be noise.
"""

from __future__ import annotations

import json
import re
import sys

TRIGGERS = re.compile(
    r"\b(?:write|writing|rewrite|draft|drafting|copy|caption|newsletter|email|"
    r"blog|post|article|landing\s*page|headline|hook|script|essay|announcement|"
    r"changelog\s+entry|release\s+notes|bio|about\s+page|sales\s+page|"
    r"humanize|humanise|edit\s+this|tighten|proofread)\b",
    re.IGNORECASE,
)

# Coding prompts that happen to contain "write" ("write a function") should not
# pull the writing rules in.
CODE_CONTEXT = re.compile(
    r"\b(?:function|class|test|tests|bug|refactor|compile|typescript|python|"
    r"migration|endpoint|query|schema|regex|stack\s*trace|lint)\b",
    re.IGNORECASE,
)

REMINDER = """\
<human-facing-writing>
This prompt looks like it is asking for prose a person will read. Before drafting:

1. Decide the shape first — what the reader gets in the opening line, what order
   the middle goes in, and where it stops. Do not default to intro / three points
   / conclusion.
2. Ban list, non-negotiable: delve, tapestry, testament, pivotal, seamless,
   transformative, landscape, realm, journey, unlock, harness, elevate, empower,
   game-changer, leverage, utilize, robust, comprehensive, meticulous.
3. No "it's not just X, it's Y". No trailing "…, highlighting the importance of".
   No "In conclusion". No three-item lists on autopilot.
4. Vary sentence length on purpose. Put a five-word sentence next to a long one.
5. Every claim gets a number, a name, or a date, or it gets cut. No "experts say".
6. At most one em dash per few hundred words.

The PostToolUse hook checks the file after you write it. Getting it right in the
first draft is cheaper than being sent back.
</human-facing-writing>"""


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    prompt = payload.get("prompt") or ""
    if not isinstance(prompt, str):
        return 0
    if TRIGGERS.search(prompt) and not CODE_CONTEXT.search(prompt):
        print(REMINDER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
