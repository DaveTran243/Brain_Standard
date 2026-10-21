"""Plugin Javis OS cho Bộ não 3.0 (Brain_Standard).

Hai việc:
1. Đưa lệnh `brain` thành tool cho MỌI engine của Javis, kể cả engine API không có shell.
   Tool chỉ gọi lại tools/brain.py của chính repo bộ não, nên luật nằm một chỗ.
   Javis thu bằng brain_ghi, brain_nop; làm tiếp bằng brain_viec_javis, brain_xong.
   Không có tool cho `brain giao`: chỉ chủ bộ não giao việc.
2. Hook pre_tool_call chặn AI ghi thẳng vào permanent note, file mẫu `_*.md` và 00-Inbox/agent,
   và chặn AI tự gắn hay nâng nhãn @javis trong Next Actions.

Brain trong Javis phải trỏ vào gốc repo bộ não (thư mục có brain.toml) hoặc một thư mục con
của nó. Chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

TOOL_GHI_FILE = ("javis_write_file", "javis_edit_file")
MAC_DINH = {"vault": "vault", "permanent": "30-Knowledge/permanent", "inbox_agent": "00-Inbox/agent",
            "next_actions": "10-Action/11-next-actions.md", "nhan": "@javis"}
MUC_JAVIS = ("suggest", "auto", "full")


def _goc(vault_root) -> Path | None:
    """Thư mục có brain.toml: BRAIN_ROOT nếu đặt, không thì đi ngược lên từ vault của Javis."""
    chi_dinh = os.environ.get("BRAIN_ROOT")
    if chi_dinh and (Path(chi_dinh) / "brain.toml").is_file():
        return Path(chi_dinh).resolve()
    if not vault_root:
        return None
    tu = Path(vault_root).resolve()
    for p in [tu, *tu.parents]:
        if (p / "brain.toml").is_file():
            return p
    return None


def _duong_dan(goc: Path) -> dict:
    try:
        with (goc / "brain.toml").open("rb") as f:
            cfg = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        cfg = {}
    dd = cfg.get("duong_dan", {})
    return {
        "vault": cfg.get("bo_nao", {}).get("vault", MAC_DINH["vault"]),
        "permanent": dd.get("permanent", MAC_DINH["permanent"]),
        "inbox_agent": dd.get("inbox_agent", MAC_DINH["inbox_agent"]),
        "next_actions": dd.get("next_actions", MAC_DINH["next_actions"]),
        "nhan": cfg.get("javis", {}).get("nhan", MAC_DINH["nhan"]),
    }


def _chay(ctx, *args: str) -> str:
    goc = _goc(getattr(ctx, "vault_root", None))
    if goc is None:
        return ("ERROR: brain đang chọn trong Javis không phải repo Brain_Standard (không thấy brain.toml). "
                "Trỏ brain vào gốc repo bộ não, hoặc đặt biến BRAIN_ROOT.")
    try:
        r = subprocess.run([sys.executable, str(goc / "tools" / "brain.py"), "--root", str(goc), *args],
                           cwd=str(goc), capture_output=True, text=True, encoding="utf-8", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"ERROR: không chạy được brain: {type(e).__name__}: {e}"
    ra = "\n".join(s for s in (r.stdout.strip(), r.stderr.strip()) if s)
    return f"[mã thoát {r.returncode}]\n{ra}" if r.returncode else ra


def _ghi(args, ctx):
    args = args or {}
    noi_dung = str(args.get("noi_dung") or "").strip()
    if not noi_dung:
        return "ERROR: cần 'noi_dung'."
    return _chay(ctx, "ghi", noi_dung, "--kenh", str(args.get("kenh") or "javis"))


def _nop(args, ctx):
    file = str((args or {}).get("file") or "").strip()
    if not file:
        return "ERROR: cần 'file' (đường dẫn tới phiếu nguồn .md)."
    p = Path(file)
    if not p.is_absolute() and getattr(ctx, "vault_root", None):
        p = Path(ctx.vault_root) / p
    return _chay(ctx, "nop", str(p))


def _kiem(args, ctx):
    return _chay(ctx, "kiem")


def _turn(args, ctx):
    args = args or {}
    loai = str(args.get("loai") or "").strip()
    tom_tat = str(args.get("tom_tat") or "").strip()
    if loai not in ("viec", "y", "file", "xoa") or not tom_tat:
        return "ERROR: cần 'loai' (viec, y, file, xoa) và 'tom_tat'."
    return _chay(ctx, "turn", loai, tom_tat)


def _weekly(args, ctx):
    return _chay(ctx, "weekly")


def _muc(args) -> list[str]:
    muc = str((args or {}).get("muc_toi_da") or "").strip()
    return ["--muc", muc] if muc in MUC_JAVIS else []


def _viec_javis(args, ctx):
    return _chay(ctx, "javis", *_muc(args))


def _xong(args, ctx):
    args = args or {}
    try:
        so = int(args.get("so"))
    except (TypeError, ValueError):
        return "ERROR: cần 'so' là số thứ tự trong brain_viec_javis."
    ket_qua = str(args.get("ket_qua") or "").strip()
    if not ket_qua:
        return "ERROR: cần 'ket_qua': một câu nói đã làm gì và kết quả nằm ở đâu."
    return _chay(ctx, "xong", str(so), ket_qua, *_muc(args))


def _dem_nhan(text: str, nhan: str) -> dict:
    """Số nhãn theo từng mức trong một đoạn chữ, ví dụ {'auto': 2, '': 1}."""
    dem: dict = {}
    for m in re.finditer(re.escape(nhan) + r"(?::([\w-]+))?(?![\w:-])", text or ""):
        dem[m.group(1) or ""] = dem.get(m.group(1) or "", 0) + 1
    return dem


def _them_nhan(cu: str, moi: str, nhan: str) -> bool:
    """True nếu đoạn mới có thêm nhãn ở một mức nào đó so với đoạn cũ (gắn mới hoặc nâng mức)."""
    a, b = _dem_nhan(cu, nhan), _dem_nhan(moi, nhan)
    return any(b[k] > a.get(k, 0) for k in b)


def ly_do_chan(tool_name: str, args: dict, vault_root) -> str | None:
    """Lý do chặn một lần ghi file, hoặc None nếu được ghi."""
    if not str(tool_name or "").endswith(TOOL_GHI_FILE):
        return None
    duong = str((args or {}).get("path") or "").strip()
    goc = _goc(vault_root)
    if not duong or goc is None:
        return None
    p = Path(duong)
    if not p.is_absolute():
        p = Path(vault_root) / p
    p = p.resolve()
    dd = _duong_dan(goc)
    vault = (goc / dd["vault"]).resolve()
    if not p.is_relative_to(vault):
        return None
    if p == (vault / dd["next_actions"]).resolve():
        a = args or {}
        if "content" in a:
            cu, moi = (p.read_text(encoding="utf-8") if p.is_file() else ""), str(a.get("content") or "")
        else:
            cu, moi = str(a.get("old_string") or ""), str(a.get("new_string") or "")
        if _them_nhan(cu, moi, dd["nhan"]):
            return (f"Bộ não 3.0: chỉ chủ bộ não giao việc cho Javis, bằng lệnh brain giao. AI không tự gắn "
                    f"hay nâng mức nhãn {dd['nhan']}. Đề xuất việc nên giao trong câu trả lời.")
        return None
    if p.is_relative_to((vault / dd["permanent"]).resolve()):
        return ("Bộ não 3.0: AI không viết permanent note thay chủ bộ não. Đề xuất nháp, câu hỏi "
                "và các note nên nối tới trong câu trả lời, để chủ bộ não tự viết.")
    if p.is_relative_to((vault / dd["inbox_agent"]).resolve()):
        return ("Bộ não 3.0: mục agent vào Inbox qua cổng K1. Viết phiếu nguồn ở chỗ khác "
                "rồi gọi tool brain_nop.")
    if any(phan.startswith("_") for phan in p.relative_to(vault).parts):
        # Mẫu (_mau-*.md, _mau/) và _log do CLI brain ghi, không phải AI.
        return ("Bộ não 3.0: không sửa file mẫu hay thư mục bắt đầu bằng '_'. "
                "Chép mẫu ra tên mới rồi mới điền; _log do lệnh brain tự ghi.")
    return None


def _chan_ghi(tool_name=None, args=None, vault_root=None, **kwargs):
    ly_do = ly_do_chan(tool_name, args or {}, vault_root)
    return {"deny": ly_do} if ly_do else None


def register(ctx):
    ctx.register_tool(
        name="brain_ghi",
        description=("Ghi lời của chủ bộ não vào Inbox (Bộ não 3.0). Đây là bước THU của Javis. Dùng cho tin bắt đầu bằng 'ghi:'. "
                     "Không dùng cho dữ kiện AI tự tra, thứ đó đi qua brain_nop."),
        handler=_ghi, min_mode="safe",
        schema={"type": "object",
                "properties": {"noi_dung": {"type": "string", "description": "Nội dung cần ghi"},
                               "kenh": {"type": "string", "description": "Kênh: javis, telegram, noi… (mặc định javis)"}},
                "required": ["noi_dung"]},
    )
    ctx.register_tool(
        name="brain_nop",
        description=("Nộp một phiếu nguồn do AI mang về qua cổng K1. File .md cần frontmatter nguon, ngay_lay, "
                     "luu_tru, ma (A–F + 1–6), cach_kiem theo vault/_mau/phieu-nguon.md. Không bịa mã."),
        handler=_nop, min_mode="safe",
        schema={"type": "object",
                "properties": {"file": {"type": "string", "description": "Đường dẫn tới file phiếu nguồn"}},
                "required": ["file"]},
    )
    ctx.register_tool(
        name="brain_kiem",
        description="Rà vault theo luật Bộ não 3.0 và các cổng K1–K3. Chỉ đọc.",
        handler=_kiem, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="brain_turn",
        description=("Đóng một lượt làm việc trong Bộ não 3.0. Vault còn lỗi thì lượt không đóng được: "
                     "chạy brain_kiem, sửa lỗi, rồi gọi lại."),
        handler=_turn, min_mode="safe",
        schema={"type": "object",
                "properties": {"loai": {"type": "string", "enum": ["viec", "y", "file", "xoa"]},
                               "tom_tat": {"type": "string", "description": "Một câu tóm tắt lượt"}},
                "required": ["loai", "tom_tat"]},
    )
    ctx.register_tool(
        name="brain_weekly",
        description="Số đo cho Weekly Review của Bộ não 3.0. Chỉ đọc; chủ bộ não lưu bằng brain weekly --ghi.",
        handler=_weekly, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="brain_viec_javis",
        description=("Liệt kê next action chủ bộ não đã giao cho Javis (nhãn @javis:<mức>), kèm số thứ tự và mức. "
                     "Chỉ làm việc có trong danh sách này. muc_toi_da = mức quyền của lượt đang chạy "
                     "(suggest, auto, full): chỉ trả việc ở mức đó trở xuống."),
        handler=_viec_javis, min_mode="readonly",
        schema={"type": "object",
                "properties": {"muc_toi_da": {"type": "string", "enum": list(MUC_JAVIS)}}},
    )
    ctx.register_tool(
        name="brain_xong",
        description=("Báo xong một việc được giao: đánh dấu xong trong Next Actions và ghi kết quả vào Inbox để chủ "
                     "bộ não làm rõ. 'so' là số thứ tự từ brain_viec_javis, gọi với cùng muc_toi_da. Dữ kiện tự tra "
                     "trong kết quả phải đã nộp qua brain_nop."),
        # readonly có chủ ý: chỗ ghi duy nhất là sổ sách của CLI (đánh dấu xong, một dòng Inbox), và
        # loop mức suggest cần nó để trả kết quả về Inbox. Hub chặn mọi ghi file khác ở mức đó.
        handler=_xong, min_mode="readonly",
        schema={"type": "object",
                "properties": {"so": {"type": "integer"},
                               "ket_qua": {"type": "string", "description": "Đã làm gì, kết quả ở đâu"},
                               "muc_toi_da": {"type": "string", "enum": list(MUC_JAVIS)}},
                "required": ["so", "ket_qua"]},
    )
    ctx.register_hook("pre_tool_call", _chan_ghi)
