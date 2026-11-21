"""The script library (ADR-21): filing by topic, one variant per OS, the manifest, the log, the SC rules, the capture
hook, the agent tools and the code graph."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_brain import REPO, BrainTestCase  # noqa: E402

from brain import agent_tools, checks, kg, scripts  # noqa: E402
from brain.cli import main  # noqa: E402

LINUX = """#!/usr/bin/env bash
# Check whether a TCP port is open on a host
set -euo pipefail
host=${1:-localhost}; port=${2:-22}
if command -v nc >/dev/null; then nc -z -w 3 "$host" "$port" && echo open || echo closed; fi
"""
RHEL = """#!/usr/bin/env bash
# Open a firewall port permanently
sudo firewall-cmd --permanent --add-port="$1/tcp" && sudo firewall-cmd --reload
"""
PS1 = """<#
.SYNOPSIS
Check whether a TCP port is open on a host
#>
param([string]$HostName = "localhost", [int]$Port = 22)
$r = Test-NetConnection -ComputerName $HostName -Port $Port
if ($r.TcpTestSucceeded) { Write-Output "open" } else { Write-Output "closed" }
"""
NET = "Code/52 Scripts/52.02 network"


class ScriptsTest(BrainTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.gen = self.tmp / "generated"
        self.gen.mkdir()

    def file(self, name: str, text: str) -> Path:
        p = self.gen / name
        p.write_text(text, encoding="utf-8")
        return p

    def codes(self):
        errors, warnings = checks.check(self.brain())
        return [e.split(" ·")[0] for e in errors], [w.split(" ·")[0] for w in warnings], errors + warnings

    # ------------------------------------------------------------ filing
    def test_add_files_by_topic_with_jdex_line_first(self):
        code, out = self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)), "--by", "claude-code",
                                   "--prompt", "viết script kiểm tra port")
        self.assertEqual(code, 0, out)
        self.assertIn("52.02 network", out)
        self.assertIn("Still missing: rhel, macos, windows", out)
        self.assertTrue((self.vault / NET / "check-port.linux.sh").is_file())
        index = self.read("Code/50 System/50.00 Index (JDex).md")
        self.assertIn("## 52 Scripts\n- 52.02 network · location: Code/52 Scripts/52.02 network/ · status: in use", index)
        self.assertLess(index.index("## 52 Scripts"), index.index("## Line format"))
        man = self.read(f"{NET}/check-port.md")
        for want in ("type: script", "generated_by: claude-code", 'prompt: "viết script kiểm tra port"',
                     'purpose: "Check whether a TCP port is open on a host"', "os: linux", "| `check-port.linux.sh` |"):
            self.assertIn(want, man)
        log = self.read("_log/scripts.md")
        self.assertRegex(log, r"add · 52.02 network/check-port.linux.sh · sha256:[0-9a-f]{64} · by claude-code")

    def test_os_from_extension_and_commands(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        code, out = self.run_brain("script", "add", str(self.file("check-port.ps1", PS1)))
        self.assertIn("windows", out)
        code, out = self.run_brain("script", "add", str(self.file("open-port.sh", RHEL)))
        self.assertIn("open-port.rhel.sh", out)
        brew = self.file("install-tools.sh", "#!/bin/zsh\n# install developer tools\nbrew install git\n")
        code, out = self.run_brain("script", "add", str(brew))
        self.assertIn("install-tools.macos.sh", out)
        self.assertIn("52.05 dev-tools", out)

    def test_second_os_joins_the_same_script_and_topic(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        self.run_brain("script", "add", str(self.file("check-port.ps1", PS1)))
        s = scripts.find(self.brain(), "check-port")
        self.assertEqual(sorted(s.variants), ["linux", "windows"])
        code, out = self.run_brain("script", "add", str(self.file("x.sh", LINUX)), "--name", "check-port",
                                   "--os", "rhel", "--topic", "system")
        self.assertEqual(code, 2)
        self.assertIn("already filed under 52.02 network", out)

    def test_replace_needs_flag_and_same_content_is_noop(self):
        p = self.file("check-port.sh", LINUX)
        self.run_brain("script", "add", str(p))
        code, out = self.run_brain("script", "add", str(p))
        self.assertIn("Already saved", out)
        p.write_text(LINUX + "echo done\n", encoding="utf-8")
        code, out = self.run_brain("script", "add", str(p))
        self.assertEqual(code, 2)
        self.assertIn("--replace", out)
        code, out = self.run_brain("script", "add", str(p), "--replace")
        self.assertEqual(code, 0, out)
        self.assertIn("replace · 52.02 network/check-port.linux.sh", self.read("_log/scripts.md"))

    def test_unknown_topic_and_fallback(self):
        code, out = self.run_brain("script", "add", str(self.file("a.sh", "#!/bin/sh\necho hi\n")), "--topic", "cooking")
        self.assertEqual(code, 2)
        self.assertIn("52.02 network", out)
        code, out = self.run_brain("script", "add", str(self.file("hello.sh", "#!/bin/sh\necho hi\n")))
        self.assertIn("52.99 unsorted", out)
        self.assertIn("SC-08", self.codes()[1])
        code, out = self.run_brain("script", "move", "hello", "automation")
        self.assertEqual(code, 0, out)
        self.assertTrue((self.vault / "Code/52 Scripts/52.09 automation/hello.linux.sh").is_file())
        self.assertNotIn("SC-08", self.codes()[1])

    def test_stdin_save(self):
        out = io.StringIO()
        stdin = sys.stdin
        sys.stdin = io.TextIOWrapper(io.BytesIO(PS1.encode()))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                code = main(["--root", str(self.tmp), "script", "save", "--name", "check-port", "--os", "windows",
                             "--ext", "ps1"])
        finally:
            sys.stdin = stdin
        self.assertEqual(code, 0, out.getvalue())
        self.assertTrue((self.vault / NET / "check-port.windows.ps1").is_file())

    def test_wrong_extension_for_os(self):
        code, out = self.run_brain("script", "add", str(self.file("a.sh", LINUX)), "--os", "windows")
        self.assertEqual(code, 2)
        self.assertIn(".ps1", out)

    # ------------------------------------------------------------ rules
    def test_template_vault_and_full_script_are_clean(self):
        self.assertEqual([c for c in sum(self.codes()[:2], []) if c.startswith("SC")], [])
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        self.run_brain("script", "add", str(self.file("check-port.ps1", PS1)))
        self.run_brain("script", "add", str(self.file("x.sh", LINUX)), "--name", "check-port", "--os", "rhel")
        man = self.vault / NET / "check-port.md"
        man.write_text(man.read_text(encoding="utf-8").replace(
            "not_applicable: ", "not_applicable: macos: the owner has no Mac"), encoding="utf-8")
        errors, warnings, _ = self.codes()
        self.assertEqual(errors, [])
        self.assertFalse([w for w in warnings if w.startswith("SC")], self.codes()[2])
        self.assertIn("| macos · macOS (zsh, bash 3.2, BSD tools) | not applicable | the owner has no Mac |",
                      self.run_brain("script", "sync")[1] and self.read(f"{NET}/check-port.md"))

    def test_missing_variants_warn(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        _, warnings, text = self.codes()
        self.assertEqual(warnings.count("SC-03"), 3, text)

    def test_hand_edit_is_caught_and_synced(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        f = self.vault / NET / "check-port.linux.sh"
        f.write_text(LINUX + "echo edited\n", encoding="utf-8")
        self.assertIn("SC-05", self.codes()[1])
        code, out = self.run_brain("script", "sync")
        self.assertIn("recorded 52.02 network/check-port.linux.sh", out)
        self.assertNotIn("SC-05", self.codes()[1])
        self.assertIn("change · 52.02 network/check-port.linux.sh", self.read("_log/scripts.md"))

    def test_bad_names_nesting_and_missing_manifest(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        self.write(f"{NET}/random.sh", "#!/bin/sh\n")
        (self.vault / NET / "sub").mkdir()
        self.write(f"{NET}/orphan.linux.sh", "#!/bin/sh\necho x\n")
        errors, _, text = self.codes()
        self.assertEqual(errors.count("SC-02"), 2, text)
        self.assertIn("SC-01", errors)

    def test_topic_folder_without_jdex_line(self):
        self.write("Code/52 Scripts/52.03 storage-backup/backup.linux.sh", "#!/bin/sh\nrsync -a a b\n")
        self.assertIn("SC-04", self.codes()[0])

    def test_os_portability_lint(self):
        self.run_brain("script", "add", str(self.file("x.sh", "#!/bin/bash\n# update packages\napt-get update\n")),
                       "--name", "update-packages", "--os", "rhel")
        self.run_brain("script", "add", str(self.file("y.sh", "# free memory\nfree -h\n")), "--name", "mem",
                       "--os", "macos")
        _, warnings, text = self.codes()
        self.assertEqual(warnings.count("SC-07"), 2, text)
        self.assertIn("SC-06", warnings)       # no shebang

    # ------------------------------------------------------------ capture hook
    def hook(self, path: Path) -> str:
        out = io.StringIO()
        stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"session_id": "s1", "cwd": str(self.tmp), "tool_name": "Write",
                                            "tool_input": {"file_path": str(path)}}))
        try:
            with contextlib.redirect_stdout(out):
                main(["--root", str(self.tmp), "hook", "script"])
        finally:
            sys.stdin = stdin
        return out.getvalue()

    def test_hook_files_a_script_written_anywhere(self):
        out = self.hook(self.file("check-port.sh", LINUX))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("filed as Code/52 Scripts/52.02 network/check-port.linux.sh", ctx)
        self.assertIn("Still missing", ctx)
        self.assertIn("by claude-code", self.read("_log/scripts.md"))
        self.assertEqual(self.hook(self.file("check-port.sh", LINUX)), "")        # unchanged: nothing to say
        self.assertEqual(self.hook(self.file("notes.txt", "x")), "")             # not a script
        other = self.tmp / "other" / "check-port.sh"
        other.parent.mkdir()
        other.write_text(LINUX + "# another one\n", encoding="utf-8")
        self.assertIn("check-port-2.linux.sh", self.hook(other))               # same name, other origin

    def test_hook_records_a_direct_write_in_the_library(self):
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        f = self.vault / NET / "check-port.linux.sh"
        f.write_text(LINUX + "echo edited\n", encoding="utf-8")
        self.assertIn("recorded", self.hook(f))
        self.assertNotIn("SC-05", self.codes()[1])

    # ------------------------------------------------------------ agents
    def test_agent_tool_saves_and_lists(self):
        out = agent_tools.call(REPO, "brain_script_save", {"content": RHEL, "name": "Open Port", "os": "rhel",
                                                            "ext": "sh", "prompt": "mở port", "by": "codex"}, self.tmp)
        self.assertIn("open-port.rhel.sh", out)
        man = self.read(f"{NET}/open-port.md")
        self.assertIn("generated_by: codex", man)
        self.assertNotIn("origin_", man)
        listed = agent_tools.call(REPO, "brain_scripts", {"query": "firewall"}, self.tmp)
        self.assertIn("<brain-data>", listed)
        self.assertIn("open-port", listed)
        self.assertEqual(agent_tools.BY_NAME["brain_script_save"]["min_mode"], "safe")
        self.assertIn("required", agent_tools.call(REPO, "brain_script_save", {"content": "x"}, self.tmp))

    # ------------------------------------------------------------ code graph
    def test_commands_and_graph(self):
        self.assertEqual(scripts.commands(LINUX, ".sh"), {"nc"})
        self.assertEqual(scripts.commands(RHEL, ".sh"), {"firewall-cmd"})
        self.assertEqual(scripts.commands(PS1, ".ps1"), {"Test-NetConnection", "Write-Output"})
        self.assertEqual(scripts.imports("import os\nfrom pathlib import Path\n", ".py"), {"os", "pathlib"})
        self.run_brain("script", "add", str(self.file("check-port.sh", LINUX)))
        self.run_brain("script", "add", str(self.file("check-port.ps1", PS1)))
        self.run_brain("script", "add", str(self.file("open-port.sh", RHEL)))
        kg.build(self.brain())
        got = {(t["s"], t["p"], t["o"]) for t in kg.load(self.brain())}
        self.assertIn(("script check-port", "in topic", "52.02 network"), got)
        self.assertIn(("script check-port", "calls on windows", "test-netconnection"), got)
        self.assertIn(("script open-port", "calls on rhel", "firewall-cmd"), got)
        _, facts = kg.ask(self.brain(), "firewall-cmd")
        self.assertTrue(any(f["s"] == "script open-port" for f in facts))
        code, out = self.run_brain("script", "list", "--os", "windows")
        self.assertIn("check-port", out)
        self.assertNotIn("open-port", out)


if __name__ == "__main__":
    unittest.main()
