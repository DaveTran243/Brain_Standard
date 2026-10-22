"""Tests for the brain package. Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from brain import config, gates, metrics, notes  # noqa: E402
from brain.cli import main  # noqa: E402

RECORD = """---
source: https://example.org/article
retrieved: 2026-10-20
archived: https://web.archive.org/example
grade: {grade}
verification: "checked against the original"
---

# A claim brought in by an agent
"""

PROJECT = """---
type: project
status: active
started: 2026-10-01
outcome: "x"
done_when: "y"
stop_when: "z"
{extra}---

# Project
"""


class BrainTestCase(unittest.TestCase):
    """A fresh copy of the standard brain in a temporary folder, at a fixed time."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(REPO / "brain.toml", self.tmp / "brain.toml")
        shutil.copytree(REPO / "vault", self.tmp / "vault")
        self.vault = self.tmp / "vault"
        os.environ[config.NOW_ENV] = "2026-10-20T21:30:00"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)
        os.environ.pop(config.NOW_ENV, None)

    def run_brain(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = main(["--root", str(self.tmp), *args])
        return code, out.getvalue()

    def write(self, rel: str, text: str) -> Path:
        p = self.vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    def read(self, rel: str) -> str:
        return (self.vault / rel).read_text(encoding="utf-8")

    def brain(self):
        return config.open_brain(self.tmp)

    def agent_items(self) -> list[Path]:
        return notes.list_notes(self.vault / "00-Inbox/agent", "_")


class CoreTest(BrainTestCase):
    def test_template_vault_is_clean(self):
        code, out = self.run_brain("check")
        self.assertEqual(code, 0, out)
        self.assertIn("Vault is clean", out)

    def test_capture_to_inbox(self):
        code, _ = self.run_brain("capture", "Read", "chapter", "5")
        self.assertEqual(code, 0)
        self.assertIn("- [2026-10-20 21:30] (hand) Read chapter 5", self.read("00-Inbox/Inbox.md"))
        self.run_brain("capture", "Call the accountant", "--channel", "telegram")
        self.assertIn("(telegram) Call the accountant", self.read("00-Inbox/Inbox.md"))

    def test_config_override_beats_default(self):
        (self.tmp / "brain.toml").write_text(
            '[brain]\nvault = "vault"\n[capture]\ndefault_channel = "voice"\n[clarify]\nfleeting_max_days = 30\n',
            encoding="utf-8")
        b = self.brain()
        self.assertEqual(b.cfg["clarify"]["fleeting_max_days"], 30)
        self.assertEqual(b.cfg["gates"]["strict"], True)  # untouched default
        self.run_brain("capture", "an idea")
        self.assertIn("(voice) an idea", self.read("00-Inbox/Inbox.md"))

    def test_missing_brain_toml(self):
        empty = Path(tempfile.mkdtemp())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = main(["--root", str(empty), "check"])
        shutil.rmtree(empty)
        self.assertEqual(code, 1)
        self.assertIn("No brain.toml found", out.getvalue())


class GateTest(BrainTestCase):
    def test_submit_without_full_record_is_returned(self):
        f = self.tmp / "item.md"
        f.write_text("---\nsource: https://x\ngrade: B2\n---\n# Claim\n", encoding="utf-8")
        code, out = self.run_brain("submit", str(f))
        self.assertEqual(code, 2)
        self.assertIn("missing retrieved, archived, verification", out)
        self.assertEqual(self.agent_items(), [])

    def test_comment_only_field_counts_as_empty(self):
        f = self.tmp / "item.md"
        f.write_text(RECORD.format(grade="B2").replace("archived: https://web.archive.org/example",
                                                       "archived:   # not yet"), encoding="utf-8")
        code, out = self.run_brain("submit", str(f))
        self.assertEqual(code, 2)
        self.assertIn("missing archived", out)

    def test_malformed_grade(self):
        f = self.tmp / "item.md"
        f.write_text(RECORD.format(grade="G9"), encoding="utf-8")
        code, out = self.run_brain("submit", str(f))
        self.assertEqual(code, 2)
        self.assertIn("grade 'G9' must be source A–F + credibility 1–6", out)

    def test_rejected_grades_go_to_log(self):
        for grade in ("E1", "B5"):
            f = self.tmp / f"item-{grade}.md"
            f.write_text(RECORD.format(grade=grade), encoding="utf-8")
            code, _ = self.run_brain("submit", str(f))
            self.assertEqual(code, 3)
        log = self.read("_log/rejected.md")
        self.assertIn("rejected · E1", log)
        self.assertIn("rejected · B5", log)
        self.assertEqual(self.agent_items(), [])

    def test_reach_and_inbox_line(self):
        g = config.defaults()["gates"]
        expected = {"B2": "card", "A3": "literature", "C6": "literature", "D1": "fleeting", "F6": "fleeting",
                    "E2": "reject", "x": "malformed"}
        for grade, reach in expected.items():
            self.assertEqual(gates.reach(grade, g), reach, grade)
        f = self.tmp / "item.md"
        f.write_text(RECORD.format(grade="D3"), encoding="utf-8")
        code, out = self.run_brain("submit", str(f))
        self.assertEqual(code, 0, out)
        (item,) = self.agent_items()
        fm, _ = notes.frontmatter(item.read_text(encoding="utf-8"))
        self.assertEqual((fm["max_reach"], fm["label"], fm["submitted"]), ("fleeting", "unverified", "2026-10-20"))
        self.assertIn("(agent) A claim brought in by an agent · D3 · up to fleeting (unverified) → agent/",
                      self.read("00-Inbox/Inbox.md"))

    def test_check_catches_agent_item_without_record(self):
        self.write("00-Inbox/agent/dropped-in.md", "---\nsource: https://x\n---\n# x\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 1)
        self.assertIn("G1-01 · 00-Inbox/agent/dropped-in.md", out)

    def test_g2_literature(self):
        self.write("30-Knowledge/literature/a.md", "---\ntype: literature\ngrade: D2\n---\n- point\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 1)
        self.assertIn("G2-02 · 30-Knowledge/literature/a.md: literature needs source A–C", out)
        self.assertIn("G2-03", out)

    def test_g3_and_permanent_links(self):
        self.write("30-Knowledge/permanent/p1.md", "---\nid: 202610201200\ngrade: B3\n---\n# An idea\nNo link.\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 1)
        self.assertIn("KN-01", out)
        self.assertIn("G3-02 · 30-Knowledge/permanent/p1.md: permanent needs credibility 1–2", out)
        self.write("30-Knowledge/permanent/p1.md", "---\nid: 202610201200\ngrade: B2\n---\n# An idea\nLinks [[p0]].\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 0, out)

    def test_old_fleeting_warns(self):
        self.write("30-Knowledge/fleeting/idea.md", "---\ndate: 2026-10-01\n---\nan idea\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 0)
        self.assertIn("KN-03 · 30-Knowledge/fleeting/idea.md: fleeting note is 19 days old", out)

    def test_valid_until(self):
        self.assertEqual(str(notes.expires_on("2027-04")), "2027-05-01")
        self.assertEqual(str(notes.expires_on("2026-12")), "2027-01-01")
        self.write("30-Knowledge/literature/old.md", "---\ntype: literature\nvalid_until: 2026-09\n---\n- figure\n")
        _, out = self.run_brain("check")
        self.assertIn("VD-01 · 30-Knowledge/literature/old.md: past its valid_until date (2026-09)", out)


class ProjectTest(BrainTestCase):
    def test_active_project_missing_criteria(self):
        self.write("10-Action/13-Projects/p.md", "---\nstatus: active\noutcome: x\n---\n")
        code, out = self.run_brain("check")
        self.assertEqual(code, 1)
        self.assertIn("AC-02 · 10-Action/13-Projects/p.md: missing done_when", out)
        self.assertIn("missing stop_when", out)

    def test_milestone_without_board_warns(self):
        self.write("10-Action/13-Projects/p.md", PROJECT.format(extra='milestone: "M1"\n'))
        code, out = self.run_brain("check")
        self.assertEqual(code, 0)
        self.assertIn("EX-01", out)
        self.assertIn("EX-02", out)

    def test_no_limits(self):
        """No limit on projects or next actions: 5 active projects and 25 tasks are fine."""
        lines = []
        for i in range(5):
            self.write(f"10-Action/13-Projects/p{i}.md", PROJECT.format(extra=f"board: https://example.org/b{i}\n"))
            lines += [f"- [ ] Do task {i}-{j} · [[p{i}]]" for j in range(5)]
        na = self.vault / "10-Action/11-next-actions.md"
        na.write_text(na.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
        code, out = self.run_brain("check")
        self.assertEqual(code, 0, out)
        self.assertIn("Vault is clean", out)
        self.assertEqual(self.run_brain("turn", "task", "many", "projects")[0], 0)
        m = metrics.measure(self.brain())
        self.assertEqual((m["projects_active"], m["next_open"]), (5, 25))


class TurnAndWeeklyTest(BrainTestCase):
    def test_turn_refused_while_errors(self):
        self.write("30-Knowledge/permanent/p.md", "---\nid: 1\n---\n# idea\n")
        code, out = self.run_brain("turn", "idea", "wrote a note")
        self.assertEqual(code, 1)
        self.assertIn("Turn not closed", out)
        self.assertFalse((self.vault / "_log/turns.md").exists())

    def test_turn_log(self):
        code, out = self.run_brain("turn", "file", "opened category 51")
        self.assertEqual(code, 0, out)
        self.assertIn("Brain: file · opened category 51", out)
        self.assertIn("- [2026-10-20 21:30] file · opened category 51", self.read("_log/turns.md"))

    def test_turn_type_from_config(self):
        code, _ = self.run_brain("turn", "viec", "old type")
        self.assertEqual(code, 2)

    def test_weekly(self):
        self.run_brain("capture", "one idea")
        self.run_brain("turn", "idea", "captured an idea")
        code, out = self.run_brain("weekly", "--save")
        self.assertEqual(code, 0, out)
        self.assertIn("Metrics · 2026-W43", out)
        self.assertIn("| Inbox items · oldest (days) | 1 · 0 |", out)
        self.assertIn("| Turns in 7 days | 1 (task 0, idea 1, file 0, drop 0) |", out)
        self.assertTrue((self.vault / "weekly/2026-W43.md").is_file())


class AssistantTest(BrainTestCase):
    def add_tasks(self, *lines: str) -> Path:
        p = self.vault / "10-Action/11-next-actions.md"
        p.write_text(p.read_text(encoding="utf-8") + "".join(f"{line}\n" for line in lines), encoding="utf-8")
        return p

    def test_assign_adds_label_and_date(self):
        p = self.add_tasks("- [ ] Draft an email to the accountant · @computer", "- [ ] Call mum")
        code, out = self.run_brain("assign", "accountant", "auto")
        self.assertEqual(code, 0, out)
        self.assertIn("- [ ] Draft an email to the accountant · @computer · @javis:auto · assigned 2026-10-20",
                      p.read_text(encoding="utf-8"))
        code, out = self.run_brain("assign", "accountant", "full")
        self.assertEqual(code, 2)
        self.assertIn("already assigned to Javis", out)

    def test_assign_needs_exactly_one_match(self):
        self.add_tasks("- [ ] Call mum", "- [ ] Call dad")
        code, out = self.run_brain("assign", "Call", "auto")
        self.assertEqual(code, 2)
        self.assertIn("found 2", out)

    def test_assigned_filters_by_level(self):
        self.add_tasks("- [ ] Compare printer prices · @javis:suggest", "- [ ] Send the quote · @javis:full",
                       "- [x] Old task · @javis:auto · done 2026-10-19", "- [ ] My own task")
        code, out = self.run_brain("assigned")
        self.assertEqual(code, 0)
        self.assertIn("1 · suggest · Compare printer prices", out)
        self.assertIn("2 · full · Send the quote", out)
        self.assertNotIn("Old task", out)
        self.assertNotIn("My own task", out)
        _, out = self.run_brain("assigned", "--level", "auto")
        self.assertNotIn("Send the quote", out)

    def test_report_checks_off_and_writes_inbox(self):
        p = self.add_tasks("- [ ] Compare printer prices · @web · @javis:suggest · assigned 2026-10-18")
        code, out = self.run_brain("report", "1", "Three", "quotes", "in", "drafts/printer.md")
        self.assertEqual(code, 0, out)
        self.assertIn("- [x] Compare printer prices · @web · @javis:suggest · assigned 2026-10-18 · done 2026-10-20",
                      p.read_text(encoding="utf-8"))
        self.assertIn('- [2026-10-20 21:30] (javis) Result "Compare printer prices · @web": Three quotes in drafts/printer.md',
                      self.read("00-Inbox/Inbox.md"))
        code, _ = self.run_brain("report", "1", "again")
        self.assertEqual(code, 2)

    def test_check_assignment_rules(self):
        self.add_tasks("- [ ] Call mum · @javis", "- [ ] Look up the schedule · @javis:auto · assigned 2026-10-01",
                       "- [x] Done already · @javis · done 2026-10-01")
        code, out = self.run_brain("check")
        self.assertEqual(code, 1)
        self.assertIn("AS-01 · next action line", out)
        self.assertIn("AS-02 · next action line", out)
        self.assertIn("assigned 19 days ago", out)
        self.assertEqual(out.count("AS-0"), 2)

    def test_weekly_counts_assignments(self):
        self.add_tasks("- [ ] A · @javis:auto · assigned 2026-10-01", "- [ ] B · @javis:auto · assigned 2026-10-19",
                       "- [x] C · @javis:auto · assigned 2026-10-15 · done 2026-10-18")
        _, out = self.run_brain("weekly")
        self.assertIn("| Assigned to Javis: open · done in 7 days · stale | 2 · 1 · 1 |", out)

    def test_assistant_name_and_label_from_config(self):
        (self.tmp / "brain.toml").write_text('[brain]\nvault = "vault"\n[assistant]\nname = "Ada"\nlabel = "@ada"\n',
                                             encoding="utf-8")
        p = self.add_tasks("- [ ] Book the venue")
        code, out = self.run_brain("assign", "venue", "suggest")
        self.assertEqual(code, 0, out)
        self.assertIn("Assigned to Ada (suggest)", out)
        self.assertIn("@ada:suggest", p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
