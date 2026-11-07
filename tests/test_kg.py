"""The knowledge graph, the turn hooks that read it before and update it after, and the MCP server.
Run: python3 -m unittest discover -s tests"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import REPO, BrainTestCase  # noqa: E402

from brain import kg, kgcore  # noqa: E402

PERMANENT = """---
id: 202610201430
type: permanent
links: ["[[202610191200-paging]]"]
tags: [inference]
---

# The KV cache decides the inference bill

Decoding uses memory bandwidth.
"""

LITERATURE = """---
type: literature
source: "vLLM paper · Kwon et al."
grade: B2
archived: https://web.archive.org/x
read_on: 2026-10-19
---

# vLLM paper

PagedAttention is a memory manager.
"""


class GraphTest(BrainTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.write("30-Knowledge/permanent/202610201430-kv-cache.md", PERMANENT)
        self.write("30-Knowledge/permanent/202610191200-paging.md",
                   "---\nid: 202610191200\nlinks: [\"[[202610201430-kv-cache]]\"]\n---\n\n# Paging stops memory waste\n")
        self.write("30-Knowledge/literature/vllm.md", LITERATURE)
        self.write("30-Knowledge/fleeting/groq.md", "---\nlabel: unverified\ngrade: D3\n---\n\nGroq is a chip maker.\n")

    def test_build_trust_and_templates_out(self):
        code, out = self.run_brain("kg", "build")
        self.assertEqual(code, 0, out)
        triples = kg.load(self.brain())
        trust = {t["s"]: t["trust"] for t in triples}
        self.assertEqual(trust["decoding"], "owner")
        self.assertEqual(trust["pagedattention"], "graded")
        self.assertEqual(trust["groq"], "unverified")
        self.assertIn(("kv cache decides the inference bill", "links to", "paging stops memory waste"),
                      {(t["s"], t["p"], t["o"]) for t in triples})
        self.assertFalse(any("template" in t["src"] for t in triples))
        self.assertIn("0 read again", self.run_brain("kg", "build")[1])
        self.assertIn("Vault is clean", self.run_brain("check")[1])

    def test_llm_extraction_falls_back(self):
        def chat(cfg, system, user):
            if "PagedAttention" in user:
                raise OSError("down")
            return '[{"subject": "kv cache", "predicate": "drives", "object": "inference bill"}]'
        r = kg.build(self.brain(), use_llm=True, chat=chat)
        self.assertEqual(r["llm_errors"], 1)
        self.assertTrue(any(t["method"] == "llm" for t in kg.load(self.brain())))

    def test_ask_suggest_export(self):
        self.run_brain("kg", "build")
        code, out = self.run_brain("kg", "ask", "what", "decides", "the", "inference", "bill?")
        self.assertIn("kv cache → decides → inference bill", out)
        self.assertIn("[permanent:202610201430-kv-cache · owner]", out)
        self.assertEqual(self.run_brain("kg", "suggest")[0], 0)
        self.assertEqual(self.run_brain("kg", "export", str(self.tmp / "g.json"))[0], 0)
        self.assertTrue(json.loads((self.tmp / "g.json").read_text(encoding="utf-8"))[0]["subject"])

    def hook(self, event: str, payload: dict) -> str:
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(sys, "stdout", out):
            from brain.cli import main
            self.assertEqual(main(["--root", str(self.tmp), "hook", event]), 0)
        return out.getvalue()

    def test_hooks_read_before_and_remember_after(self):
        self.run_brain("kg", "build")
        out = self.hook("prompt", {"session_id": "s1", "prompt": "What decides the inference bill?"})
        self.assertIn("[Brain KG]", out)
        self.run_brain("turn", "idea", "explained the kv cache and the inference bill")
        self.hook("stop", {"session_id": "s1"})
        mem = [t for t in kg.load(self.brain()) if t["kind"] == "memory"]
        self.assertIn(("mentions", "owner"), {(t["p"], t["trust"]) for t in mem})
        self.assertIn(("about", "agent"), {(t["p"], t["trust"]) for t in mem})
        n = len(kg.load(self.brain()))
        self.hook("stop", {"session_id": "s1"})
        self.assertEqual(len(kg.load(self.brain())), n)

    def test_hooks_never_fail_the_turn(self):
        self.assertEqual(self.hook("prompt", {"prompt": "anything"}), "")   # no graph yet: says nothing
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO("not json")), mock.patch.object(sys, "stdout", out):
            from brain.cli import main
            self.assertEqual(main(["--root", str(self.tmp), "hook", "stop"]), 0)


class MCPTest(BrainTestCase):
    def setUp(self) -> None:
        super().setUp()
        spec = importlib.util.spec_from_file_location("brain_mcp", REPO / "integrations/mcp/brain_mcp.py")
        self.mcp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mcp)
        shutil.copytree(REPO / "tools", self.tmp / "tools", ignore=shutil.ignore_patterns("__pycache__"))

    def rpc(self, server, *msgs):
        out = io.StringIO()
        server.serve(io.StringIO("".join(json.dumps(m) + "\n" for m in msgs)), out)
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_protocol(self):
        server = self.mcp.Server(self.tmp, self.tmp)
        r = self.rpc(server,
                     {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                     {"jsonrpc": "2.0", "method": "notifications/initialized"},
                     {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                     {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "brain_capture", "arguments": {"text": "ask about GPUs", "channel": "slack"}}},
                     {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                      "params": {"name": "brain_submit", "arguments": {
                          "claim": "Printer A costs 3 million", "source": "https://example.org", "retrieved": "2026-10-20",
                          "archived": "https://web.archive.org/x", "grade": "B2", "verification": "read it"}}},
                     {"jsonrpc": "2.0", "id": 5, "method": "nope"})
        self.assertEqual([m["id"] for m in r], [1, 2, 3, 4, 5])
        self.assertEqual(r[0]["result"]["serverInfo"]["name"], "brain-standard")
        names = {t["name"] for t in r[1]["result"]["tools"]}
        self.assertIn("brain_recall", names)
        self.assertNotIn("brain_assign", names)
        self.assertFalse(r[2]["result"]["isError"])
        self.assertIn("(slack) ask about GPUs", self.read("00-Inbox/Inbox.md"))
        self.assertFalse(r[3]["result"]["isError"], r[3])
        self.assertEqual(len(self.agent_items()), 1)
        self.assertEqual(r[4]["error"]["code"], -32601)

    def test_read_only(self):
        server = self.mcp.Server(self.tmp, self.tmp, read_only=True)
        r = self.rpc(server, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertNotIn("brain_capture", {t["name"] for t in r[0]["result"]["tools"]})


class CoreTest(unittest.TestCase):
    def test_same_core_as_second_brain(self):
        """kgcore is portable: one file, the same in every brain."""
        self.assertIn("Portable on purpose", (REPO / "tools/brain/kgcore.py").read_text(encoding="utf-8"))
        self.assertEqual(kgcore.norm("Nguồn đọc lớn (Claude viết)"), "nguồn đọc lớn (claude viết)")


if __name__ == "__main__":
    unittest.main()
