# humanizer stack

Hooks and standing instructions that stop Claude Code from writing like Claude
Code whenever the output is meant for a person.

Built from the reel at
[instagram.com/reel/DbJzWBfxPvD](https://www.instagram.com/reel/DbJzWBfxPvD/),
and from the three sources it points at:

- Wikipedia, [*Signs of AI writing*](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing)
- [`blader/humanizer`](https://github.com/blader/humanizer)
- [`jenna-russell/storyscope`](https://github.com/jenna-russell/storyscope) — *StoryScope: Investigating Idiosyncrasies in AI Fiction* (Russell, Rajendhran, Pham, Iyyer, Wieting; COLM 2026)

The reel's own repo is [`NulightJens/humanizer-stack`](https://github.com/NulightJens/humanizer-stack),
which packages the same sources as two Claude Code skills with a surface scanner
and a structural one. This repo takes the hook route instead — see
[Prior art](#prior-art) for where the two differ and what each is better at.

StoryScope is the reason this is a hook and not a word list. It separates AI
fiction from human fiction at 93.2 macro-F1 using narrative structure alone, and
still manages 93.9 after the prose has been professionally rewritten. Replacing
"delve" does not fix a draft whose shape gives it away, so the checker measures
shape too: sentence-length variance and concreteness, not just banned words.

## What's in here

```
CLAUDE.md                          standing rules, loaded every session
.claude/settings.json              hook wiring
.claude/hooks/patterns.json        every rule, threshold, and path glob
.claude/hooks/humanizer_check.py   PostToolUse — scores the file after a write
.claude/hooks/writing_context.py   UserPromptSubmit — injects rules on writing prompts
.claude/skills/humanizer/SKILL.md  the editing procedure, for deeper passes
samples/                           one AI draft, one human draft
tests/test_check.py                24 tests
```

## How it behaves

Ask for a landing page. `writing_context.py` spots the writing prompt and adds
the rules to that turn — it stays silent on "write a function that parses the
config schema", so coding turns cost nothing.

Claude writes the file. `humanizer_check.py` scores it. High-severity rules count
3, medium count 1, and at 6 the hook exits 2, which sends the findings back with
line numbers and a one-line reason each. Claude rewrites before you ever see the
draft.

```
$ .claude/hooks/humanizer_check.py samples/ai_draft.md
humanizer: 31 AI-writing tell(s) in ai_draft.md — score 75 (threshold 6, BLOCKING)

  [high] inflated-symbolism — Ceremonial significance the subject did not earn.
      line 3: …the morning routine stands as a testament to the importance of…
  [high] burstiness — Sentence lengths are too uniform.
      line 1: sentence length stdev 4.3 over 16 sentences (floor 5.0)
  [high] concreteness — Almost no numbers, names, or dates.
      line 1: 0 numbers and 0 proper nouns in 208 words (0.0 per 100, floor 1.0)
  …
```

The same command on `samples/human_draft.md` prints `clean`.

## Setup

Nothing to install. Python 3.9+, standard library only. Clone it, or copy
`.claude/` and `CLAUDE.md` into a project you already have.

Check that the hooks registered:

```
/hooks          # inside Claude Code
```

## Tuning

Everything lives in `.claude/hooks/patterns.json`.

- **Too noisy** — raise `thresholds.block_score`, or drop a rule's `severity`
  from `high` to `medium`.
- **Wrong files getting checked** — `scope.include` and `scope.exclude` are glob
  patterns against repo-relative paths. `CLAUDE.md`, `README.md`, and everything
  under `.claude/` are excluded already, since those are written for machines and
  maintainers.
- **Your own tells** — add a regex to any `lexical` rule, or add a rule with its
  own `id`, `severity`, and `why`. The `why` text is what Claude sees when the
  rule fires, so write it as an instruction.

After any change:

```
python3 tests/test_check.py
```

`samples/ai_draft.md` has to stay above the threshold and `samples/human_draft.md`
has to stay below it. A rule that flags the human draft is a rule that will flag
your writing.

## Prior art

[`NulightJens/humanizer-stack`](https://github.com/NulightJens/humanizer-stack)
is the reference implementation, by the author of the reel. Same sources,
different shape, and the two are complementary rather than competing.

| | humanizer-stack | this repo |
|---|---|---|
| Delivery | Two skills, invoked on intent | Hooks, fire whether or not Claude reaches for them |
| Scope control | You point the scanner at files | Glob-based, automatic |
| Surface tells | 4 rules | 10 rules, severity-weighted into one score |
| Structure | Paragraph-length CV, reader address, numbers | Sentence-length variance, concreteness, em-dash density, triad stacking |
| Narrative tells | Embodied emotion, stated lesson, tidy closer | Not covered |
| Reference docs | StoryScope's 30 features with rates, genre calibration, model fingerprints | The rule table in SKILL.md |
| Escape hatch | `copy-ignore` comment per line | None yet |
| Tests | — | 24 |

Measured against each other on the fixtures in `samples/`: on marketing copy this
repo flags 31 tells to their 6, and their em-dash rule false-positives on
`human_draft.md` because it fires per line rather than on density. On narrative
prose the result inverts — their structural scanner catches 7 tells in a passage
where this one catches 1 and would not block.

If you write fiction, personal essays, or anything with a narrator, install their
skills alongside these hooks.

## Limits

Regex catches phrasing, not thinking. A draft can score clean and still be empty.
The checker also never sees what Claude says in chat — it only fires on files
written to disk, so conversational replies are governed by `CLAUDE.md` alone.
