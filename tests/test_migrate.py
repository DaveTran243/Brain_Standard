"""Tests for brain migrate, on a copy of a real 3.0 brain (tests/fixtures/brain-3.0)."""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

from brain import notes  # noqa: E402
from brain.cli import main  # noqa: E402

FIXTURE = REPO / "tests/fixtures/brain-3.0"


class MigrateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(FIXTURE, self.tmp, dirs_exist_ok=True)
        self.vault = self.tmp / "vault"
        os.environ["BRAIN_NOW"] = "2026-10-20T21:30:00"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)
        os.environ.pop("BRAIN_NOW", None)

    def run_brain(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = main(["--root", str(self.tmp), *args])
        return code, out.getvalue()

    def read(self, rel: str) -> str:
        return (self.vault / rel).read_text(encoding="utf-8")

    def test_dry_run_changes_nothing(self):
        before = {p: p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}
        code, out = self.run_brain("migrate", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Would change", out)
        self.assertIn("brain.toml: rename tables and keys", out)
        after = {p: p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_config_is_converted(self):
        self.run_brain("migrate")
        with (self.tmp / "brain.toml").open("rb") as f:
            cfg = tomllib.load(f)
        self.assertEqual(cfg["brain"]["version"], "4.0.0")
        self.assertEqual(cfg["gates"]["required_fields"], ["source", "retrieved", "archived", "grade", "verification"])
        self.assertEqual(cfg["gates"]["fleeting_only_sources"], ["D", "F"])
        self.assertEqual(cfg["assistant"], {"label": "@javis", "stale_after_days": 7})
        self.assertEqual(cfg["johnny_decimal"], {"area": "50-59", "max_categories": 10})
        self.assertNotIn("kiem_duyet", cfg)

    def test_files_and_folders_are_renamed(self):
        self.run_brain("migrate")
        for rel in ("_templates/source-record.md", "10-Action/13-Projects/_template-project.md",
                    "weekly/_template-weekly.md", "Code/50 System/50.00 Index (JDex).md", "_log/rejected.md"):
            self.assertTrue((self.vault / rel).is_file(), rel)
        for rel in ("_mau", "Coding", "_log/k1.md"):
            self.assertFalse((self.vault / rel).exists(), rel)
        jdex = self.read("Code/50 System/50.00 Index (JDex).md")
        self.assertIn("Code/50 System/", jdex)
        self.assertNotIn("Coding/", jdex)

    def test_frontmatter_keys_and_values(self):
        self.run_brain("migrate")
        fm, _ = notes.frontmatter(self.read("10-Action/13-Projects/website.md"))
        self.assertEqual((fm["type"], fm["status"], fm["outcome"], fm["due"]), ("project", "active", "Trang bán hàng chạy được", "2026-12-31"))
        fm, _ = notes.frontmatter(self.read("00-Inbox/agent/20261018-090500-lam-phat.md"))
        self.assertEqual((fm["grade"], fm["archived"], fm["max_reach"], fm["submitted"]), ("B2", "https://web.archive.org/cpi", "card", "2026-10-18"))
        fm, _ = notes.frontmatter(self.read("30-Knowledge/permanent/202610181200-cache.md"))
        self.assertEqual((fm["links"], fm["cards"]), ('["[[a]]"]', "0"))
        self.assertIn("# grade: B2", self.read("30-Knowledge/permanent/_template-permanent.md"))

    def test_lines_are_converted_only_in_their_files(self):
        self.run_brain("migrate")
        inbox = self.read("00-Inbox/Inbox.md")
        self.assertIn("(hand) gọi lại kế toán", inbox)
        self.assertIn("· B2 · up to flashcard → agent/", inbox)
        self.assertIn('(javis) Result "Tra giá máy in"', inbox)
        self.assertIn("## Items", inbox)
        na = self.read("10-Action/11-next-actions.md")
        self.assertIn("@javis:auto · assigned 2026-10-18", na)
        self.assertIn("· assigned 2026-10-17 · done 2026-10-19", na)
        self.assertIn("- [x] y · một việc tên lạ", na)
        self.assertIn("- [ ] y · ghi chú này không phải log", self.read("10-Action/13-Projects/website.md"))
        turns = self.read("_log/turns.md")
        self.assertIn("] task · lập project", turns)
        self.assertIn("] idea · ghi ý", turns)
        self.assertIn("] drop · hỏi nhanh", turns)
        self.assertIn("] rejected · E2", self.read("_log/rejected.md"))

    def test_migrated_brain_works_and_migrate_is_idempotent(self):
        self.run_brain("migrate")
        code, out = self.run_brain("assigned")
        self.assertIn("1 · auto · Soạn email hỏi kế toán", out)
        code, out = self.run_brain("weekly")
        self.assertIn("| Turns in 7 days | 3 (task 1, idea 1, file 0, drop 1) |", out)
        self.assertIn("| Rejected at G1 in 7 days | 1 |", out)
        code, out = self.run_brain("migrate")
        self.assertEqual(code, 0)
        self.assertIn("Nothing to migrate", out)


if __name__ == "__main__":
    unittest.main()
