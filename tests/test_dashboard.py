"""brain dashboard (ADR-20): the contract schema 1, the four golden signals, the picker, a read-only HTTP server on
127.0.0.1, and a page that still works when one source cannot be read."""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import BrainTestCase  # noqa: E402

from brain import config, dashboard  # noqa: E402

KEYS = {"schema", "version", "brain", "label", "at", "days", "signals", "series", "rules", "projects", "knowledge",
        "timeline", "errors_reading"}


class CollectTest(BrainTestCase):
    def test_contract_on_the_template_brain(self) -> None:
        d = dashboard.collect(self.brain())
        self.assertEqual(set(d), KEYS)
        self.assertEqual(d["schema"], 1)
        self.assertEqual(list(d["signals"]), ["traffic", "latency", "errors", "saturation"])
        for s in d["signals"].values():
            self.assertIn(s["level"], ("ok", "warn", "fail"))
            self.assertTrue({"headline", "caption", "rows", "sparks"} <= set(s))
        self.assertEqual(len(d["series"]["days"]), 30)
        self.assertEqual(d["series"]["days"][-1], "2026-10-20")
        self.assertEqual(d["errors_reading"], [])
        json.dumps(d, ensure_ascii=False)

    def test_capture_and_turns_count_and_traffic_is_never_coloured(self) -> None:
        self.run_brain("capture", "an idea for later")
        self.run_brain("turn", "task", "did a thing")
        d = dashboard.collect(self.brain())
        inbox = next(r for r in d["series"]["rows"] if r["key"] == "inbox")
        task = next(r for r in d["series"]["rows"] if r["key"] == "task")
        self.assertEqual(inbox["values"][-1], 1)
        self.assertEqual(task["values"][-1], 1)
        self.assertEqual(d["signals"]["traffic"]["level"], "ok")
        self.assertEqual(d["timeline"][0]["type"], "task")
        self.assertIn("did a thing", d["timeline"][0]["text"])

    def test_an_old_inbox_turns_latency_amber(self) -> None:
        self.run_brain("capture", "an old thought")
        os.environ[config.NOW_ENV] = "2026-11-05T09:00:00"
        d = dashboard.collect(self.brain())
        self.assertEqual(d["signals"]["latency"]["level"], "warn")
        row = d["signals"]["latency"]["rows"][0]
        self.assertEqual((row["value"], row["limit"], row["level"]), (16, 7, "warn"))

    def test_rules_carry_their_code_and_command(self) -> None:
        self.write("30-Knowledge/fleeting/old.md", "---\ndate: 2026-09-01\n---\nan old fleeting note\n")
        d = dashboard.collect(self.brain())
        kn = next(r for r in d["rules"] if r["code"] == "KN-03")
        self.assertEqual((kn["level"], kn["count"], kn["command"]), ("warning", 1, "brain check"))
        self.assertEqual(d["signals"]["errors"]["level"], "warn")

    def test_a_broken_source_leaves_the_rest(self) -> None:
        with mock.patch("brain.checks.check", side_effect=RuntimeError("boom")):
            d = dashboard.collect(self.brain())
        self.assertEqual(d["errors_reading"][0]["source"], "check")
        self.assertEqual(d["signals"]["errors"]["level"], "ok")
        self.assertIn("latency", d["signals"])

    def test_picker_lists_named_brains(self) -> None:
        other = self.tmp / "family"
        other.mkdir()
        (other / "brain.toml").write_text((self.tmp / "brain.toml").read_text(encoding="utf-8")
                                          + '\n[dashboard]\nname = "Family"\n', encoding="utf-8")
        (self.tmp / "brain.toml").write_text((self.tmp / "brain.toml").read_text(encoding="utf-8")
                                             + '\n[dashboard]\nbrains = ["family", "missing"]\n', encoding="utf-8")
        state = dashboard.State(self.brain())
        self.assertEqual([b["slug"] for b in state.list()], ["main", "family"])
        self.assertEqual(state.list()[1]["label"], "Family")
        self.assertIsNone(state.get("missing"))

    def test_cli_json_and_warn_host(self) -> None:
        code, out = self.run_brain("dashboard", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["schema"], 1)
        self.assertIsNone(dashboard.warn_host("127.0.0.1"))
        self.assertIn("other machines", dashboard.warn_host("0.0.0.0"))


class ServerTest(BrainTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.srv = dashboard.make_server(self.brain(), "127.0.0.1", 0)
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def get(self, path: str):
        with urllib.request.urlopen(self.base + path, timeout=10) as r:
            return r.status, r.headers, r.read().decode("utf-8")

    def code(self, path: str, method: str = "GET") -> int:
        req = urllib.request.Request(self.base + path, method=method, data=b"{}" if method != "GET" else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_page_and_api(self) -> None:
        status, headers, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertNotIn("__BOOT__", body)
        self.assertNotIn("<script src", body)          # self-contained: no outside script
        status, headers, body = self.get("/api/state")
        self.assertEqual(json.loads(body)["schema"], 1)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(self.get("/api/brains")[2])[0]["slug"], "main")
        self.assertTrue(json.loads(self.get("/healthz")[2])["ok"])

    def test_read_only(self) -> None:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            self.assertEqual(self.code("/api/state", method), 405)
        self.assertEqual(self.code("/api/state?brain=nope"), 404)
        self.assertEqual(self.code("/nothing"), 404)


if __name__ == "__main__":
    unittest.main()
