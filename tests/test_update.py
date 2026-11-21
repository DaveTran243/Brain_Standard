"""bin/update_brain.py: a brain is updated from the standard, its notes and settings untouched, and rolled back when
the update does not work on the machine."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("update_brain", REPO / "bin/update_brain.py")
ub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ub)

IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".brain", "*.pyc")
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.org", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.org", "GIT_CONFIG_NOSYSTEM": "1"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def copy_standard(dest: Path) -> None:
    dest.mkdir(parents=True)
    for name in ("tools", "docs", "bin", "tests", "integrations", "vault"):
        shutil.copytree(REPO / name, dest / name, ignore=IGNORE)
    for name in ("CHANGELOG.md", "brain.toml"):
        shutil.copy(REPO / name, dest / name)


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, GIT_ENV)
        self.env.start()
        self.tmp = Path(tempfile.mkdtemp())
        self.std, self.brain = self.tmp / "standard", self.tmp / "brain"
        copy_standard(self.std)
        git(self.std, "init", "-q", "-b", "main")
        git(self.std, "add", "-A")
        git(self.std, "commit", "-q", "-m", "standard")
        self.new = ub.version_of((self.std / "tools/brain/defaults.toml").read_text(encoding="utf-8"))

        # A brain on an older version: an old version number, a module the standard has since added is missing,
        # its own notes, its own AGENTS.md, no eval questions yet.
        copy_standard(self.brain)
        d = self.brain / "tools/brain/defaults.toml"
        d.write_text(d.read_text(encoding="utf-8").replace(f'version = "{self.new}"', 'version = "4.3.0"'),
                     encoding="utf-8")
        (self.brain / "tools/brain/reading.py").unlink()
        shutil.rmtree(self.brain / "vault/_eval")
        (self.brain / "vault/AGENTS.md").write_text("# My own rules\n", encoding="utf-8")
        (self.brain / "vault/30-Knowledge/permanent/202611010900-mine.md").write_text("# Mine\n\nmy note\n",
                                                                                     encoding="utf-8")
        (self.brain / "brain.toml").write_text((self.brain / "brain.toml").read_text(encoding="utf-8")
                                               + "\n# my setting\n", encoding="utf-8")
        git(self.brain, "init", "-q", "-b", "main")
        git(self.brain, "add", "-A")
        git(self.brain, "commit", "-q", "-m", "my brain")
        self.head = git(self.brain, "rev-parse", "HEAD")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_update(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = ub.main(["--brain", str(self.brain), "--standard", str(self.std), *args])
        return code, out.getvalue()

    def version(self) -> str:
        return ub.version_of((self.brain / "tools/brain/defaults.toml").read_text(encoding="utf-8"))

    def test_update_replaces_only_the_standard_paths(self):
        code, out = self.run_update()
        self.assertEqual(code, 0, out)
        self.assertIn(f"4.3.0 → {self.new}", out)
        self.assertEqual(self.version(), self.new)
        self.assertTrue((self.brain / "tools/brain/reading.py").is_file())
        self.assertTrue((self.brain / "vault/_eval/questions.md").is_file())
        self.assertEqual((self.brain / "vault/AGENTS.md").read_text(encoding="utf-8"), "# My own rules\n")
        self.assertIn("kept yours", out)
        self.assertTrue((self.brain / "vault/30-Knowledge/permanent/202611010900-mine.md").is_file())
        self.assertIn("# my setting", (self.brain / "brain.toml").read_text(encoding="utf-8"))
        self.assertIn(".brain/", (self.brain / ".gitignore").read_text(encoding="utf-8"))
        self.assertIn("Not committed", out)
        self.assertEqual(git(self.brain, "rev-parse", "HEAD"), self.head)

    def test_commit_and_second_run_is_current(self):
        code, out = self.run_update("--commit")
        self.assertEqual(code, 0, out)
        self.assertEqual(git(self.brain, "log", "-1", "--format=%s"), f"Update Brain_Standard 4.3.0 → {self.new}")
        self.assertEqual(git(self.brain, "status", "--porcelain", "--", *ub.PATHS), "")
        code, out = self.run_update()
        self.assertEqual(code, 0)
        self.assertIn("Already up to date", out)

    def test_update_agents_on_request(self):
        code, out = self.run_update("--update-agents")
        self.assertEqual(code, 0, out)
        self.assertEqual((self.brain / "vault/AGENTS.md").read_text(encoding="utf-8").strip(),
                         (self.std / "vault/AGENTS.md").read_text(encoding="utf-8").strip())

    def test_dry_run_changes_nothing(self):
        code, out = self.run_update("--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("Dry run", out)
        self.assertEqual(self.version(), "4.3.0")
        self.assertEqual(git(self.brain, "status", "--porcelain"), "")

    def test_refuses_to_overwrite_uncommitted_work(self):
        (self.brain / "tools/brain/notes.py").write_text("# my edit\n", encoding="utf-8")
        code, out = self.run_update()
        self.assertEqual(code, 2)
        self.assertIn("uncommitted changes", out)
        self.assertEqual((self.brain / "tools/brain/notes.py").read_text(encoding="utf-8"), "# my edit\n")

    def test_failed_verification_rolls_everything_back(self):
        with mock.patch.object(ub, "verify", return_value=["the standard's tests fail: FAILED (failures=1)"]):
            code, out = self.run_update()
        self.assertEqual(code, 1)
        self.assertIn("Rolled back to 4.3.0", out)
        self.assertEqual(self.version(), "4.3.0")
        self.assertFalse((self.brain / "tools/brain/reading.py").exists())     # a file the update added is gone
        self.assertFalse((self.brain / "vault/_eval").exists())
        self.assertEqual(git(self.brain, "status", "--porcelain", "--", *ub.PATHS, "vault"), "")

    def test_verify_checks_the_cli_version(self):
        code, _ = self.run_update()
        self.assertEqual(ub.verify(self.brain, self.new, run_tests=False), [])
        self.assertTrue(ub.verify(self.brain, "9.9.9", run_tests=False))

    def test_standard_tests_run_in_a_copy_not_in_the_brain(self):
        self.run_update()
        seen = {}
        real = subprocess.run

        def fake_run(cmd, cwd=None, **kw):
            if cmd[0] == "git":
                return real(cmd, cwd=cwd, **kw)
            seen["cwd"] = Path(cwd)
            seen["has_tests"] = (Path(cwd) / "tests").is_dir() and (Path(cwd) / "vault/AGENTS.md").is_file()
            seen["agents"] = (Path(cwd) / "vault/AGENTS.md").read_text(encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "Ran 1 test\n\nOK")
        with mock.patch.object(ub.subprocess, "run", side_effect=fake_run):
            self.assertEqual(ub.standard_tests(self.brain), [])
        self.assertNotEqual(seen["cwd"], self.brain)
        self.assertTrue(seen["has_tests"])
        self.assertNotEqual(seen["agents"], "# My own rules\n")        # the standard's template, not this brain

    def test_not_a_brain(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = ub.main(["--brain", str(self.tmp), "--standard", str(self.std)])
        self.assertEqual(code, 2)
        self.assertIn("No brain.toml", out.getvalue())


class DesktopConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = self.tmp / "Claude" / "claude_desktop_config.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_adds_read_only_server_and_keeps_others(self):
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}), encoding="utf-8")
        msg = ub.mcp_desktop(Path("/b"), write=False, dry=False, path=self.cfg)
        data = json.loads(self.cfg.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["other"], {"command": "x"})
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["mcpServers"]["brain"]["args"][-1], "--read-only")
        self.assertTrue(list(self.cfg.parent.glob("*.bak")))
        self.assertIn("Restart Claude Desktop", msg)
        self.assertIn("already set", ub.mcp_desktop(Path("/b"), write=False, dry=False, path=self.cfg))

    def test_new_file_write_mode_and_dry_run(self):
        self.assertIn("would set", ub.mcp_desktop(Path("/b"), write=True, dry=True, path=self.cfg))
        self.assertFalse(self.cfg.exists())
        ub.mcp_desktop(Path("/b"), write=True, dry=False, path=self.cfg)
        self.assertNotIn("--read-only", json.loads(self.cfg.read_text(encoding="utf-8"))["mcpServers"]["brain"]["args"])

    def test_broken_json_is_left_alone(self):
        self.cfg.parent.mkdir(parents=True)
        self.cfg.write_text("{not json", encoding="utf-8")
        self.assertIn("not valid JSON", ub.mcp_desktop(Path("/b"), write=False, dry=False, path=self.cfg))
        self.assertEqual(self.cfg.read_text(encoding="utf-8"), "{not json")


if __name__ == "__main__":
    unittest.main()
