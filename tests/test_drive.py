"""The platform map: a root scanned into a graph of locations, incremental updates, datasets, JDex locations,
`brain where`, the prompt hook's [Brain Drive] lines, the drawing and the agent tools."""
from __future__ import annotations

import io
import json
import os
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import BrainTestCase  # noqa: E402

from brain import agent_tools, drawing, drive  # noqa: E402


class DriveTest(BrainTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.disk = self.tmp / "disk"
        repo = self.disk / "Code" / "invoice-bot"
        (repo / ".git").mkdir(parents=True)
        (repo / ".git" / "config").write_text('[remote "origin"]\n\turl = https://github.com/owner/invoice-bot\n',
                                              encoding="utf-8")
        (repo / "README.md").write_text("bot", encoding="utf-8")
        (repo / "node_modules").mkdir()
        (repo / "node_modules" / "x.js").write_text("x", encoding="utf-8")
        audio = self.disk / "Data" / "audio"
        audio.mkdir(parents=True)
        for i in range(6):
            (audio / f"a{i}.mp3").write_bytes(b"x" * 10)
        (self.disk / "Library" / "Thư viện").mkdir(parents=True)
        (self.disk / "Library" / "Thư viện" / "Principia.pdf").write_bytes(b"%PDF")
        (self.disk / "90-Archive" / "invoice-bot-old").mkdir(parents=True)
        (self.disk / "pagefile.sys").write_bytes(b"")
        root = str(self.disk).replace("\\", "/")
        toml = self.tmp / "brain.toml"
        toml.write_text(toml.read_text(encoding="utf-8") + f'\n[drive]\nenabled = true\nroot = "{root}"\nbulk_files = 5\n',
                        encoding="utf-8")
        index = "Code/50 System/50.00 Index (JDex).md"
        self.write(index, self.read(index).replace(
            "## Line format", f"## 51 Bots\n- 51.01 invoice-bot · location: Code/51 Bots/51.01 invoice-bot/ · note: "
                              f"{root}/Code/invoice-bot · status: in use\n\n## Line format"))
        (self.vault / "Code" / "51 Bots" / "51.01 invoice-bot").mkdir(parents=True)

    def k(self, *parts):
        return drive._key(self.disk.joinpath(*parts))

    def triples(self):
        return {(t["s"], t["p"], t["o"]) for t in drive.load(self.brain())}

    def test_scan(self):
        r = drive.scan(self.brain(), full=True)
        got = self.triples()
        self.assertIn((self.k("Code"), "contains", self.k("Code", "invoice-bot")), got)
        self.assertIn((self.k("Code", "invoice-bot"), "repo", "https://github.com/owner/invoice-bot"), got)
        self.assertIn((self.k("Data", "audio"), "is a", "dataset"), got)
        self.assertIn(("51.01 invoice-bot", "located at", self.k("Code", "invoice-bot")), got)
        self.assertFalse(any("node_modules" in s + o or o.endswith("pagefile.sys") for s, _, o in got))
        self.assertFalse(any(s.startswith("51.03") for s, _, _ in got))   # the template's example line
        self.assertEqual(r["datasets"], 1)

    def test_update_reads_only_changed_folders(self):
        b = self.brain()
        drive.scan(b, full=True)
        self.assertEqual(drive.scan(b)["read"], 0)
        new = self.disk / "Library" / "Thư viện" / "Ethics.pdf"
        new.write_bytes(b"%PDF")
        os.utime(new.parent, (time.time() + 2, time.time() + 2))
        self.assertEqual(drive.scan(b)["read"], 1)
        self.assertIn((self.k("Library", "Thư viện", "Ethics.pdf"), "is a", "document"), self.triples())

    def test_where_and_prompt(self):
        b = self.brain()
        drive.scan(b, full=True)
        self.assertEqual(drive.where(b, "invoice bot")[0]["path"], self.k("Code", "invoice-bot"))
        self.assertEqual(drive.where(b, "thu vien")[0]["path"], self.k("Library", "Thư viện"))
        self.assertTrue(drive.context(b, "open the invoice bot").startswith("[Brain Drive]"))
        self.assertEqual(drive.context(b, "good morning"), "")
        code, out = self.run_brain("where", "invoice", "--json")
        self.assertEqual((code, json.loads(out)[0]["path"]), (0, self.k("Code", "invoice-bot")))

    def test_off_by_default(self):
        (self.tmp / "brain.toml").write_text((self.tmp / "brain.toml").read_text(encoding="utf-8")
                                             .replace("enabled = true\nroot", "enabled = false\nroot"), encoding="utf-8")
        self.assertFalse(drive.enabled(self.brain()))
        code, _ = self.run_brain("where", "invoice")
        self.assertEqual(code, 1)

    def test_draw(self):
        b = self.brain()
        drive.scan(b, full=True)
        out = self.tmp / "map.html"
        self.assertGreater(drawing.write(b, out), 5)
        page = out.read_text(encoding="utf-8")
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn("<title>Platform Map</title>", page)

    def test_hooks(self):
        drive.scan(self.brain(), full=True)
        with mock_stdin(json.dumps({"prompt": "where is the invoice bot", "session_id": "s1"})):
            code, out = self.run_brain("hook", "prompt")
        self.assertEqual(code, 0)
        self.assertIn("[Brain Drive]", out)
        new = self.disk / "Code" / "invoice-bot" / "report.md"
        new.write_text("done", encoding="utf-8")
        os.utime(new.parent, (time.time() + 2, time.time() + 2))
        with mock_stdin(json.dumps({"session_id": "s1"})):
            self.run_brain("hook", "stop")
        self.assertIn((self.k("Code", "invoice-bot", "report.md"), "is a", "document"), self.triples())

    def test_paths_in_notes(self):
        f = drive.PATH_IN_TEXT.findall
        self.assertEqual(f("D:/Brain/bot (was D:/Project/bot)"), ["D:/Brain/bot", "D:/Project/bot"])
        self.assertEqual(f("/srv/brain/Code/bot · x"), ["/srv/brain/Code/bot"])
        self.assertEqual(f("see https://github.com/x/y, a/b and 5/10"), [])

    def test_agent_tools(self):
        names = {t["name"] for t in agent_tools.TOOLS}
        self.assertTrue({"brain_where", "brain_map_update"} <= names)
        self.assertEqual(agent_tools.BY_NAME["brain_where"]["argv"]({"query": "x"}), ["where", "x"])


class mock_stdin:
    def __init__(self, text: str):
        self.text = text

    def __enter__(self):
        self.old, sys.stdin = sys.stdin, io.StringIO(self.text)

    def __exit__(self, *exc):
        sys.stdin = self.old


if __name__ == "__main__":
    unittest.main()
