# CLAUDE.md

## What this repo is

The humanizer stack: hooks plus standing instructions that keep human-facing
prose out of the register models fall into by default. Built from three sources —
Wikipedia's *Signs of AI writing*, the `blader/humanizer` skill, and StoryScope
(Russell et al., COLM 2026), which showed that AI fiction is separable from human
fiction at 93.2 macro-F1 on narrative structure alone, and stays separable at 93.9
after the prose has been professionally rewritten.

That last number is the reason this repo exists. Swapping out flagged words does
not fix a draft whose shape is wrong. Shape first, vocabulary second.

## Human-facing writing

Applies to anything a person reads as writing: marketing copy, emails,
newsletters, landing pages, posts, scripts, release notes, docs meant to persuade.
It does not apply to code, code comments, commit messages, or this file.

### Decide the shape before the first sentence

Answer these three before drafting. If you cannot, you are not ready to draft.

- What does the reader get in the opening line? Not context, not setup — the thing.
- What order does the middle go in, and why that order rather than any other?
- Where does it stop? Name the last beat now so you do not write past it.

Default AI shape is intro / three even sections / summary that restates the intro.
Break it on purpose: open mid-thought, end on the sharpest line, let one section
run three times as long as another if it deserves to.

**Vary the break across pieces.** StoryScope's deepest finding is convergence: all
five models it tested occupy one tight region of structural space while human
writers are scattered across it. Rarity is the human signal. So if every piece
opens mid-thought and ends on a hard line, that is a new cluster, not an escape
from the old one. Pick a different intervention than last time, and be able to say
why this piece got this shape.

### Sentence-level rules

**Banned outright.** delve, tapestry, testament, pivotal, seamless(ly),
transformative, landscape, realm, journey, unlock, harness, elevate, empower,
game-changer, supercharge, holistic, synergy, leverage, utilize, facilitate,
robust, comprehensive, meticulous, vibrant, bustling, boasts, nestled.

**Banned constructions.**

- `It's not just X, it's Y` and every variant. Say the one true thing.
- Trailing participles: `…, highlighting the importance of…`, `…, underscoring…`,
  `…, reflecting a broader shift…`. They restate; they never add.
- `In conclusion`, `Overall`, `In summary`, `At the end of the day`.
- `In today's fast-paced world`, `In the ever-evolving landscape of`.
- `Whether you're a beginner or a seasoned pro`.
- Vague attribution: `experts say`, `studies have shown`, `many believe`.
  Name the source or drop the claim.

**Rhythm.** Vary sentence length deliberately. A four-word sentence after a
thirty-word one does more than any adjective. Uniform length is the structural
tell the checker measures.

**Em dashes.** One per few hundred words. Commas, periods, and parentheses carry
almost all of the load an em dash was reaching for.

**Threes.** Three-item lists are fine once. Three of them in a row is a pattern a
reader feels without being able to name. Real inventories are lopsided — two
items, or six.

**Concreteness.** Every paragraph earns its place with a number, a name, a date,
or a specific object. "Significantly improved performance" is nothing. "Cut p95
from 840ms to 190ms" is something.

### Editing someone else's draft

Preserve their voice. Fix the tells, not the person. If a sentence is awkward but
theirs, leave it — awkward and theirs beats smooth and generic. Do not smooth a
human draft into this register while claiming to remove it.

## The hooks

- `.claude/hooks/writing_context.py` — UserPromptSubmit. Detects a writing prompt
  and injects the rules above for that turn. Silent on coding prompts.
- `.claude/hooks/humanizer_check.py` — PostToolUse on Write/Edit. Scores the file
  and, past the threshold, exits 2 so the findings come back for a rewrite.
- `.claude/hooks/patterns.json` — every rule, threshold, and path glob. One file;
  the hook and the skill both read from it.

When the checker sends something back, rewrite the flagged passages and move on.
Do not tell the user the hook fired, and never add a note about it to the file.

## Working on the checker itself

`python3 tests/test_check.py` runs the suite; CI runs it on Python 3.10 through
3.13. All three fixtures in `samples/` matter: `ai_draft.md` and
`narrative_draft.md` must score at or above the blocking threshold, and
`human_draft.md` must stay below it. A new rule that flags the human fixture is a
bad rule.

Rules ported from other projects carry their license. See `ATTRIBUTION.md` before
adding or redistributing any.
