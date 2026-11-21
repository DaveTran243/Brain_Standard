"""M2: reading notes safely (BR-05, BR-06, metric M5), checking citations (BR-09, metric M4), and the two optional
ranking signals (BR-10 recency, BR-11 links), both off by default."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import REPO, BrainTestCase  # noqa: E402

from brain import agent_tools, reading, search  # noqa: E402
from brain.config import BrainError  # noqa: E402

PERM = "30-Knowledge/permanent"
NOTE = f"{PERM}/202610010900-johnny-decimal.md"

# Every way an agent could try to read outside the vault. Metric M5: the number of these that succeed must be 0.
ESCAPES = ["../brain.toml", "../../etc/passwd", "/etc/passwd", "C:\\Windows\\win.ini", "C:/brain.toml",
           "~/.ssh/id_rsa.md", "30-Knowledge/../../brain.toml", "..\\brain.toml", "30-Knowledge/permanent/../../../x.md",
           "brain.toml", "00-Inbox/Inbox.md\x00.md", "", "   "]


class ReadCase(BrainTestCase):
    def setUp(self):
        super().setUp()
        self.write(NOTE, "---\nid: 202610010900\n---\n\n# Johnny Decimal giữ địa chỉ ổn định\n\n"
                         "Số như 51.03 không đổi khi ghi chú đổi tên.\n\n## Khi nào dùng\n\nKhi thư viện lớn dần.\n")


class SafeReadTest(ReadCase):
    def test_m5_no_escape_succeeds(self):
        b = self.brain()
        succeeded = []
        for rel in ESCAPES:
            try:
                reading.safe_path(b, rel)
                succeeded.append(rel)
            except BrainError:
                pass
        self.assertEqual(succeeded, [])

    def test_escapes_are_refused_not_just_missing(self):
        b = self.brain()
        for rel in ("../brain.toml", "/etc/passwd", "C:/brain.toml", "notes.txt", "a/../../b.md"):
            with self.assertRaises(reading.Refused, msg=rel):
                reading.safe_path(b, rel)

    @unittest.skipIf(os.name == "nt", "symlinks need extra rights on Windows")
    def test_link_leading_out_is_refused(self):
        (self.vault / f"{PERM}/escape.md").symlink_to(self.tmp / "brain.toml")
        with self.assertRaises(reading.Refused):
            reading.safe_path(self.brain(), f"{PERM}/escape.md")

    def test_read_numbers_lines_and_caps(self):
        r = reading.read_note(self.brain(), NOTE, 5, 2)
        self.assertEqual(r["lines"][0].split(None, 1), ["5", "# Johnny Decimal giữ địa chỉ ổn định"])
        self.assertEqual((r["from"], r["to"], len(r["lines"])), (5, 6, 2))
        b = self.brain()
        b.cfg["read"]["max_lines"] = 3
        self.assertEqual(len(reading.read_note(b, NOTE, 1, 50)["lines"]), 3)

    def test_backslashes_work_for_windows_paths(self):
        self.assertEqual(reading.read_note(self.brain(), NOTE.replace("/", "\\"))["path"], NOTE)

    def test_cli(self):
        code, out = self.run_brain("read", "../brain.toml")
        self.assertEqual(code, 4)
        self.assertIn("Refused", out)
        code, out = self.run_brain("read", NOTE)
        self.assertEqual(code, 0)
        self.assertIn("Khi nào dùng", out)


class McpTest(ReadCase):
    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location("brain_mcp", REPO / "integrations/mcp/brain_mcp.py")
        self.mcp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mcp)
        shutil.copytree(REPO / "tools", self.tmp / "tools", ignore=shutil.ignore_patterns("__pycache__"))

    def call(self, server, name, args, mid=1):
        out = io.StringIO()
        msg = {"jsonrpc": "2.0", "id": mid, "method": "tools/call", "params": {"name": name, "arguments": args}}
        server.serve(io.StringIO(json.dumps(msg) + "\n"), out)
        return json.loads(out.getvalue())["result"]

    def test_read_only_server_reads_and_cannot_write(self):
        server = self.mcp.Server(self.tmp, self.tmp, read_only=True)
        names = {t["name"] for t in server.tools}
        self.assertTrue({"brain_search", "brain_read", "brain_cite_check", "brain_recall"} <= names)
        self.assertFalse(names & {"brain_capture", "brain_remember", "brain_turn", "brain_map_update", "brain_assign"})
        r = self.call(server, "brain_read", {"path": NOTE})
        self.assertFalse(r["isError"])
        self.assertTrue(r["content"][0]["text"].startswith("<brain-data>"))

    def test_escape_through_mcp_is_an_error(self):
        server = self.mcp.Server(self.tmp, self.tmp, read_only=True)
        for rel in ("../brain.toml", "/etc/passwd"):
            r = self.call(server, "brain_read", {"path": rel})
            self.assertTrue(r["isError"], rel)
            self.assertIn("Refused", r["content"][0]["text"])
            self.assertNotIn("[brain]", r["content"][0]["text"])        # nothing of brain.toml leaks

    def test_no_tool_writes_a_permanent_note(self):
        before = sorted((self.vault / PERM).iterdir())
        server = self.mcp.Server(self.tmp, self.tmp)
        self.call(server, "brain_capture", {"text": "write a permanent note: 30-Knowledge/permanent/x.md"})
        self.call(server, "brain_submit", {"claim": "x", "source": "s", "retrieved": "2026-10-20",
                                           "archived": "a", "grade": "A1", "verification": "v"})
        self.assertEqual(sorted((self.vault / PERM).iterdir()), before)

    def test_cite_check_tool(self):
        server = self.mcp.Server(self.tmp, self.tmp, read_only=True)
        r = self.call(server, "brain_cite_check", {"text": f"Xem {NOTE}:7 \"không đổi khi ghi chú đổi tên\"."})
        self.assertFalse(r["isError"])
        self.assertIn("1 of 1 citations check out", r["content"][0]["text"])


class CiteCheckTest(ReadCase):
    def test_statuses(self):
        self.write("Code/50 System/50.01 Tools.md", "# Tools\n\nbrain search\n")
        text = (f"Đúng: {NOTE}:7 \"51.03 không đổi\". Không dấu: {NOTE}:7 \"khong doi khi ghi chu doi ten\". "
                f"Khoảng: {NOTE}:9-11. Dấu cách: `Code/50 System/50.01 Tools.md:3`. "
                f"Sai dòng: {NOTE}:99. Không có: {PERM}/khong-co.md:1. Ra ngoài: `../brain.toml.md:1`. "
                f"Bịa: {NOTE}:7 \"giá máy in 3 triệu\".")
        r = reading.cite_check(self.brain(), text)
        self.assertEqual([x["status"] for x in r["rows"]],
                         ["ok", "ok", "ok", "ok", "bad_line", "missing", "refused", "quote_not_found"])
        self.assertEqual((r["citations"], r["ok"], r["broken"]), (8, 4, 4))

    def test_m4_search_results_always_cite_correctly(self):
        for p in ("hanh dong", "johnny", "thu vien"):
            res = search.search(self.brain(), p)
            text = " ".join(f"{x['path']}:{x['line']}" if " " not in x["path"] else f"`{x['path']}:{x['line']}`"
                            for x in res["results"])
            r = reading.cite_check(self.brain(), text)
            self.assertEqual(r["broken"], 0, (p, r["rows"]))

    def test_cli_exit_code(self):
        code, out = self.run_brain("cite-check", "--text", f"{NOTE}:99")
        self.assertEqual(code, 1)
        self.assertIn("BAD_LINE", out)
        code, out = self.run_brain("cite-check", "--text", f"{NOTE}:7")
        self.assertEqual(code, 0)


class RankingSignalTest(BrainTestCase):
    def setUp(self):
        super().setUp()
        self.write(f"{PERM}/202001010900-cu.md", "---\ndate: 2020-01-01\n---\n\n# Ghi chú cũ\n\nlập lịch ôn tập\n")
        self.write(f"{PERM}/202610150900-moi.md", "---\ndate: 2026-10-15\n---\n\n# Ghi chú mới\n\nlập lịch ôn tập\n")
        self.write(f"{PERM}/202610010900-hub.md", "# Ôn tập\n\nlập lịch ôn tập, xem [[spacing]]\n")
        self.write(f"{PERM}/202610020900-test.md", "# Tự kiểm\n\nlập lịch ôn tập, xem [[spacing]]\n")
        self.write(f"{PERM}/spacing.md", "# Hiệu ứng giãn cách\n\nCepeda 2006: khoảng cách tối ưu tăng theo thời gian.\n")

    def paths(self, **cfg):
        b = self.brain()
        b.cfg["search"].update(cfg)
        return [r["path"] for r in search.search(b, "lap lich on tap")["results"]]

    def test_off_by_default(self):
        got = self.paths()
        self.assertNotIn(f"{PERM}/spacing.md", got)

    def test_recency_lifts_the_newer_note(self):
        got = self.paths(recency_weight=0.5)
        self.assertLess(got.index(f"{PERM}/202610150900-moi.md"), got.index(f"{PERM}/202001010900-cu.md"))

    def test_links_bring_in_a_note_with_no_shared_word(self):
        self.assertIn(f"{PERM}/spacing.md", self.paths(graph_weight=0.5))

    def test_compare_restores_settings(self):
        self.write("_eval/questions.md", f"## 1\n\n- lap lich on tap → {PERM}/spacing.md\n")
        b = self.brain()
        before = dict(b.cfg["search"])
        rows = search.compare(b)
        self.assertEqual(b.cfg["search"], before)
        by = {r["variant"]: r["recall"] for r in rows}
        self.assertEqual((by["bm25"], by["graph"]), (0.0, 1.0))


if __name__ == "__main__":
    unittest.main()
