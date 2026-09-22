---
name: humanizer
description: Strip AI-writing tells from human-facing prose — marketing copy, emails, newsletters, landing pages, posts, scripts. Use when drafting anything a person will read as writing, when asked to humanize or de-AI a draft, when asked whether something reads as AI-generated, or when the humanizer_check hook sends a file back. Fixes structure first (shape, rhythm, concreteness), then vocabulary.
---

# Humanizer

## When to reach for this

Drafting or editing prose a person reads as writing. Not code, not commit
messages, not internal API docs.

If `humanizer_check.py` sent a file back, the findings name the rule IDs. Look
each one up in `.claude/hooks/patterns.json` — the `why` field says what the fix
is, and it is the same file the checker reads, so it is never out of date.

## Order of operations

Structure before vocabulary. StoryScope's finding is the whole argument for this:
AI text stays separable from human text at 93.9 macro-F1 *after* a professional
rewrite of the prose. Word swaps do not touch what actually gives it away.

### 1. Shape

Say out loud what the piece does before writing a line of it.

- Opening line delivers the thing, not the runway to the thing.
- The middle has an order you can defend. "Point one, point two, point three" is
  not an order, it is a lack of one.
- The ending is chosen in advance. Most AI drafts end twice: once where the
  argument runs out, then again with a paragraph restating it.

Sections do not have to be the same size. Let the one that matters run long.

### 2. Rhythm

Read the draft counting words per sentence. If most land between fourteen and
twenty-two, that is the tell the checker measures as burstiness. Fix it by
cutting one sentence to the bone and letting the next one run.

### 3. Concreteness

Go paragraph by paragraph. Find the number, name, date, or object. If there is
none, either add one or delete the paragraph — it was not saying anything.

`Significantly improved onboarding` → `Cut signup from nine fields to three.`

### 4. Vocabulary

Only now. The full pattern list is in `.claude/hooks/patterns.json`; the
`lexical` array is grouped by rule ID with a `why` on each. The short version:

| Rule | Looks like | Fix |
|---|---|---|
| `inflated-symbolism` | stands as a testament, plays a pivotal role | say what happened |
| `ai-vocabulary` | delve, seamless, unlock the power, ever-evolving | plain verb, plain noun |
| `negative-parallelism` | it's not just X, it's Y | assert the one true thing |
| `participial-tail` | …, highlighting the importance of… | cut the clause |
| `vague-attribution` | experts say, studies have shown | name the source or cut |
| `canned-frame` | In conclusion, In today's world, let's dive in | start and stop cold |
| `corporate-verbs` | utilize, leverage, facilitate | use, use, help |
| `promo-adjectives` | stunning, vibrant, must-visit, meticulous | describe the thing |

## Channel notes

**Email.** No "I hope this finds you well." First line says why you wrote. Subject
lines are lowercase and specific; title case reads like a campaign.

**Video and reel scripts.** The first three seconds are one concrete claim, not a
question. "You probably didn't know that…" is a hook; "Let's talk about…" is not.
Write for the ear: contractions, fragments, sentences that end early.

**LinkedIn.** The one-line-per-paragraph stack is itself a tell now. Write real
paragraphs. Skip the closing "What's your take? 👇".

**Blog and newsletter.** No summary of what the post will cover. Start with the
specific case and generalize from it, not the reverse.

## Editing someone else's writing

Their voice survives; the tells go. A sentence that is clumsy but theirs stays.
The failure mode here is sanding a human draft down into exactly the register
this skill exists to remove.

## Checking your own work

```
.claude/hooks/humanizer_check.py path/to/draft.md
```

Findings print with line numbers and a score. Score at or above `block_score` in
`patterns.json` means it would have been sent back. Clean output means clean —
though a clean score is a floor, not a finish line. The checker cannot tell you
whether the piece is worth reading.
