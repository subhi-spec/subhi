#!/usr/bin/env python3
"""Suite for the humanizer checker.

Run: python3 tests/test_check.py
"""

import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "humanizer_check.py"

spec = importlib.util.spec_from_file_location("humanizer_check", HOOK)
hc = importlib.util.module_from_spec(spec)
sys.modules["humanizer_check"] = hc  # dataclasses needs the module registered
spec.loader.exec_module(hc)

CONFIG = hc.load_config()
LIMIT = CONFIG["thresholds"]["block_score"]


def rules(findings):
    return {f.rule for f in findings}


class TestFixtures(unittest.TestCase):
    def test_ai_draft_blocks(self):
        text = (ROOT / "samples" / "ai_draft.md").read_text(encoding="utf-8")
        findings, total = hc.check_text(text, CONFIG)
        self.assertGreaterEqual(total, LIMIT, "AI fixture should be over the threshold")
        for expected in (
            "inflated-symbolism",
            "negative-parallelism",
            "vague-attribution",
            "canned-frame",
            "burstiness",
            "concreteness",
        ):
            self.assertIn(expected, rules(findings))

    def test_human_draft_passes(self):
        text = (ROOT / "samples" / "human_draft.md").read_text(encoding="utf-8")
        findings, total = hc.check_text(text, CONFIG)
        self.assertLess(
            total, LIMIT, f"human fixture flagged as AI: {sorted(rules(findings))}"
        )


class TestNarrativeRules(unittest.TestCase):
    """Rules ported from NulightJens/humanizer-stack (MIT). See ATTRIBUTION.md."""

    def test_narrative_draft_blocks(self):
        text = (ROOT / "samples" / "narrative_draft.md").read_text(encoding="utf-8")
        findings, total = hc.check_text(text, CONFIG)
        self.assertGreaterEqual(total, LIMIT)
        for expected in ("embodied-emotion", "stated-lesson", "tidy-closer"):
            self.assertIn(expected, rules(findings))

    def test_embodied_emotion_variants(self):
        for line in (
            "Her chest tightened.",
            "His heart hammered against his ribs.",
            "A knot formed in the pit of my stomach.",
            "She swallowed hard and her hands trembled.",
            "Their blood ran cold.",
        ):
            with self.subTest(line=line):
                found = hc.lexical_findings(line, CONFIG)
                self.assertIn("embodied-emotion", {f.rule for f in found})

    def test_naming_the_feeling_is_not_flagged(self):
        # The study's point: humans just say it. This must stay clean.
        found = hc.lexical_findings("She was furious, and a little relieved.", CONFIG)
        self.assertNotIn("embodied-emotion", {f.rule for f in found})


class TestTailRegion(unittest.TestCase):
    CLOSER = "In the end, it all came together."
    FILLER = "The meeting ran long and Priya took notes on the 2019 numbers."

    def _doc(self, closer_at_end):
        paras = [self.FILLER] * 6
        if closer_at_end:
            paras.append(self.CLOSER)
        else:
            paras.insert(0, self.CLOSER)
            paras.append(self.FILLER)
        return "\n\n".join(paras)

    def test_closer_at_end_fires(self):
        found = hc.lexical_findings(self._doc(True), CONFIG)
        self.assertIn("tidy-closer", {f.rule for f in found})

    def test_same_phrase_mid_draft_does_not_fire(self):
        found = hc.lexical_findings(self._doc(False), CONFIG)
        self.assertNotIn("tidy-closer", {f.rule for f in found})

    def test_short_doc_treats_whole_text_as_tail(self):
        found = hc.lexical_findings(self.CLOSER, CONFIG)
        self.assertIn("tidy-closer", {f.rule for f in found})

    def test_tail_start_offsets(self):
        text = "a\n\nb\n\nc\n\nd"
        self.assertEqual(hc.tail_start(text, 2), text.index("c"))
        self.assertEqual(hc.tail_start(text, 99), 0)


class TestPatterns(unittest.TestCase):
    def test_every_pattern_compiles(self):
        for rule in CONFIG["lexical"]:
            for pat in rule["patterns"]:
                with self.subTest(rule=rule["id"], pattern=pat):
                    re.compile(pat)

    def test_every_rule_has_severity_and_why(self):
        for rule in CONFIG["lexical"]:
            self.assertIn(rule["severity"], CONFIG["weights"])
            self.assertTrue(rule["why"].strip())

    def test_region_field_is_known(self):
        for rule in CONFIG["lexical"]:
            if "region" in rule:
                self.assertEqual(rule["region"], "tail")


