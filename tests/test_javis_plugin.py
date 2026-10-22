"""Tests for the Javis OS plugin and the Claude Code hook. Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("brain_standard_plugin",
                                               REPO / "integrations/javis/brain-standard/plugin.py")
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)

RECORD = """---
source: https://example.org/article
retrieved: 2026-10-20
archived: https://web.archive.org/example
grade: B2
verification: "checked against the original"
---

# A claim brought in by an agent
"""


class FakeContext:
    """The parts of a Javis PluginContext the plugin uses."""

    def __init__(self, vault_root: str) -> None:
        self.vault_root = vault_root
        self.tools: dict = {}
        self.hooks: dict = {}

    def register_tool(self, name, description, handler, schema=None, min_mode="readonly", **kw):
        self.tools[name] = {"handler": handler, "min_mode": min_mode}

    def register_hook(self, event, callback):
        self.hooks.setdefault(event, []).append(callback)

    def call(self, name: str, args: dict | None = None) -> str:
        return self.tools[name]["handler"](args or {}, self)


class PluginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(REPO / "brain.toml", self.tmp / "brain.toml")
        shutil.copytree(REPO / "vault", self.tmp / "vault")
        shutil.copytree(REPO / "tools", self.tmp / "tools", ignore=shutil.ignore_patterns("__pycache__"))
        os.environ.pop(plugin.ROOT_ENV, None)
        os.environ["BRAIN_NOW"] = "2026-10-20T21:30:00"
        self.ctx = FakeContext(str(self.tmp))
        plugin.register(self.ctx)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)
        os.environ.pop("BRAIN_NOW", None)

    def inbox(self) -> str:
        return (self.tmp / "vault/00-Inbox/Inbox.md").read_text(encoding="utf-8")

    def add_tasks(self, *lines: str) -> Path:
        p = self.tmp / "vault/10-Action/11-next-actions.md"
        p.write_text(p.read_text(encoding="utf-8") + "".join(f"{line}\n" for line in lines), encoding="utf-8")
        return p

    def guard(self, path: str, tool: str = "javis_write_file", **extra) -> dict | None:
        return self.ctx.hooks["pre_tool_call"][0](tool_name=tool, args={"path": path, **extra},
                                                  mode="full", vault_root=str(self.tmp), turn=None)

    def test_registers_tools_and_hook(self):
        self.assertEqual(set(self.ctx.tools), {"brain_capture", "brain_submit", "brain_check", "brain_turn",
                                               "brain_weekly", "brain_assigned", "brain_report"})
        self.assertNotIn("brain_assign", self.ctx.tools)
        for name in ("brain_submit", "brain_check", "brain_weekly", "brain_assigned", "brain_report"):
            self.assertEqual(self.ctx.tools[name]["min_mode"], "readonly", name)
        for name in ("brain_capture", "brain_turn"):
            self.assertEqual(self.ctx.tools[name]["min_mode"], "safe", name)
        self.assertIn("pre_tool_call", self.ctx.hooks)

    def test_capture_uses_plugin_channel_from_config(self):
        out = self.ctx.call("brain_capture", {"text": "call the accountant"})
        self.assertIn("Captured to Inbox", out)
        self.assertIn("(javis) call the accountant", self.inbox())
        self.ctx.call("brain_capture", {"text": "buy milk", "channel": "telegram"})
        self.assertIn("(telegram) buy milk", self.inbox())

    def test_submit_from_record_text_leaves_no_file(self):
        out = self.ctx.call("brain_submit", {"record": RECORD, "name": "printer price"})
        self.assertIn("G1 passed", out)
        items = list((self.tmp / "vault/00-Inbox/agent").glob("*.md"))
        self.assertEqual(len(items), 1)
        self.assertIn("printer-price", items[0].name)
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["brain.toml", "tools", "vault"])

    def test_submit_rejected_and_returned(self):
        self.assertIn("[exit code 3]", self.ctx.call("brain_submit", {"record": RECORD.replace("B2", "E2")}))
        (self.tmp / "bare.md").write_text("# no record\n", encoding="utf-8")
        out = self.ctx.call("brain_submit", {"file": "bare.md"})
        self.assertIn("[exit code 2]", out)
        self.assertIn("G1 returned", out)
        self.assertTrue(self.ctx.call("brain_submit", {}).startswith("ERROR"))

    def test_check_turn_weekly(self):
        self.assertIn("Vault is clean", self.ctx.call("brain_check"))
        self.assertIn("Brain: idea · tried the plugin", self.ctx.call("brain_turn", {"type": "idea", "summary": "tried the plugin"}))
        self.assertIn("[exit code 2]", self.ctx.call("brain_turn", {"type": "viec", "summary": "x"}))
        self.assertIn("Metrics · 2026-W43", self.ctx.call("brain_weekly"))

    def test_assigned_and_report(self):
        self.add_tasks("- [ ] Compare printer prices · @javis:suggest · assigned 2026-10-20", "- [ ] Send the quote · @javis:full")
        self.assertNotIn("Send the quote", self.ctx.call("brain_assigned", {"max_level": "suggest"}))
        out = self.ctx.call("brain_report", {"number": 1, "result": "three quotes in drafts/", "max_level": "suggest"})
        self.assertIn("Done: Compare printer prices", out)
        self.assertIn("(javis) Result", self.inbox())
        self.assertTrue(self.ctx.call("brain_report", {"result": "x"}).startswith("ERROR"))

    def test_not_a_brain(self):
        ctx = FakeContext(tempfile.mkdtemp())
        plugin.register(ctx)
        self.assertIn("not a Brain_Standard repository", ctx.call("brain_check"))
        self.assertIsNone(ctx.hooks["pre_tool_call"][0](tool_name="javis_write_file", args={"path": "x.md"},
                                                         vault_root=ctx.vault_root))
        shutil.rmtree(ctx.vault_root)

    def test_guard_blocks_protected_paths(self):
        self.assertIn("permanent", self.guard("vault/30-Knowledge/permanent/new-idea.md")["deny"])
        self.assertIn("G1", self.guard(str(self.tmp / "vault/00-Inbox/agent/x.md"))["deny"])
        self.assertIn("Templates", self.guard("vault/_templates/source-record.md", "javis_edit_file")["deny"])
        self.assertIn("permanent", self.guard("vault/30-Knowledge/fleeting/../permanent/a.md")["deny"])

    def test_guard_lets_other_writes_through(self):
        self.assertIsNone(self.guard("vault/30-Knowledge/fleeting/idea.md"))
        self.assertIsNone(self.guard("memory/facts/a.md"))
        self.assertIsNone(self.guard("vault/30-Knowledge/permanent/a.md", "javis_read_file"))

    def test_guard_blocks_self_assignment(self):
        na = "vault/10-Action/11-next-actions.md"
        self.add_tasks("- [ ] Call mum", "- [ ] Look up the schedule · @javis:suggest · assigned 2026-10-20")
        self.assertIn("brain assign", self.guard(na, "javis_edit_file", old_string="- [ ] Call mum",
                                                 new_string="- [ ] Call mum · @javis:auto")["deny"])
        self.assertIn("brain assign", self.guard(na, "javis_edit_file", old_string="@javis:suggest",
                                                 new_string="@javis:full")["deny"])
        current = (self.tmp / na).read_text(encoding="utf-8")
        self.assertIn("brain assign", self.guard(na, content=current + "- [ ] New · @javis:auto\n")["deny"])
        self.assertIsNone(self.guard(na, content=current + "- [ ] New, no label\n"))
        self.assertIsNone(self.guard(na, "javis_edit_file", old_string="- [ ] Look up", new_string="- [x] Look up"))

    def test_guard_paths_from_config(self):
        (self.tmp / "brain.toml").write_text(
            '[brain]\nvault = "vault"\n[assistant.guard]\nprotected = ["permanent", "inbox_agent", "maps"]\n',
            encoding="utf-8")
        self.assertIn("reserved", self.guard("vault/40-Maps/moc.md")["deny"])


class ClaudeHookTest(PluginTest):
    def hook(self, event: dict) -> subprocess.CompletedProcess:
        script = self.tmp / "integrations/javis/claude_write_guard.py"
        script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / "integrations/javis/claude_write_guard.py", script)
        return subprocess.run([sys.executable, str(script)], input=json.dumps({"cwd": str(self.tmp), **event}),
                              capture_output=True, text=True, encoding="utf-8")

    def test_blocks_permanent_and_self_assignment(self):
        r = self.hook({"tool_name": "Write", "tool_input": {"file_path": str(self.tmp / "vault/30-Knowledge/permanent/a.md")}})
        self.assertEqual(r.returncode, 2)
        self.assertIn("permanent", r.stderr)
        r = self.hook({"tool_name": "Edit", "tool_input": {
            "file_path": str(self.tmp / "vault/10-Action/11-next-actions.md"),
            "old_string": "## Tasks", "new_string": "## Tasks\n- [ ] X · @javis:full"}})
        self.assertEqual(r.returncode, 2)
        self.assertIn("brain assign", r.stderr)

    def test_lets_other_tools_through(self):
        self.assertEqual(self.hook({"tool_name": "Edit", "tool_input": {
            "file_path": str(self.tmp / "vault/30-Knowledge/fleeting/a.md")}}).returncode, 0)
        self.assertEqual(self.hook({"tool_name": "Read", "tool_input": {
            "file_path": str(self.tmp / "vault/30-Knowledge/permanent/a.md")}}).returncode, 0)


if __name__ == "__main__":
    unittest.main()
