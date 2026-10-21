#!/usr/bin/env python3
"""Hook PreToolUse cho Claude Code: cùng luật chặn với plugin brain-standard.

Engine Claude Code trong Javis (và Claude Code chạy thẳng trong repo) ghi file bằng tool riêng
Write/Edit, không đi qua MCP Hub của Javis, nên hook của plugin không thấy. Script này đọc JSON
của hook từ stdin; thoát mã 2 kèm lý do trên stderr thì Claude Code không ghi.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

TOOL_GHI = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

_spec = importlib.util.spec_from_file_location(
    "brain_standard_plugin", Path(__file__).resolve().parent / "brain-standard" / "plugin.py")
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)


def main() -> int:
    try:
        su_kien = json.load(sys.stdin)
    except ValueError:
        return 0
    if su_kien.get("tool_name") not in TOOL_GHI:
        return 0
    vao = su_kien.get("tool_input") or {}
    duong = vao.get("file_path") or vao.get("notebook_path") or ""
    args = {"path": duong}
    if "content" in vao:
        args["content"] = vao["content"]
    else:
        sua = vao.get("edits") or [vao]
        args["old_string"] = "\n".join(str(e.get("old_string") or "") for e in sua)
        args["new_string"] = "\n".join(str(e.get("new_string") or "") for e in sua)
    ly_do = plugin.ly_do_chan("javis_write_file", args, su_kien.get("cwd") or ".")
    if ly_do:
        print(ly_do, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
