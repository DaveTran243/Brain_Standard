"""Test cho tools/brain.py. Chạy: python3 -m unittest discover -s tests"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

GOC_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOC_REPO / "tools"))
import brain  # noqa: E402

PHIEU = """---
nguon: https://example.org/bai
ngay_lay: 2026-10-20
luu_tru: https://web.archive.org/example
ma: {ma}
cach_kiem: "đối chiếu văn bản gốc"
---

# Một khẳng định do agent mang về
"""

PROJECT = """---
loai: project
trang_thai: active
bat_dau: 2026-10-01
ket_qua: "x"
tieu_chi_xong: "y"
tieu_chi_dung: "z"
{them}---

# Project
"""


class BoNaoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(GOC_REPO / "brain.toml", self.tmp / "brain.toml")
        shutil.copytree(GOC_REPO / "vault", self.tmp / "vault")
        self.vault = self.tmp / "vault"
        os.environ["BRAIN_NOW"] = "2026-10-20T21:30:00"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)
        os.environ.pop("BRAIN_NOW", None)

    def chay(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            ma = brain.main(["--root", str(self.tmp), *args])
        return ma, out.getvalue()

    def viet(self, rel: str, text: str) -> Path:
        p = self.vault / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p

    # ---- khung mẫu
    def test_vault_mau_sach(self):
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 0, out)
        self.assertIn("Vault sạch", out)

    # ---- ghi
    def test_ghi_vao_inbox(self):
        ma, _ = self.chay("ghi", "Đọc", "chương", "5")
        self.assertEqual(ma, 0)
        inbox = (self.vault / "00-Inbox/Inbox.md").read_text(encoding="utf-8")
        self.assertIn("- [2026-10-20 21:30] (tay) Đọc chương 5", inbox)

    # ---- K1
    def test_nop_thieu_phieu_bi_tra_lai(self):
        f = self.tmp / "muc.md"
        f.write_text("---\nnguon: https://x\nma: B2\n---\n# Khẳng định\n", encoding="utf-8")
        ma, out = self.chay("nop", str(f))
        self.assertEqual(ma, 2)
        self.assertIn("thiếu ngay_lay, luu_tru, cach_kiem", out)
        self.assertEqual(brain.cac_note(self.vault / "00-Inbox/agent"), [])

    def test_nop_ma_sai_dang(self):
        f = self.tmp / "muc.md"
        f.write_text(PHIEU.format(ma="G9"), encoding="utf-8")
        ma, _ = self.chay("nop", str(f))
        self.assertEqual(ma, 2)

    def test_nop_ma_loai_ghi_log(self):
        for ma_k1 in ("E1", "B5"):
            f = self.tmp / f"muc-{ma_k1}.md"
            f.write_text(PHIEU.format(ma=ma_k1), encoding="utf-8")
            ma, _ = self.chay("nop", str(f))
            self.assertEqual(ma, 3)
        log = (self.vault / "_log/k1.md").read_text(encoding="utf-8")
        self.assertIn("loại · E1", log)
        self.assertIn("loại · B5", log)
        self.assertEqual(brain.cac_note(self.vault / "00-Inbox/agent"), [])

    def test_nop_phan_loai(self):
        mong_doi = {"B2": "the", "A3": "literature", "C6": "literature", "D1": "fleeting", "F6": "fleeting"}
        for ma_k1, kq in mong_doi.items():
            self.assertEqual(brain.phan_loai(ma_k1, brain.MAC_DINH["kiem_duyet"]), kq, ma_k1)
        f = self.tmp / "muc.md"
        f.write_text(PHIEU.format(ma="D3"), encoding="utf-8")
        ma, out = self.chay("nop", str(f))
        self.assertEqual(ma, 0, out)
        (muc,) = brain.cac_note(self.vault / "00-Inbox/agent")
        fm, _ = brain.frontmatter(muc.read_text(encoding="utf-8"))
        self.assertEqual(fm["k1_toi_da"], "fleeting")
        self.assertEqual(fm["nhan"], "chua-kiem")
        self.assertIn("(agent) Một khẳng định do agent mang về · D3", (self.vault / "00-Inbox/Inbox.md").read_text(encoding="utf-8"))

    def test_kiem_bat_muc_agent_thieu_phieu(self):
        self.viet("00-Inbox/agent/tha-vao.md", "---\nnguon: https://x\n---\n# x\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 1)
        self.assertIn("K1 · 00-Inbox/agent/tha-vao.md", out)

    # ---- K2, K3, luật tri thức
    def test_k2_literature(self):
        self.viet("30-Knowledge/literature/a.md", "---\nloai: literature\nma: D2\n---\n- ý\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 1)
        self.assertIn("K2 · 30-Knowledge/literature/a.md: literature cần nguồn A–C", out)
        self.assertIn("thiếu bản lưu", out)

    def test_k3_va_link_permanent(self):
        self.viet("30-Knowledge/permanent/p1.md", "---\nid: 202610201200\nma: B3\n---\n# Một ý\nKhông có link.\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 1)
        self.assertIn("chưa nối tới note nào", out)
        self.assertIn("K3 · 30-Knowledge/permanent/p1.md: permanent cần tin 1–2", out)
        self.viet("30-Knowledge/permanent/p1.md", "---\nid: 202610201200\nma: B2\n---\n# Một ý\nNối [[p0]].\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 0, out)

    def test_fleeting_qua_7_ngay_canh_bao(self):
        self.viet("30-Knowledge/fleeting/y.md", "---\nngay: 2026-10-01\n---\nmột ý\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 0)
        self.assertIn("fleeting đã 19 ngày", out)

    def test_han_dung(self):
        self.assertEqual(str(brain.han_het("2027-04")), "2027-05-01")
        self.assertEqual(str(brain.han_het("2026-12")), "2027-01-01")
        self.viet("30-Knowledge/literature/cu.md", "---\nloai: literature\nhan_dung: 2026-09\n---\n- số liệu\n")
        _, out = self.chay("kiem")
        self.assertIn("quá hạn dùng (2026-09)", out)

    # ---- project và tầng thực thi
    def test_project_thieu_tieu_chi_la_loi(self):
        self.viet("10-Action/13-Projects/p.md", "---\ntrang_thai: active\nket_qua: x\n---\n")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 1)
        self.assertIn("thiếu tieu_chi_xong", out)
        self.assertIn("thiếu tieu_chi_dung", out)

    def test_milestone_khong_board_canh_bao(self):
        self.viet("10-Action/13-Projects/p.md", PROJECT.format(them='milestone: "M1"\n'))
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 0)
        self.assertIn("có milestone nhưng chưa có board", out)
        self.assertIn("chưa có việc nào", out)

    def test_khong_con_gioi_han_2_2(self):
        """2.2.0: 5 project active và 25 next action không sinh lỗi hay cảnh báo giới hạn."""
        dong = []
        for i in range(5):
            self.viet(f"10-Action/13-Projects/p{i}.md", PROJECT.format(them=f"board: https://example.org/b{i}\n"))
            dong += [f"- [ ] Làm việc {i}-{j} · [[p{i}]]" for j in range(5)]
        na = self.vault / "10-Action/11-next-actions.md"
        na.write_text(na.read_text(encoding="utf-8") + "\n".join(dong) + "\n", encoding="utf-8")
        ma, out = self.chay("kiem")
        self.assertEqual(ma, 0, out)
        self.assertIn("Vault sạch", out)
        ma, out = self.chay("turn", "viec", "nhiều", "project")
        self.assertEqual(ma, 0, out)
        s = brain.so_do(brain.mo_bo_nao(str(self.tmp)))
        self.assertEqual(s["project_active"], 5)
        self.assertEqual(s["next_mo"], 25)

    # ---- turn và weekly
    def test_turn_chan_khi_co_loi(self):
        self.viet("30-Knowledge/permanent/p.md", "---\nid: 1\n---\n# ý\n")
        ma, out = self.chay("turn", "y", "viết note")
        self.assertEqual(ma, 1)
        self.assertIn("Lượt chưa đóng được", out)
        self.assertFalse((self.vault / "_log/turns.md").exists())

    def test_turn_ghi_log(self):
        ma, out = self.chay("turn", "file", "mở category 51")
        self.assertEqual(ma, 0, out)
        self.assertIn("Bộ não: file · mở category 51", out)
        self.assertIn("- [2026-10-20 21:30] file · mở category 51", (self.vault / "_log/turns.md").read_text(encoding="utf-8"))

    def test_weekly(self):
        self.chay("ghi", "ý một")
        self.chay("turn", "y", "ghi ý")
        ma, out = self.chay("weekly", "--ghi")
        self.assertEqual(ma, 0, out)
        self.assertIn("Số đo · 2026-W43", out)
        self.assertIn("| Mục trong Inbox · cũ nhất (ngày) | 1 · 0 |", out)
        self.assertIn("| Lượt làm việc trong 7 ngày | 1 (viec 0, y 1, file 0, xoa 0) |", out)
        self.assertTrue((self.vault / "weekly/2026-W43.md").is_file())


if __name__ == "__main__":
    unittest.main()
