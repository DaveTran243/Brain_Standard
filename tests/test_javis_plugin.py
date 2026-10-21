"""Test cho plugin Javis OS ở integrations/javis/brain-standard. Chạy: python3 -m unittest discover -s tests"""
from __future__ import annotations

import importlib.util
import os
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GOC_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "brain_standard_plugin", GOC_REPO / "integrations" / "javis" / "brain-standard" / "plugin.py")
plugin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plugin)

PHIEU = """---
nguon: https://example.org/bai
ngay_lay: 2026-10-20
luu_tru: https://web.archive.org/example
ma: B2
cach_kiem: "đối chiếu văn bản gốc"
---

# Một khẳng định do agent mang về
"""


class Ctx:
    """Giả PluginContext của Javis: chỉ giữ thứ plugin dùng."""

    def __init__(self, vault_root: str) -> None:
        self.vault_root = vault_root
        self.tools: dict = {}
        self.hooks: dict = {}

    def register_tool(self, name, description, handler, schema=None, min_mode="readonly", **kw):
        self.tools[name] = {"handler": handler, "min_mode": min_mode}

    def register_hook(self, event, callback):
        self.hooks.setdefault(event, []).append(callback)

    def goi(self, ten: str, args: dict | None = None) -> str:
        return self.tools[ten]["handler"](args or {}, self)


class PluginTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(GOC_REPO / "brain.toml", self.tmp / "brain.toml")
        shutil.copytree(GOC_REPO / "vault", self.tmp / "vault")
        shutil.copytree(GOC_REPO / "tools", self.tmp / "tools")
        os.environ.pop("BRAIN_ROOT", None)
        os.environ["BRAIN_NOW"] = "2026-10-20T21:30:00"
        self.ctx = Ctx(str(self.tmp))
        plugin.register(self.ctx)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)
        os.environ.pop("BRAIN_NOW", None)

    def chan(self, path: str, tool: str = "javis_write_file") -> dict | None:
        return self.ctx.hooks["pre_tool_call"][0](tool_name=tool, args={"path": path},
                                                   mode="full", vault_root=str(self.tmp), turn=None)

    def test_dang_ky_du_tool_va_hook(self):
        self.assertEqual(set(self.ctx.tools), {"brain_ghi", "brain_nop", "brain_kiem", "brain_turn", "brain_weekly",
                                               "brain_viec_javis", "brain_xong"})
        self.assertNotIn("brain_giao", self.ctx.tools)
        self.assertEqual(self.ctx.tools["brain_kiem"]["min_mode"], "readonly")
        self.assertEqual(self.ctx.tools["brain_ghi"]["min_mode"], "safe")
        self.assertEqual(self.ctx.tools["brain_nop"]["min_mode"], "readonly")
        self.assertEqual(self.ctx.tools["brain_viec_javis"]["min_mode"], "readonly")
        self.assertEqual(self.ctx.tools["brain_xong"]["min_mode"], "readonly")
        self.assertIn("pre_tool_call", self.ctx.hooks)

    def test_ghi_vao_inbox(self):
        ra = self.ctx.goi("brain_ghi", {"noi_dung": "gọi lại kế toán", "kenh": "telegram"})
        self.assertIn("Đã ghi vào Inbox", ra)
        self.assertIn("(telegram) gọi lại kế toán", (self.tmp / "vault/00-Inbox/Inbox.md").read_text(encoding="utf-8"))

    def test_nop_duong_dan_tuong_doi(self):
        (self.tmp / "nhap").mkdir()
        (self.tmp / "nhap/phieu.md").write_text(PHIEU, encoding="utf-8")
        ra = self.ctx.goi("brain_nop", {"file": "nhap/phieu.md"})
        self.assertIn("K1 đạt", ra)

    def test_nop_tu_noi_dung_phieu(self):
        ra = self.ctx.goi("brain_nop", {"phieu": PHIEU, "ten": "giá máy in"})
        self.assertIn("K1 đạt", ra)
        muc = list((self.tmp / "vault/00-Inbox/agent").glob("*.md"))
        self.assertEqual(len(muc), 1)
        self.assertIn("ma: B2", muc[0].read_text(encoding="utf-8"))
        self.assertEqual(sorted(p.name for p in self.tmp.iterdir()), ["brain.toml", "tools", "vault"])

    def test_nop_tu_noi_dung_bi_loai(self):
        ra = self.ctx.goi("brain_nop", {"phieu": PHIEU.replace("ma: B2", "ma: E2")})
        self.assertIn("[mã thoát 3]", ra)
        self.assertEqual(list((self.tmp / "vault/00-Inbox/agent").glob("*.md")), [])

    def test_nop_khong_co_gi(self):
        self.assertTrue(self.ctx.goi("brain_nop", {}).startswith("ERROR"))

    def test_nop_thieu_phieu_bi_tra_lai(self):
        (self.tmp / "thieu.md").write_text("# không có phiếu\n", encoding="utf-8")
        ra = self.ctx.goi("brain_nop", {"file": "thieu.md"})
        self.assertIn("[mã thoát 2]", ra)
        self.assertIn("K1 trả lại", ra)

    def test_kiem_va_turn(self):
        self.assertIn("Vault sạch", self.ctx.goi("brain_kiem"))
        self.assertIn("Bộ não: y · thử plugin", self.ctx.goi("brain_turn", {"loai": "y", "tom_tat": "thử plugin"}))
        self.assertTrue(self.ctx.goi("brain_turn", {"loai": "sai", "tom_tat": "x"}).startswith("ERROR"))

    def test_khong_phai_bo_nao(self):
        ctx = Ctx(tempfile.mkdtemp())
        plugin.register(ctx)
        self.assertIn("không thấy brain.toml", ctx.goi("brain_kiem"))
        shutil.rmtree(ctx.vault_root)

    def test_hook_chan_permanent_mau_va_inbox_agent(self):
        self.assertIn("permanent", self.chan("vault/30-Knowledge/permanent/y-moi.md")["deny"])
        self.assertIn("K1", self.chan(str(self.tmp / "vault/00-Inbox/agent/x.md"))["deny"])
        self.assertIn("mẫu", self.chan("vault/_mau/phieu-nguon.md", "javis_edit_file")["deny"])
        self.assertIn("permanent", self.chan("vault/30-Knowledge/fleeting/../permanent/a.md")["deny"])

    def test_hook_cho_qua(self):
        self.assertIsNone(self.chan("vault/30-Knowledge/fleeting/y.md"))
        self.assertIsNone(self.chan("memory/facts/a.md"))
        self.assertIsNone(self.ctx.hooks["pre_tool_call"][0](
            tool_name="javis_read_file", args={"path": "vault/30-Knowledge/permanent/a.md"},
            vault_root=str(self.tmp)))


    def hook_claude(self, tool: str, path: str) -> subprocess.CompletedProcess:
        vao = json.dumps({"tool_name": tool, "tool_input": {"file_path": path}, "cwd": str(self.tmp)})
        return subprocess.run([sys.executable, str(GOC_REPO / "integrations/javis/chan_ghi_claude.py")],
                              input=vao, capture_output=True, text=True, encoding="utf-8")

    def test_hook_claude_code(self):
        r = self.hook_claude("Write", str(self.tmp / "vault/30-Knowledge/permanent/a.md"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("permanent", r.stderr)
        self.assertEqual(self.hook_claude("Edit", "vault/30-Knowledge/fleeting/a.md").returncode, 0)
        self.assertEqual(self.hook_claude("Read", "vault/30-Knowledge/permanent/a.md").returncode, 0)


    def them_viec(self, *dong: str) -> Path:
        p = self.tmp / "vault/10-Action/11-next-actions.md"
        p.write_text(p.read_text(encoding="utf-8") + "".join(f"{d}\n" for d in dong), encoding="utf-8")
        return p

    def test_viec_javis_va_xong(self):
        self.them_viec("- [ ] Tra giá máy in · @javis:suggest · giao 2026-10-20", "- [ ] Gửi báo giá · @javis:full")
        self.assertNotIn("Gửi báo giá", self.ctx.goi("brain_viec_javis", {"muc_toi_da": "suggest"}))
        ra = self.ctx.goi("brain_xong", {"so": 1, "ket_qua": "ba báo giá ở nhap/", "muc_toi_da": "suggest"})
        self.assertIn("Đã xong: Tra giá máy in", ra)
        self.assertIn("(javis) Kết quả", (self.tmp / "vault/00-Inbox/Inbox.md").read_text(encoding="utf-8"))
        self.assertTrue(self.ctx.goi("brain_xong", {"ket_qua": "x"}).startswith("ERROR"))

    def test_hook_chan_tu_gan_nhan(self):
        na = "vault/10-Action/11-next-actions.md"
        self.them_viec("- [ ] Gọi mẹ", "- [ ] Tra lịch · @javis:suggest · giao 2026-10-20")
        hook = self.ctx.hooks["pre_tool_call"][0]

        def goi(tool, **args):
            return hook(tool_name=tool, args={"path": na, **args}, vault_root=str(self.tmp))

        self.assertIn("brain giao", goi("javis_edit_file", old_string="- [ ] Gọi mẹ",
                                        new_string="- [ ] Gọi mẹ · @javis:auto")["deny"])
        self.assertIn("brain giao", goi("javis_edit_file", old_string="@javis:suggest", new_string="@javis:full")["deny"])
        cu = (self.tmp / na).read_text(encoding="utf-8")
        self.assertIn("brain giao", goi("javis_write_file", content=cu + "- [ ] Mới · @javis:auto\n")["deny"])
        self.assertIsNone(goi("javis_write_file", content=cu + "- [ ] Mới, không nhãn\n"))
        self.assertIsNone(goi("javis_edit_file", old_string="- [ ] Tra lịch", new_string="- [x] Tra lịch"))

    def test_hook_claude_code_chan_tu_gan_nhan(self):
        vao = json.dumps({"tool_name": "Edit", "cwd": str(self.tmp),
                          "tool_input": {"file_path": str(self.tmp / "vault/10-Action/11-next-actions.md"),
                                         "old_string": "## Việc", "new_string": "## Việc\n- [ ] X · @javis:full"}})
        r = subprocess.run([sys.executable, str(GOC_REPO / "integrations/javis/chan_ghi_claude.py")],
                           input=vao, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 2)
        self.assertIn("brain giao", r.stderr)

if __name__ == "__main__":
    unittest.main()
