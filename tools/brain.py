#!/usr/bin/env python3
"""brain · CLI cho Brain_Standard 3.0.

Lệnh:
  ghi "…"                       ghi lời bạn vào Inbox (không qua K1)
  nop <file.md>                 nộp mục do agent mang về qua cổng K1
  kiem                          rà vault theo luật 3.0 và cổng K2–K3
  turn <viec|y|file|xoa> "…"    đóng một lượt làm việc
  weekly [--ghi]                số đo cho Weekly Review
  giao "…" <suggest|auto|full>  giao một next action cho Javis (chỉ chủ bộ não)
  javis [--muc …]               liệt kê việc đang giao cho Javis
  xong <số> "kết quả"           Javis báo xong một việc; kết quả về Inbox

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

PHIEN_BAN = "3.0.0"
MA_RE = re.compile(r"^([A-F])([1-6])$")
DONG_INBOX_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?\]")
LINK_RE = re.compile(r"\[\[[^\]]+\]\]")
LOAI_TURN = ("viec", "y", "file", "xoa")
TRANG_THAI = ("someday", "active", "done", "stopped")
MUC_JAVIS = ("suggest", "auto", "full")
VIEC_RE = re.compile(r"^(\s*)- \[([ xX])\] (.*)$")
GIAO_RE = re.compile(r"· giao (\d{4}-\d{2}-\d{2})")
XONG_RE = re.compile(r"· xong (\d{4}-\d{2}-\d{2})")
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
    "javis": {"nhan": "@javis", "treo_toi_da_ngay": 7},
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


@dataclass
class ViecJavis:
    """Một next action mang nhãn @javis."""

    dong: int          # chỉ số dòng trong file Next Actions
    xong: bool
    muc: str           # "" nếu thiếu hoặc sai mức
    noi_dung: str
    giao: dt.date | None
    ngay_xong: dt.date | None


def _nhan_re(bn: "BoNao") -> re.Pattern:
    return re.compile(re.escape(bn.cfg["javis"]["nhan"]) + r"(?::([\w-]+))?(?![\w:-])")


def viec_javis(bn: "BoNao") -> list[ViecJavis]:
    p = bn.p("next_actions")
    if not p.is_file():
        return []
    nhan = _nhan_re(bn)
    kq = []
    for i, d in enumerate(doc(p).splitlines()):
        m = VIEC_RE.match(d)
        if not m:
            continue
        n = nhan.search(m.group(3))
        if not n:
            continue
        muc = n.group(1) or ""
        g, x = GIAO_RE.search(d), XONG_RE.search(d)
        kq.append(ViecJavis(
            dong=i, xong=m.group(2) != " ", muc=muc if muc in MUC_JAVIS else "",
            noi_dung=m.group(3), giao=dt.date.fromisoformat(g.group(1)) if g else None,
            ngay_xong=dt.date.fromisoformat(x.group(1)) if x else None,
        ))
    return kq


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


def lenh_giao(bn: BoNao, khop: str, muc: str) -> int:
    p = bn.p("next_actions")
    khop = " ".join(khop.split())
    dong = doc(p).splitlines() if p.is_file() else []
    nhan = _nhan_re(bn)
    trung = [i for i, d in enumerate(dong)
             if (m := VIEC_RE.match(d)) and m.group(2) == " " and khop.lower() in m.group(3).lower()]
    if len(trung) != 1:
        print(f"Cần đúng 1 next action đang mở chứa '{khop}', đang thấy {len(trung)}.", file=sys.stderr)
        return 2
    i = trung[0]
    if nhan.search(dong[i]):
        print("Việc này đã giao cho Javis. Sửa mức bằng tay trong Next Actions nếu cần.", file=sys.stderr)
        return 2
    dong[i] = f"{dong[i].rstrip()} · {bn.cfg['javis']['nhan']}:{muc} · giao {bn.now:%Y-%m-%d}"
    p.write_text("\n".join(dong) + "\n", encoding="utf-8", newline="\n")
    print(f"Đã giao cho Javis ({muc}): {VIEC_RE.match(dong[i]).group(3)}")
    return 0


def _mo_theo_muc(bn: BoNao, muc_toi_da: str | None) -> list[ViecJavis]:
    tran = MUC_JAVIS.index(muc_toi_da) if muc_toi_da else len(MUC_JAVIS) - 1
    return [v for v in viec_javis(bn) if not v.xong and v.muc and MUC_JAVIS.index(v.muc) <= tran]


def lenh_javis(bn: BoNao, muc_toi_da: str | None) -> int:
    ds = _mo_theo_muc(bn, muc_toi_da)
    if not ds:
        print("Không có việc nào đang giao cho Javis" + (f" ở mức {muc_toi_da} trở xuống." if muc_toi_da else "."))
        return 0
    for so, v in enumerate(ds, 1):
        print(f"{so} · {v.muc} · {v.noi_dung}")
    return 0


def lenh_xong(bn: BoNao, so: int, ket_qua: str, muc_toi_da: str | None) -> int:
    ket_qua = " ".join(ket_qua.split())
    if not ket_qua:
        print("Cần một câu kết quả.", file=sys.stderr)
        return 2
    ds = _mo_theo_muc(bn, muc_toi_da)
    if not 1 <= so <= len(ds):
        print(f"Không có việc số {so}. Chạy brain javis để xem danh sách.", file=sys.stderr)
        return 2
    v = ds[so - 1]
    p = bn.p("next_actions")
    dong = doc(p).splitlines()
    dong[v.dong] = dong[v.dong].replace("- [ ]", "- [x]", 1).rstrip() + f" · xong {bn.now:%Y-%m-%d}"
    p.write_text("\n".join(dong) + "\n", encoding="utf-8", newline="\n")
    viec = _nhan_re(bn).sub("", GIAO_RE.sub("", v.noi_dung))
    viec = " ".join(viec.replace("· ·", "·").split()).strip(" ·")
    ghi_them(bn.p("inbox"), f"- [{bn.gio}] (javis) Kết quả \"{viec}\": {ket_qua}\n", "# Inbox\n\n## Mục\n")
    print(f"Đã xong: {viec}. Kết quả đã vào Inbox để làm rõ.")
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

    # Javis · 3.0: việc giao phải có mức; việc treo quá lâu thì cảnh báo
    treo = int(bn.cfg["javis"]["treo_toi_da_ngay"])
    for v in viec_javis(bn):
        if v.xong:
            continue
        if not v.muc:
            loi.append(f"Javis · next action dòng {v.dong + 1}: {bn.cfg['javis']['nhan']} cần mức {', '.join(MUC_JAVIS)}")
        elif v.giao and (hom_nay - v.giao).days > treo:
            canh_bao.append(f"Javis · next action dòng {v.dong + 1}: giao Javis đã {(hom_nay - v.giao).days} ngày chưa xong")
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
    javis = viec_javis(bn)
    treo = int(bn.cfg["javis"]["treo_toi_da_ngay"])
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
        "javis_mo": sum(1 for v in javis if not v.xong),
        "javis_xong": sum(1 for v in javis if v.xong and v.ngay_xong and v.ngay_xong > tuan_truoc),
        "javis_treo": sum(1 for v in javis if not v.xong and v.giao and (hom_nay - v.giao).days > treo),
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
            f"| Việc giao Javis đang mở · xong trong 7 ngày · treo | {s['javis_mo']} · {s['javis_xong']} · {s['javis_treo']} |",
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
    sub.add_parser("kiem", help="rà vault theo luật 3.0")
    t = sub.add_parser("turn", help="đóng một lượt làm việc")
    t.add_argument("loai", choices=LOAI_TURN)
    t.add_argument("tom_tat", nargs="+")
    w = sub.add_parser("weekly", help="số đo cho Weekly Review")
    w.add_argument("--ghi", action="store_true", help="lưu vào thư mục weekly/")
    gi = sub.add_parser("giao", help="giao một next action cho Javis (chỉ chủ bộ não)")
    gi.add_argument("khop", help="một đoạn chữ có trong đúng một next action đang mở")
    gi.add_argument("muc", choices=MUC_JAVIS)
    j = sub.add_parser("javis", help="liệt kê việc đang giao cho Javis")
    j.add_argument("--muc", choices=MUC_JAVIS, help="chỉ việc ở mức này trở xuống")
    x = sub.add_parser("xong", help="báo xong một việc của Javis; kết quả về Inbox")
    x.add_argument("so", type=int, help="số thứ tự trong brain javis")
    x.add_argument("ket_qua", nargs="+")
    x.add_argument("--muc", choices=MUC_JAVIS, help="cùng --muc đã dùng với brain javis")
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
    if a.lenh == "giao":
        return lenh_giao(bn, a.khop, a.muc)
    if a.lenh == "javis":
        return lenh_javis(bn, a.muc)
    if a.lenh == "xong":
        return lenh_xong(bn, a.so, " ".join(a.ket_qua), a.muc)
    return 2


if __name__ == "__main__":
    sys.exit(main())