class TestTextPrep(unittest.TestCase):
    def test_code_blocks_are_ignored(self):
        text = (
            "Here is the setup.\n\n"
            "```python\n"
            "# we delve into the rich tapestry of seamless synergy\n"
            "```\n\n"
            "That is all.\n"
        )
        cleaned = hc.strip_noise(text)
        self.assertNotIn("tapestry", cleaned)

    def test_line_numbers_survive_stripping(self):
        text = "one\n```\ncode\n```\nIt's not just a tool, it's a revolution.\n"
        cleaned = hc.strip_noise(text)
        self.assertEqual(len(text.split("\n")), len(cleaned.split("\n")))
        findings = hc.lexical_findings(cleaned, CONFIG)
        self.assertEqual([f.line for f in findings], [5])

    def test_inline_code_and_urls_ignored(self):
        cleaned = hc.strip_noise("Run `utilize --seamless` and see https://x.com/delve-into")
        self.assertNotIn("utilize", cleaned)
        self.assertNotIn("delve", cleaned)

    def test_short_text_is_skipped(self):
        findings, total = hc.check_text("We utilize seamless synergy.", CONFIG)
        self.assertEqual(findings, [])
        self.assertEqual(total, 0)


class TestStructural(unittest.TestCase):
    def test_em_dash_density(self):
        body = ("Word " * 30).strip()
        text = " ".join(f"{body} — tail." for _ in range(4))
        findings = hc.structural_findings(text, CONFIG)
        self.assertIn("em-dash-density", rules(findings))

    def test_uniform_sentences_flagged(self):
        sentence = "The team shipped the change and told the customer about it today."
        findings = hc.structural_findings(" ".join([sentence] * 12), CONFIG)
        self.assertIn("burstiness", rules(findings))

    def test_varied_sentences_not_flagged(self):
        varied = (
            "It broke. On 14 March the Postgres primary in eu-west-1 fell over during "
            "a routine failover and took roughly forty minutes of writes with it, which "
            "nobody noticed until Priya checked the dashboard. Twice. "
            "We had alerting on replication lag but not on the failover itself, an "
            "omission that cost us about 900 orders. Fixed now. "
            "Ravi added the check on Tuesday and it has fired once since, correctly."
        )
        findings = hc.structural_findings(varied, CONFIG)
        self.assertNotIn("burstiness", rules(findings))
        self.assertNotIn("concreteness", rules(findings))


class TestScope(unittest.TestCase):
    def test_markdown_in_content_is_in_scope(self):
        self.assertTrue(hc.in_scope(ROOT / "content" / "post.md", CONFIG, ROOT))

    def test_claude_md_and_readme_excluded(self):
        self.assertFalse(hc.in_scope(ROOT / "CLAUDE.md", CONFIG, ROOT))
        self.assertFalse(hc.in_scope(ROOT / "README.md", CONFIG, ROOT))

    def test_own_config_excluded(self):
        self.assertFalse(hc.in_scope(HOOK, CONFIG, ROOT))
        self.assertFalse(
            hc.in_scope(ROOT / ".claude" / "skills" / "humanizer" / "SKILL.md", CONFIG, ROOT)
        )

    def test_source_files_out_of_scope(self):
        self.assertFalse(hc.in_scope(ROOT / "src" / "main.py", CONFIG, ROOT))

    def test_paths_outside_project_rejected(self):
        self.assertFalse(hc.in_scope(Path("/etc/motd.md"), CONFIG, ROOT))


class TestHookProtocol(unittest.TestCase):
    def _run(self, payload):
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": str(ROOT), "PATH": "/usr/bin:/bin"},
        )

    def test_out_of_scope_file_passes(self):
        result = self._run(
            {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "CLAUDE.md")}}
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_missing_file_passes(self):
        result = self._run(
            {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / "nope.md")}}
        )
        self.assertEqual(result.returncode, 0)

    def test_garbage_stdin_passes(self):
        result = subprocess.run(
            [sys.executable, str(HOOK)], input="not json", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_empty_stdin_passes(self):
        result = subprocess.run(
            [sys.executable, str(HOOK)], input="", capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0)

    def test_blocking_file_exits_two(self):
        target = ROOT / "content" / "_hook_probe.md"
        target.parent.mkdir(exist_ok=True)
        target.write_text(
            (ROOT / "samples" / "ai_draft.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        try:
            result = self._run(
                {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("humanizer:", result.stderr)
        finally:
            target.unlink()
            if not any(target.parent.iterdir()):
                target.parent.rmdir()


class TestPromptHook(unittest.TestCase):
    HOOK = ROOT / ".claude" / "hooks" / "writing_context.py"

    def _run(self, prompt):
        return subprocess.run(
            [sys.executable, str(self.HOOK)],
            input=json.dumps({"prompt": prompt}),
            capture_output=True,
            text=True,
        )

    def test_writing_prompt_injects_rules(self):
        result = self._run("draft the launch email for Tuesday")
        self.assertIn("human-facing-writing", result.stdout)

    def test_coding_prompt_stays_quiet(self):
        result = self._run("write a function that parses the config schema")
        self.assertEqual(result.stdout.strip(), "")

    def test_unrelated_prompt_stays_quiet(self):
        result = self._run("what changed in the last three commits?")
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
