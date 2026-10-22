"""brain migrate: convert a brain from the 3.0 Vietnamese names to the 4.0 English names.

Run once after pulling 4.0. It is safe to run again: names already converted are left alone.
Every rename here is listed in docs/glossary.md.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import notes
from .config import CONFIG_FILE, defaults

# ---- brain.toml: old table → (new table, {old key: new key})
CONFIG_TABLES = {
    "bo_nao": ("brain", {"phien_ban": "version", "vault": "vault"}),
    "duong_dan": ("paths", {}),
    "lam_ro": ("clarify", {"fleeting_toi_da_ngay": "fleeting_max_days", "moc_khi_du_note": "moc_min_notes"}),
    "nhip": ("rhythm", {"vong_ngay_chon_toi_da": "daily_pick_max"}),
    "kiem_duyet": ("gates", {
        "chan_cung": "strict", "truong_bat_buoc": "required_fields", "loai_nguon": "reject_sources",
        "loai_tin": "reject_credibility", "chi_toi_fleeting": "fleeting_only_sources",
        "literature_nguon": "literature_sources", "permanent_tin": "permanent_credibility",
        "the_tin": "card_credibility",
    }),
    "thuc_thi": ("execution", {
        "canh_bao_milestone_khong_board": "warn_milestone_without_board",
        "canh_bao_project_khong_viec": "warn_project_without_task",
    }),
    "johnny_decimal": ("johnny_decimal", {"khu": "area", "toi_da_category": "max_categories"}),
    "javis": ("assistant", {"nhan": "label", "treo_toi_da_ngay": "stale_after_days"}),
}

# ---- frontmatter keys and values
FIELDS = {
    "loai": "type", "nguon": "source", "nguon_goc": "original_source", "tac_gia": "author",
    "ngay_dang": "published", "ngay_lay": "retrieved", "han_dung": "valid_until", "luu_tru": "archived",
    "ma": "grade", "cach_kiem": "verification", "k1_toi_da": "max_reach", "ngay_nop": "submitted",
    "nhan": "label", "vi_tri": "location", "doc_ngay": "read_on", "lien_ket": "links", "the": "cards",
    "trang_thai": "status", "bat_dau": "started", "ket_qua": "outcome", "tieu_chi_xong": "done_when",
    "tieu_chi_dung": "stop_when", "han": "due", "nguoi": "people", "ly_do_dung": "stop_reason",
    "tieu_chuan": "standard", "project_quy_nay": "project_this_quarter", "ngay": "date",
}
VALUES = {"max_reach": {"the": "card"}, "label": {"chua-kiem": "unverified"}}

# ---- files and folders (relative to the vault), applied in order
RENAMES = [
    ("_mau/phieu-nguon.md", "_templates/source-record.md"),
    ("_mau", "_templates"),
    ("Coding/50 He thong", "Coding/50 System"),
    ("Coding", "Code"),
    ("_log/k1.md", "_log/rejected.md"),
]
TEMPLATE_RE = re.compile(r"^_mau-(.+\.md)$")

# ---- text inside line-based files: [paths] key → rules (old → new). "*" applies to every note.
LINE_RULES = {
    "next_actions": [
        (re.compile(r" · giao (\d{4}-\d{2}-\d{2})"), r" · assigned \1"),
        (re.compile(r" · xong (\d{4}-\d{2}-\d{2})"), r" · done \1"),
    ],
    "inbox": [
        (re.compile(r"^(- \[[^\]]+\]) \(tay\) ", re.M), r"\1 (hand) "),
        (re.compile(r"^(- \[[^\]]+\]) \(noi\) ", re.M), r"\1 (voice) "),
        (re.compile(r"^(- \[[^\]]+\] \(javis\)) Kết quả ", re.M), r"\1 Result "),
        (re.compile(r" · tối đa thẻ ôn → "), " · up to flashcard → "),
        (re.compile(r" · tối đa literature → "), " · up to literature → "),
        (re.compile(r" · tối đa fleeting \(chưa kiểm\) → "), " · up to fleeting (unverified) → "),
        (re.compile(r"^## Mục$", re.M), "## Items"),
    ],
    "turn_log": [
        (re.compile(r"^(- \[[^\]]+\]) viec · ", re.M), r"\1 task · "),
        (re.compile(r"^(- \[[^\]]+\]) y · ", re.M), r"\1 idea · "),
        (re.compile(r"^(- \[[^\]]+\]) xoa · ", re.M), r"\1 drop · "),
        (re.compile(r"^# Các lượt làm việc$", re.M), "# Turns"),
    ],
    "rejected_log": [
        (re.compile(r"^(- \[[^\]]+\]) loại · ", re.M), r"\1 rejected · "),
        (re.compile(r"^# K1 · mục bị loại$", re.M), "# G1 · rejected items"),
    ],
    "*": [
        (re.compile(r"\bCoding/50 He thong/"), "Code/50 System/"),
        (re.compile(r"\bCoding/"), "Code/"),
    ],
}


@dataclass
class Plan:
    changes: list[str] = field(default_factory=list)

    def add(self, what: str) -> None:
        self.changes.append(what)


# ---------------------------------------------------------------- brain.toml

def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    s = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{s}"'


def dump_toml(data: dict, prefix: str = "") -> str:
    """Write a dict as TOML: plain keys first, then nested tables."""
    plain = {k: v for k, v in data.items() if not isinstance(v, dict)}
    tables = {k: v for k, v in data.items() if isinstance(v, dict)}
    out = []
    if prefix and plain:
        out.append(f"[{prefix}]")
    out += [f"{k} = {_toml_value(v)}" for k, v in plain.items()]
    if plain:
        out.append("")
    for k, v in tables.items():
        out.append(dump_toml(v, f"{prefix}.{k}" if prefix else k))
    return "\n".join(out)


def convert_config(old: dict, version: str) -> dict:
    new: dict = {}
    for table, values in old.items():
        if not isinstance(values, dict):
            new[table] = values
            continue
        target, keys = CONFIG_TABLES.get(table, (table, {}))
        section = new.setdefault(target, {})
        for k, v in values.items():
            if target == "gates" and k == "truong_bat_buoc":
                v = [FIELDS.get(x, x) for x in v]
            section[keys.get(k, k)] = v
    new.setdefault("brain", {})["version"] = version
    return new


def migrate_config(root: Path, plan: Plan, dry_run: bool) -> None:
    path = root / CONFIG_FILE
    with path.open("rb") as f:
        old = tomllib.load(f)
    if not any(t in old for t in CONFIG_TABLES if t not in ("johnny_decimal",)) \
            and "khu" not in old.get("johnny_decimal", {}):
        return
    version = defaults()["brain"]["version"]
    new = convert_config(old, version)
    plan.add(f"{CONFIG_FILE}: rename tables and keys to 4.0 names, version {version}")
    if not dry_run:
        header = "# Brain configuration (converted by brain migrate). Defaults: tools/brain/defaults.toml.\n\n"
        notes.write(path, header + dump_toml(new).rstrip() + "\n")


# ---------------------------------------------------------------- vault

def _rename(src: Path, dst: Path, plan: Plan, dry_run: bool, vault: Path) -> None:
    if not src.exists() or dst.exists():
        return
    plan.add(f"rename {src.relative_to(vault).as_posix()} → {dst.relative_to(vault).as_posix()}")
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        src.rename(dst)


def migrate_files(vault: Path, plan: Plan, dry_run: bool) -> None:
    for old, new in RENAMES:
        _rename(vault / old, vault / new, plan, dry_run, vault)
    for p in sorted(vault.rglob("_mau-*.md")):
        m = TEMPLATE_RE.match(p.name)
        if m:
            _rename(p, p.with_name(f"_template-{m.group(1)}"), plan, dry_run, vault)
    if not dry_run:  # drop old folders the renames left empty
        for old, _ in reversed(RENAMES):
            d = vault / old
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()


def convert_frontmatter(text: str) -> str:
    parts = notes.split_frontmatter(text)
    if parts is None:
        return text
    fm_lines, body = parts
    out = []
    for line in fm_lines:
        m = re.match(r"^(\s*#?\s*)([A-Za-z_][\w]*)(\s*:)(.*)$", line)
        if not m or m.group(2) not in FIELDS:
            out.append(line)
            continue
        key = FIELDS[m.group(2)]
        rest = m.group(4)
        for old_v, new_v in VALUES.get(key, {}).items():
            rest = re.sub(rf"(^\s*){re.escape(old_v)}(\s|$)", rf"\g<1>{new_v}\2", rest)
        out.append(f"{m.group(1)}{key}{m.group(3)}{rest}")
    return "\n".join(["---", *out, "---", *body]) + ("\n" if text.endswith("\n") else "")


def convert_lines(text: str, rules: list) -> str:
    for pattern, repl in rules:
        text = pattern.sub(repl, text)
    return text


def migrate_notes(vault: Path, paths: dict, plan: Plan, dry_run: bool) -> None:
    by_file = {(vault / paths[k]).resolve(): rules for k, rules in LINE_RULES.items() if k != "*"}
    for p in sorted(vault.rglob("*.md")):
        text = notes.read(p)
        rules = by_file.get(p.resolve(), []) + LINE_RULES["*"]
        new = convert_lines(convert_frontmatter(text), rules)
        if new != text:
            plan.add(f"update {p.relative_to(vault).as_posix()}")
            if not dry_run:
                notes.write(p, new)


def run(root: Path, vault_rel: str | None = None, dry_run: bool = False) -> Plan:
    plan = Plan()
    migrate_config(root, plan, dry_run)
    with (root / CONFIG_FILE).open("rb") as f:
        cfg = tomllib.load(f)
    vault = root / (vault_rel or cfg.get("brain", cfg.get("bo_nao", {})).get("vault", "vault"))
    paths = {**defaults()["paths"], **cfg.get("paths", cfg.get("duong_dan", {}))}
    if vault.is_dir():
        migrate_files(vault, plan, dry_run)
        if dry_run:  # files were not renamed yet: old names hold the rules
            paths = {**paths, "rejected_log": "_log/k1.md"}
        migrate_notes(vault, paths, plan, dry_run)
    return plan
