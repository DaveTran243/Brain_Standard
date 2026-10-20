#!/usr/bin/env python3
"""brain · CLI cho Brain_Standard 2.2.

Lệnh:
  ghi "…"                       ghi lời bạn vào Inbox (không qua K1)
  nop <file.md>                 nộp mục do agent mang về qua cổng K1
  kiem                          rà vault theo luật 2.2 và cổng K2–K3
  turn <viec|y|file|xoa> "…"    đóng một lượt làm việc
  weekly [--ghi]                số đo cho Weekly Review

Chỉ dùng thư viện chuẩn, cần Python 3.11 trở lên. Thời điểm hiện tại có thể đặt
bằng biến môi trường BRAIN_NOW (ISO 8601), dùng cho test.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

PHIEN_BAN = "2.2.0"
MA_RE = re.compile(r"^([A-F])([1-6])$")
DONG_INBOX_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?\]")
LINK_RE = re.compile(r"\[\[[^\]]+\]\]")
LOAI_TURN = ("viec", "y", "file", "xoa")
TRANG_THAI = ("someday", "active", "done", "stopped")
NHAN_K1 = {"the": "thẻ ôn", "literature": "literature", "fleeting": "fleeting (chưa kiểm)"}

MAC_DINH = {
    "bo_nao": {"phien_ban": PHIEN_BAN, "vault": "vault"},
    "duong_dan": {
        "inbox": "00-Inbox/Inbox.md",
        "inbox_agent": "00-Inbox/agent",
        "next_actions": "10-Action/11-next-actions.md",
        "waiting_for": "10-Action/12-waiting-for.md",
        "projects": "10-Action/13-Projects",
        "someday": "10-Action/14-someday.md",
        "fleeting": "30-Knowledge/fleeting",
        "literature": "30-Knowledge/literature",
        "permanent": "30-Knowledge/permanent",
        "maps": "40-Maps",
        "weekly": "weekly",
        "log": "_log",
    },
    "lam_ro": {"fleeting_toi_da_ngay": 7, "moc_khi_du_note": 7},
    "nhip": {"vong_ngay_chon_toi_da": 3},
    "kiem_duyet": {
        "chan_cung": True,
        "truong_bat_buoc": ["nguon", "ngay_lay", "luu_tru", "ma", "cach_kiem"],
        "loai_nguon": ["E"],
        "loai_tin": [5],
        "chi_toi_fleeting": ["D", "F"],
        "literature_nguon": ["A", "B", "C"],
        "permanent_tin": [1, 2],
        "the_tin": [1, 2],
    },
    "thuc_thi": {"canh_bao_milestone_khong_board": True, "canh_bao_project_khong_viec": True},
}


# ---------------------------------------------------------------- tiện ích


def bay_gio() -> dt.datetime:
    gia_tri = os.environ.get("BRAIN_NOW")
    if gia_tri:
        return dt.datetime.fromisoformat(gia_tri)
    return dt.datetime.now().replace(microsecond=0)


def gop(mac_dinh: dict, rieng: dict) -> dict:
    kq = {k: (dict(v) if isinstance(v, dict) else v) for k, v in mac_dinh.items()}
    for k, v in rieng.items():
        if isinstance(v, dict) and isinstance(kq.get(k), dict):
            kq[k] = {**kq[k], **v}
        else:
            kq[k] = v
    return kq


def doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def ghi_them(p: Path, dong: str, dau_file: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    moi = not p.exists()
    with p.open("a", encoding="utf-8", newline="\n") as f:
        if moi and dau_file:
            f.write(dau_file)
        f.write(dong)


def _gia_tri(v: str) -> str:
    v = v.strip()
    if v[:1] in ('"', "'"):
        cuoi = v.find(v[0], 1)
        if cuoi != -1:
            return v[1:cuoi]
    return re.split(r"\s+#", v, maxsplit=1)[0].strip()


def frontmatter(text: str) -> tuple[dict, str]:
    """Đọc frontmatter dạng `khoá: giá trị` giữa hai dòng ---. Trả về (fm, thân)."""
    dong = text.splitlines()
    if not dong or dong[0].strip() != "---":
        return {}, text
    fm: dict[str, str] = {}
    for i in range(1, len(dong)):
        s = dong[i].strip()
        if s == "---":
            return fm, "\n".join(dong[i + 1 :])
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        fm[k.strip()] = _gia_tri(v)
    return {}, text


def them_vao_frontmatter(text: str, cap: dict[str, str]) -> str:
    dong = text.splitlines()
    if not dong or dong[0].strip() != "---":
        dau = ["---", *(f"{k}: {v}" for k, v in cap.items()), "---"]
        return "\n".join(dau + dong) + "\n"
    for i in range(1, len(dong)):
        if dong[i].strip() == "---":
            moi = dong[:i] + [f"{k}: {v}" for k, v in cap.items()] + dong[i:]
            return "\n".join(moi) + "\n"
    return text


def tieu_de(body: str, du_phong: str) -> str:
    for d in body.splitlines():
        if d.startswith("# "):
            return d[2:].strip()
    return du_phong


def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60] or "muc"


def han_het(gia_tri: str) -> dt.date | None:
    """Ngày bắt đầu hết hạn. YYYY-MM-DD hết sau ngày đó; YYYY-MM hết sau tháng đó."""
    gia_tri = (gia_tri or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", gia_tri):
            return dt.date.fromisoformat(gia_tri) + dt.timedelta(days=1)
        if re.fullmatch(r"\d{4}-\d{2}", gia_tri):
            nam, thang = map(int, gia_tri.split("-"))
            return dt.date(nam + (thang == 12), thang % 12 + 1, 1)
    except ValueError:
        return None
    return None


def ngay_cua(p: Path, fm: dict) -> dt.date:
    for khoa in ("ngay", "doc_ngay", "ngay_lay", "bat_dau"):
        try:
            return dt.date.fromisoformat(fm.get(khoa, "")[:10])
        except ValueError:
            pass
    m = re.match(r"(\d{4})(\d{2})(\d{2})", fm.get("id", "") or p.name)
    if m:
        try:
            return dt.date(*map(int, m.groups()))
        except ValueError:
            pass
    return dt.date.fromtimestamp(p.stat().st_mtime)


def cac_note(thu_muc: Path) -> list[Path]:
    if not thu_muc.is_dir():
        return []
    return sorted(p for p in thu_muc.rglob("*.md") if not p.name.startswith("_"))


def phan_loai(ma: str, kd: dict) -> str:
    """K1: trả về 'the', 'literature', 'fleeting', 'loai' hoặc 'sai_ma'."""
    m = MA_RE.match((ma or "").strip().upper())
    if not m:
        return "sai_ma"
    nguon, tin = m.group(1), int(m.group(2))
    if nguon in kd["loai_nguon"] or tin in kd["loai_tin"]:
        return "loai"
    if nguon in kd["chi_toi_fleeting"]:
        return "fleeting"
    if nguon in kd["literature_nguon"] and tin in kd["the_tin"]:
        return "the"
    return "literature"


# ---------------------------------------------------------------- ngữ cảnh


@dataclass
class BoNao:
    goc: Path
    cfg: dict
    now: dt.datetime = field(default_factory=bay_gio)

    @property
    def vault(self) -> Path:
        return self.goc / self.cfg["bo_nao"]["vault"]

    def p(self, khoa: str) -> Path:
        return self.vault / self.cfg["duong_dan"][khoa]

    @property
    def kd(self) -> dict:
        return self.cfg["kiem_duyet"]

    @property
    def gio(self) -> str:
        return f"{self.now:%Y-%m-%d %H:%M}"


def tim_goc(tu: Path) -> Path | None:
    for p in [tu, *tu.parents]:
        if (p / "brain.toml").is_file():
            return p
    return None


def mo_bo_nao(goc_chi_dinh: str | None) -> BoNao:
    chi_dinh = goc_chi_dinh or os.environ.get("BRAIN_ROOT")
    goc = Path(chi_dinh).resolve() if chi_dinh else tim_goc(Path.cwd())
    if goc is None or not (goc / "brain.toml").is_file():
        raise SystemExit("Không tìm thấy brain.toml. Chạy trong thư mục bộ não hoặc dùng --root.")
    with (goc / "brain.toml").open("rb") as f:
        cfg = gop(MAC_DINH, tomllib.load(f))
    return BoNao(goc=goc, cfg=cfg)


# ---------------------------------------------------------------- lệnh


def lenh_ghi(bn: BoNao, noi_dung: str, kenh: str) -> int:
    noi_dung = " ".join(noi_dung.split())
    if not noi_dung:
        print("Không có gì để ghi.", file=sys.stderr)
        return 2
    ghi_them(bn.p("inbox"), f"- [{bn.gio}] ({kenh}) {noi_dung}\n", "# Inbox\n\n## Mục\n")
    print(f"Đã ghi vào Inbox: {noi_dung}")
    return 0


def lenh_nop(bn: BoNao, file: str) -> int:
    nguon_file = Path(file)
    if not nguon_file.is_file():
        print(f"Không thấy file {file}", file=sys.stderr)
        return 2
    text = doc(nguon_file)
    fm, body = frontmatter(text)
    thieu = [k for k in bn.kd["truong_bat_buoc"] if not fm.get(k)]
    if thieu:
        tin = f"K1 trả lại {nguon_file.name}: thiếu {', '.join(thieu)}."
        if bn.kd["chan_cung"]:
            print(tin + " Bổ sung phiếu nguồn rồi nộp lại.", file=sys.stderr)
            return 2
        print("Cảnh báo: " + tin)
    ma = fm.get("ma", "").strip().upper()
    kq = phan_loai(ma, bn.kd)
    if kq == "sai_ma":
        print(f"K1 trả lại {nguon_file.name}: mã '{ma}' phải có dạng nguồn A–F + tin 1–6, ví dụ B2.", file=sys.stderr)
        return 2
    if kq == "loai":
        ghi_them(
            bn.p("log") / "k1.md",
            f"- [{bn.gio}] loại · {ma} · {nguon_file.name} · {fm.get('nguon', '')}\n",
            "# K1 · mục bị loại\n\n",
        )
        print(f"K1 loại {nguon_file.name} (mã {ma}). Đã ghi vào _log/k1.md, không vào Inbox.")
        return 3
    cap = {"k1_toi_da": kq, "ngay_nop": f"{bn.now:%Y-%m-%d}"}
    if kq == "fleeting":
        cap["nhan"] = "chua-kiem"
    ten = f"{bn.now:%Y%m%d-%H%M%S}-{slug(nguon_file.stem)}.md"
    dich = bn.p("inbox_agent") / ten
    dich.parent.mkdir(parents=True, exist_ok=True)
    dich.write_text(them_vao_frontmatter(text, cap), encoding="utf-8", newline="\n")
    td = tieu_de(body, nguon_file.stem)
    ghi_them(bn.p("inbox"), f"- [{bn.gio}] (agent) {td} · {ma} · tối đa {NHAN_K1[kq]} → agent/{ten}\n", "# Inbox\n\n## Mục\n")
    print(f"K1 đạt: {td} · mã {ma} · đi tối đa tới {NHAN_K1[kq]}.")
    return 0


def kiem(bn: BoNao) -> tuple[list[str], list[str]]:
    loi: list[str] = []
    canh_bao: list[str] = []
    hom_nay = bn.now.date()
    kd = bn.kd

    def ten(p: Path) -> str:
        return p.relative_to(bn.vault).as_posix()

    # K1: mục agent đã nằm trong Inbox
    for p in cac_note(bn.p("inbox_agent")):
        fm, _ = frontmatter(doc(p))
        thieu = [k for k in kd["truong_bat_buoc"] if not fm.get(k)]
        if thieu:
            loi.append(f"K1 · {ten(p)}: mục agent thiếu {', '.join(thieu)}")
            continue
        kq = phan_loai(fm.get("ma", ""), kd)
        if kq == "sai_ma":
            loi.append(f"K1 · {ten(p)}: mã '{fm.get('ma')}' sai dạng")
        elif kq == "loai":
            loi.append(f"K1 · {ten(p)}: mã {fm.get('ma')} bị loại nhưng vẫn nằm trong Inbox")

    # K2: literature có mã
    for p in cac_note(bn.p("literature")):
        fm, _ = frontmatter(doc(p))
        ma = fm.get("ma", "").upper()
        if not ma:
            continue
        m = MA_RE.match(ma)
        if not m:
            loi.append(f"K2 · {ten(p)}: mã '{ma}' sai dạng")
        elif m.group(1) not in kd["literature_nguon"]:
            loi.append(f"K2 · {ten(p)}: literature cần nguồn {'–'.join((kd['literature_nguon'][0], kd['literature_nguon'][-1]))}, đang là {ma}")
        if not fm.get("luu_tru"):
            loi.append(f"K2 · {ten(p)}: thiếu bản lưu (luu_tru)")

    # K3 và luật permanent
    for p in cac_note(bn.p("permanent")):
        text = doc(p)
        fm, body = frontmatter(text)
        if not LINK_RE.search(body) and not LINK_RE.search(fm.get("lien_ket", "")):
            loi.append(f"Tri thức · {ten(p)}: permanent note chưa nối tới note nào")
        ma = fm.get("ma", "").upper()
        if ma:
            m = MA_RE.match(ma)
            if not m:
                loi.append(f"K3 · {ten(p)}: mã '{ma}' sai dạng")
            elif int(m.group(2)) not in kd["permanent_tin"]:
                loi.append(f"K3 · {ten(p)}: permanent cần tin {'–'.join(map(str, (kd['permanent_tin'][0], kd['permanent_tin'][-1])))}, đang là {ma}")
        if not fm.get("id"):
            canh_bao.append(f"Tri thức · {ten(p)}: permanent note chưa có id")

    # Fleeting quá hạn giữ
    toi_da = fleeting_toi_da(bn)
    for p in cac_note(bn.p("fleeting")):
        fm, _ = frontmatter(doc(p))
        tuoi = (hom_nay - ngay_cua(p, fm)).days
        if tuoi > toi_da:
            canh_bao.append(f"Tri thức · {ten(p)}: fleeting đã {tuoi} ngày, nâng lên literature hoặc xoá")

    # Hạn dùng
    for khoa in ("literature", "permanent", "inbox_agent"):
        for p in cac_note(bn.p(khoa)):
            fm, _ = frontmatter(doc(p))
            het = han_het(fm.get("han_dung", ""))
            if het and hom_nay >= het:
                canh_bao.append(f"Kiểm duyệt · {ten(p)}: quá hạn dùng ({fm.get('han_dung')})")

    # Projects · 2.2: không kiểm giới hạn số project hay next action
    na_path = bn.p("next_actions")
    next_actions = doc(na_path) if na_path.is_file() else ""
    tt = bn.cfg["thuc_thi"]
    for p in cac_note(bn.p("projects")):
        fm, _ = frontmatter(doc(p))
        trang_thai = fm.get("trang_thai", "")
        if trang_thai not in TRANG_THAI:
            loi.append(f"Hành động · {ten(p)}: trang_thai phải là {', '.join(TRANG_THAI)}")
            continue
        if trang_thai == "active":
            for k in ("ket_qua", "tieu_chi_xong", "tieu_chi_dung"):
                if not fm.get(k):
                    loi.append(f"Hành động · {ten(p)}: thiếu {k}, ghi ngay khi lập project")
            co_board = bool(fm.get("board"))
            if tt["canh_bao_milestone_khong_board"] and fm.get("milestone") and not co_board:
                canh_bao.append(f"Thực thi · {ten(p)}: có milestone nhưng chưa có board")
            if tt["canh_bao_project_khong_viec"] and not co_board and f"[[{p.stem}]]" not in next_actions:
                canh_bao.append(f"Thực thi · {ten(p)}: project active chưa có việc nào trong Next Actions hay trên board")
            het = han_het(fm.get("han", ""))
            if het and hom_nay >= het:
                canh_bao.append(f"Thực thi · {ten(p)}: đã qua hạn {fm.get('han')}")
        if trang_thai == "stopped" and not fm.get("ly_do_dung"):
            canh_bao.append(f"Hành động · {ten(p)}: project dừng nên ghi ly_do_dung")
    return loi, canh_bao


def in_ket_qua(loi: list[str], canh_bao: list[str]) -> None:
    if loi:
        print(f"Lỗi ({len(loi)}):")
        for d in loi:
            print(f"  - {d}")
    if canh_bao:
        print(f"Cảnh báo ({len(canh_bao)}):")
        for d in canh_bao:
            print(f"  - {d}")
    if not loi and not canh_bao:
        print("Vault sạch.")


def lenh_kiem(bn: BoNao) -> int:
    loi, canh_bao = kiem(bn)
    in_ket_qua(loi, canh_bao)
    return 1 if loi else 0


def lenh_turn(bn: BoNao, loai: str, tom_tat: str) -> int:
    tom_tat = " ".join(tom_tat.split())
    if not tom_tat:
        print("Cần một câu tóm tắt cho lượt này.", file=sys.stderr)
        return 2
    loi, canh_bao = kiem(bn)
    if loi and bn.kd["chan_cung"]:
        in_ket_qua(loi, [])
        print(f"Lượt chưa đóng được: sửa {len(loi)} lỗi rồi chạy lại brain turn.", file=sys.stderr)
        return 1
    ghi_them(bn.p("log") / "turns.md", f"- [{bn.gio}] {loai} · {tom_tat}\n", "# Các lượt làm việc\n\n")
    print(f"Bộ não: {loai} · {tom_tat}")
    if canh_bao:
        print(f"({len(canh_bao)} cảnh báo, xem brain kiem)")
    return 0


def _dong_co_ngay(p: Path) -> list[tuple[dt.date, str]]:
    if not p.is_file():
        return []
    kq = []
    for d in doc(p).splitlines():
        m = DONG_INBOX_RE.match(d)
        if m:
            kq.append((dt.date.fromisoformat(m.group(1)), d))
    return kq


def so_do(bn: BoNao) -> dict:
    hom_nay = bn.now.date()
    tuan_truoc = hom_nay - dt.timedelta(days=7)
    projects = [frontmatter(doc(p))[0] for p in cac_note(bn.p("projects"))]
    dem = {t: sum(1 for fm in projects if fm.get("trang_thai") == t) for t in TRANG_THAI}
    na = doc(bn.p("next_actions")) if bn.p("next_actions").is_file() else ""
    inbox = _dong_co_ngay(bn.p("inbox"))
    agent = cac_note(bn.p("inbox_agent"))
    agent_thieu = sum(
        1 for p in agent if any(not frontmatter(doc(p))[0].get(k) for k in bn.kd["truong_bat_buoc"])
    )
    toi_da = fleeting_toi_da(bn)
    fleeting_cu = sum(
        1 for p in cac_note(bn.p("fleeting")) if (hom_nay - ngay_cua(p, frontmatter(doc(p))[0])).days > toi_da
    )
    perm_moi = sum(
        1 for p in cac_note(bn.p("permanent")) if ngay_cua(p, frontmatter(doc(p))[0]) > tuan_truoc
    )
    turns = [d for ngay, d in _dong_co_ngay(bn.p("log") / "turns.md") if ngay > tuan_truoc]
    bi_loai = sum(1 for ngay, _ in _dong_co_ngay(bn.p("log") / "k1.md") if ngay > tuan_truoc)
    qua_han_dung = 0
    for khoa in ("literature", "permanent", "inbox_agent"):
        for p in cac_note(bn.p(khoa)):
            het = han_het(frontmatter(doc(p))[0].get("han_dung", ""))
            qua_han_dung += bool(het and hom_nay >= het)
    qua_han_project = sum(
        1
        for fm in projects
        if fm.get("trang_thai") == "active" and (h := han_het(fm.get("han", ""))) and hom_nay >= h
    )
    return {
        "tuan": f"{hom_nay.isocalendar().year}-W{hom_nay.isocalendar().week:02d}",
        "project_active": dem["active"],
        "project_xong": dem["done"],
        "project_dung": dem["stopped"],
        "project_qua_han": qua_han_project,
        "next_mo": len(re.findall(r"^\s*- \[ \]", na, flags=re.M)),
        "next_xong": len(re.findall(r"^\s*- \[[xX]\]", na, flags=re.M)),
        "inbox": len(inbox),
        "inbox_cu_nhat_ngay": max(((hom_nay - ngay).days for ngay, _ in inbox), default=0),
        "fleeting_qua_han": fleeting_cu,
        "permanent_moi": perm_moi,
        "luot": len(turns),
        "luot_theo_loai": {k: sum(1 for d in turns if f"] {k} ·" in d) for k in LOAI_TURN},
        "k1_bi_loai": bi_loai,
        "phan_tram_thieu_phieu": round(100 * agent_thieu / len(agent)) if agent else 0,
        "qua_han_dung": qua_han_dung,
    }


def lenh_weekly(bn: BoNao, luu: bool) -> int:
    s = so_do(bn)
    theo_loai = ", ".join(f"{k} {v}" for k, v in s["luot_theo_loai"].items())
    md = "\n".join(
        [
            f"## Số đo · {s['tuan']}",
            "",
            "| Số đo | Giá trị |",
            "| --- | --- |",
            f"| Project active | {s['project_active']} |",
            f"| Project xong · dừng | {s['project_xong']} · {s['project_dung']} |",
            f"| Project qua hạn | {s['project_qua_han']} |",
            f"| Next action đang mở · đã xong | {s['next_mo']} · {s['next_xong']} |",
            f"| Mục trong Inbox · cũ nhất (ngày) | {s['inbox']} · {s['inbox_cu_nhat_ngay']} |",
            f"| Fleeting quá {fleeting_toi_da(bn)} ngày | {s['fleeting_qua_han']} |",
            f"| Permanent note mới trong 7 ngày | {s['permanent_moi']} |",
            f"| Lượt làm việc trong 7 ngày | {s['luot']} ({theo_loai}) |",
            f"| K1 bị loại trong 7 ngày | {s['k1_bi_loai']} |",
            f"| % mục agent thiếu phiếu | {s['phan_tram_thieu_phieu']}% |",
            f"| Mục quá hạn dùng | {s['qua_han_dung']} |",
            "",
            "Chỉ đo, không chặn. Không có giới hạn số project hay next action từ 2.2.0.",
            "",
        ]
    )
    print(md)
    if luu:
        dich = bn.p("weekly") / f"{s['tuan']}.md"
        dich.parent.mkdir(parents=True, exist_ok=True)
        dich.write_text(f"# Weekly Review · {s['tuan']}\n\n" + md, encoding="utf-8", newline="\n")
        print(f"Đã lưu {dich.relative_to(bn.vault).as_posix()}")
    return 0


def fleeting_toi_da(bn: BoNao) -> int:
    return int(bn.cfg["lam_ro"]["fleeting_toi_da_ngay"])


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="brain", description=f"Brain_Standard {PHIEN_BAN}")
    ap.add_argument("--root", help="thư mục chứa brain.toml (mặc định: tìm từ thư mục hiện tại)")
    ap.add_argument("--version", action="version", version=f"brain {PHIEN_BAN}")
    sub = ap.add_subparsers(dest="lenh", required=True)
    g = sub.add_parser("ghi", help="ghi lời bạn vào Inbox")
    g.add_argument("noi_dung", nargs="+")
    g.add_argument("--kenh", default="tay", help="kênh: tay, noi, telegram… (mặc định: tay)")
    n = sub.add_parser("nop", help="nộp mục do agent mang về qua K1")
    n.add_argument("file")
    sub.add_parser("kiem", help="rà vault theo luật 2.2")
    t = sub.add_parser("turn", help="đóng một lượt làm việc")
    t.add_argument("loai", choices=LOAI_TURN)
    t.add_argument("tom_tat", nargs="+")
    w = sub.add_parser("weekly", help="số đo cho Weekly Review")
    w.add_argument("--ghi", action="store_true", help="lưu vào thư mục weekly/")
    a = ap.parse_args(argv)
    bn = mo_bo_nao(a.root)
    if a.lenh == "ghi":
        return lenh_ghi(bn, " ".join(a.noi_dung), a.kenh)
    if a.lenh == "nop":
        return lenh_nop(bn, a.file)
    if a.lenh == "kiem":
        return lenh_kiem(bn)
    if a.lenh == "turn":
        return lenh_turn(bn, a.loai, " ".join(a.tom_tat))
    if a.lenh == "weekly":
        return lenh_weekly(bn, a.ghi)
    return 2


if __name__ == "__main__":
    sys.exit(main())
