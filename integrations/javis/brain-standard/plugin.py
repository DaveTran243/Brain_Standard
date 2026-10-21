"""Plugin Javis OS cho Bộ não 2.2 (Brain_Standard).

Hai việc:
1. Đưa lệnh `brain` thành tool cho MỌI engine của Javis, kể cả engine API không có shell.
   Tool chỉ gọi lại tools/brain.py của chính repo bộ não, nên luật nằm một chỗ.
2. Hook pre_tool_call chặn AI ghi thẳng vào permanent note, file mẫu `_*.md` và 00-Inbox/agent.
   Mục agent phải vào bằng brain_nop để qua cổng K1.

Brain trong Javis phải trỏ vào gốc repo bộ não (thư mục có brain.toml) hoặc một thư mục con
của nó. Chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tomllib
from pathlib import Path

TOOL_GHI_FILE = ("javis_write_file", "javis_edit_file")
MAC_DINH = {"vault": "vault", "permanent": "30-Knowledge/permanent", "inbox_agent": "00-Inbox/agent"}


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
    if p.is_relative_to((vault / dd["permanent"]).resolve()):
        return ("Bộ não 2.2: AI không viết permanent note thay chủ bộ não. Đề xuất nháp, câu hỏi "
                "và các note nên nối tới trong câu trả lời, để chủ bộ não tự viết.")
    if p.is_relative_to((vault / dd["inbox_agent"]).resolve()):
        return ("Bộ não 2.2: mục agent vào Inbox qua cổng K1. Viết phiếu nguồn ở chỗ khác "
                "rồi gọi tool brain_nop.")
    if any(phan.startswith("_") for phan in p.relative_to(vault).parts):
        # Mẫu (_mau-*.md, _mau/) và _log do CLI brain ghi, không phải AI.
        return ("Bộ não 2.2: không sửa file mẫu hay thư mục bắt đầu bằng '_'. "
                "Chép mẫu ra tên mới rồi mới điền; _log do lệnh brain tự ghi.")
    return None


def _chan_ghi(tool_name=None, args=None, vault_root=None, **kwargs):
    ly_do = ly_do_chan(tool_name, args or {}, vault_root)
    return {"deny": ly_do} if ly_do else None


def register(ctx):
    ctx.register_tool(
        name="brain_ghi",
        description=("Ghi lời của chủ bộ não vào Inbox (Bộ não 2.2). Dùng cho tin bắt đầu bằng 'ghi:'. "
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
        description="Rà vault theo luật Bộ não 2.2 và các cổng K1–K3. Chỉ đọc.",
        handler=_kiem, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_tool(
        name="brain_turn",
        description=("Đóng một lượt làm việc trong Bộ não 2.2. Vault còn lỗi thì lượt không đóng được: "
                     "chạy brain_kiem, sửa lỗi, rồi gọi lại."),
        handler=_turn, min_mode="safe",
        schema={"type": "object",
                "properties": {"loai": {"type": "string", "enum": ["viec", "y", "file", "xoa"]},
                               "tom_tat": {"type": "string", "description": "Một câu tóm tắt lượt"}},
                "required": ["loai", "tom_tat"]},
    )
    ctx.register_tool(
        name="brain_weekly",
        description="Số đo cho Weekly Review của Bộ não 2.2. Chỉ đọc; chủ bộ não lưu bằng brain weekly --ghi.",
        handler=_weekly, min_mode="readonly",
        schema={"type": "object", "properties": {}},
    )
    ctx.register_hook("pre_tool_call", _chan_ghi)
