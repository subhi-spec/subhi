#!/usr/bin/env python3
"""Flag AI-writing tells in human-facing prose.

Two ways to run it:

  1. As a Claude Code PostToolUse hook. Claude Code pipes the tool call as JSON
     on stdin; the script picks the edited file out of it, checks it, and writes
     findings to stderr with exit code 2 so Claude sees them and fixes the draft.

  2. By hand:  .claude/hooks/humanizer_check.py draft.md
     Same checks, findings on stdout, exit 1 if the draft is over the threshold.

Rules live in patterns.json next to this file. Nothing here is hardcoded except
the arithmetic.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
PATTERNS_PATH = HERE / "patterns.json"


@dataclass
class Finding:
    line: int
    rule: str
    severity: str
    excerpt: str
    why: str

    @property
    def weight_key(self) -> str:
        return self.severity


# ---------------------------------------------------------------- text prep

FENCE_RE = re.compile(r"^(?P<fence>```+|~~~+).*$")
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
URL_RE = re.compile(r"https?://\S+")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>\n]{1,200}>")


def strip_noise(text: str) -> str:
    """Blank out code, URLs, and markup so prose rules only see prose.

    Lines are blanked rather than deleted so reported line numbers still match
    the file on disk.
    """
    text = FRONTMATTER_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)

    out: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        stripped = line.lstrip()
        match = FENCE_RE.match(stripped)
        if fence is None and match:
            fence = match.group("fence")[:3]
            out.append("")
            continue
        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            out.append("")
            continue
        line = INLINE_CODE_RE.sub(" ", line)
        line = URL_RE.sub(" ", line)
        line = HTML_TAG_RE.sub(" ", line)
        out.append(line)
    return "\n".join(out)


WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])[\s\n]+")


def words(text: str) -> list[str]:
    return WORD_RE.findall(text)


def prose_lines(text: str) -> list[str]:
    """Lines that are running prose: not headings, not list scaffolding."""
    keep = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("|"):
            continue
        keep.append(re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", line))
    return keep


def sentences(text: str) -> list[str]:
    joined = " ".join(prose_lines(text))
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(joined) if len(words(s)) >= 3]


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def excerpt(text: str, start: int, end: int, pad: int = 24) -> str:
    left = max(0, start - pad)
    right = min(len(text), end + pad)
    snippet = text[left:right].replace("\n", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    if left > 0:
        snippet = "…" + snippet
    if right < len(text):
        snippet = snippet + "…"
    return snippet


# ------------------------------------------------------------------- checks


def lexical_findings(text: str, config: dict) -> list[Finding]:
    found: list[Finding] = []
    for rule in config.get("lexical", []):
        for raw in rule["patterns"]:
            for m in re.finditer(raw, text, re.IGNORECASE | re.MULTILINE):
                found.append(
                    Finding(
                        line=line_of(text, m.start()),
                        rule=rule["id"],
                        severity=rule["severity"],
                        excerpt=excerpt(text, m.start(), m.end()),
                        why=rule["why"],
                    )
                )
    return found


def structural_findings(text: str, config: dict) -> list[Finding]:
    found: list[Finding] = []
    struct = config.get("structural", {})
    limits = config.get("thresholds", {})
    body = " ".join(prose_lines(text))
    word_count = len(words(body))
    if word_count == 0:
        return found

    # Em dash density.
    spec = struct.get("em_dash")
    if spec:
        dashes = [m for m in re.finditer(r"—|(?<=\w)\s--\s(?=\w)", body)]
        per_1000 = len(dashes) * 1000.0 / word_count
        ceiling = limits.get("em_dash_per_1000_words", 6.0)
        if len(dashes) >= 2 and per_1000 > ceiling:
            found.append(
                Finding(
                    line=line_of(text, text.find("—")) if "—" in text else 1,
                    rule="em-dash-density",
                    severity=spec["severity"],
                    excerpt=f"{len(dashes)} em dashes in {word_count} words "
                    f"({per_1000:.1f} per 1000, ceiling {ceiling})",
                    why=spec["why"],
                )
            )

    # Rule of three: "a, b, and c" triads stacked up.
    spec = struct.get("rule_of_three")
    if spec:
        triad = re.compile(
            r"\b[\w'’\-]+(?:\s+[\w'’\-]+){0,3},\s+[\w'’\-]+(?:\s+[\w'’\-]+){0,3},\s+"
            r"(?:and|or)\s+[\w'’\-]+"
        )
        hits = list(triad.finditer(body))
        minimum = spec.get("min_triads", 3)
        if len(hits) >= minimum:
            found.append(
                Finding(
                    line=1,
                    rule="rule-of-three",
                    severity=spec["severity"],
                    excerpt=f"{len(hits)} three-item lists, e.g. “{hits[0].group(0)[:70]}”",
                    why=spec["why"],
                )
            )

    sents = sentences(text)
    lengths = [len(words(s)) for s in sents]

    # Burstiness: humans vary sentence length far more than models do.
    spec = struct.get("burstiness")
    if spec and len(lengths) >= limits.get("burstiness_min_sentences", 8):
        stdev = statistics.pstdev(lengths)
        floor = limits.get("burstiness_min_stdev", 5.0)
        if stdev < floor:
            found.append(
                Finding(
                    line=1,
                    rule="burstiness",
                    severity=spec["severity"],
                    excerpt=f"sentence length stdev {stdev:.1f} over {len(lengths)} "
                    f"sentences (floor {floor}); mean {statistics.mean(lengths):.0f} words",
                    why=spec["why"],
                )
            )

    # Concreteness: numbers, proper nouns, dates.
    spec = struct.get("concreteness")
    if spec and word_count >= limits.get("min_words", 40):
        digits = len(re.findall(r"\b\d[\d,.]*\b", body))
        propers = len(re.findall(r"(?<![.!?]\s)(?<!^)\b[A-Z][a-z]{2,}\b", body))
        per_100 = (digits + propers) * 100.0 / word_count
        floor = limits.get("concreteness_min_per_100_words", 1.0)
        if per_100 < floor:
            found.append(
                Finding(
                    line=1,
                    rule="concreteness",
                    severity=spec["severity"],
                    excerpt=f"{digits} numbers and {propers} proper nouns "
                    f"in {word_count} words ({per_100:.1f} per 100, floor {floor})",
                    why=spec["why"],
                )
            )

    return found


def score(findings: list[Finding], weights: dict) -> int:
    return sum(weights.get(f.weight_key, 1) for f in findings)


def check_text(text: str, config: dict) -> tuple[list[Finding], int]:
    cleaned = strip_noise(text)
    if len(words(cleaned)) < config.get("thresholds", {}).get("min_words", 40):
        return [], 0
    findings = lexical_findings(cleaned, config) + structural_findings(cleaned, config)
    findings.sort(key=lambda f: (f.severity != "high", f.line))
    return findings, score(findings, config.get("weights", {}))


# -------------------------------------------------------------------- scope


def in_scope(path: Path, config: dict, project_root: Path) -> bool:
    try:
        rel = path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return False
    scope = config.get("scope", {})
    if not any(fnmatch.fnmatch(rel, pat) for pat in scope.get("include", [])):
        return False
    return not any(fnmatch.fnmatch(rel, pat) for pat in scope.get("exclude", []))


def project_root() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return HERE.parent.parent.resolve()


# ------------------------------------------------------------------- report


def render(path: Path, findings: list[Finding], total: int, limit: int) -> str:
    verdict = "BLOCKING" if total >= limit else "advisory"
    lines = [
        f"humanizer: {len(findings)} AI-writing tell(s) in {path.name} "
        f"— score {total} (threshold {limit}, {verdict})",
        "",
    ]
    by_rule: dict[str, list[Finding]] = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(f)
    for rule, group in by_rule.items():
        head = group[0]
        lines.append(f"  [{head.severity}] {rule} — {head.why}")
        for f in group[:4]:
            lines.append(f"      line {f.line}: {f.excerpt}")
        if len(group) > 4:
            lines.append(f"      … and {len(group) - 4} more")
        lines.append("")
    lines.append(
        "Rewrite the flagged passages, then move on. Do not announce the rewrite "
        "to the user and do not add a note about it to the file."
    )
    return "\n".join(lines)


# --------------------------------------------------------------------- main


def load_config() -> dict:
    with PATTERNS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def paths_from_hook_payload(payload: dict) -> list[Path]:
    tool_input = payload.get("tool_input") or {}
    candidates = []
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            candidates.append(Path(value))
    for edit in tool_input.get("edits") or []:
        value = (edit or {}).get("file_path")
        if isinstance(value, str) and value:
            candidates.append(Path(value))
    return candidates


def run_hook() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    config = load_config()
    root = project_root()
    limit = config.get("thresholds", {}).get("block_score", 6)

    reports: list[str] = []
    for path in paths_from_hook_payload(payload):
        if not path.is_absolute():
            path = (root / path).resolve()
        if not path.is_file() or not in_scope(path, config, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings, total = check_text(text, config)
        if findings and total >= limit:
            reports.append(render(path, findings, total, limit))

    if reports:
        sys.stderr.write("\n\n".join(reports) + "\n")
        return 2
    return 0


def run_cli(argv: list[str]) -> int:
    config = load_config()
    root = project_root()
    limit = config.get("thresholds", {}).get("block_score", 6)
    worst = 0
    for arg in argv:
        path = Path(arg).resolve()
        if not path.is_file():
            print(f"humanizer: no such file: {arg}", file=sys.stderr)
            worst = max(worst, 1)
            continue
        findings, total = check_text(path.read_text(encoding="utf-8"), config)
        if findings:
            print(render(path, findings, total, limit))
            if total >= limit:
                worst = max(worst, 1)
        else:
            print(f"humanizer: {path.name} clean")
    return worst


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if args:
        return run_cli(args)
    return run_hook()


if __name__ == "__main__":
    sys.exit(main())
