"""Configuration: package defaults merged with the brain's own brain.toml, and the brain context."""
from __future__ import annotations

import datetime as dt
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE = "brain.toml"
DEFAULTS_FILE = Path(__file__).with_name("defaults.toml")
ROOT_ENV = "BRAIN_ROOT"
NOW_ENV = "BRAIN_NOW"


class BrainError(Exception):
    """A rule was broken or the input is wrong. Carries the exit code to return."""

    def __init__(self, message: str, code: int = 2):
        super().__init__(message)
        self.code = code


def load_toml(path: Path) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def merge(base: dict, override: dict) -> dict:
    """Deep merge: keys in override win; nested tables merge key by key."""
    out = {k: (merge(v, {}) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in override.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def defaults() -> dict:
    return load_toml(DEFAULTS_FILE)


def find_root(start: Path | None = None) -> Path | None:
    """The nearest folder, from start upwards, that holds brain.toml."""
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / CONFIG_FILE).is_file():
            return p
    return None


def now() -> dt.datetime:
    value = os.environ.get(NOW_ENV)
    return dt.datetime.fromisoformat(value) if value else dt.datetime.now().replace(microsecond=0)


@dataclass
class Brain:
    """One brain: its root folder, merged configuration and the current time."""

    root: Path
    cfg: dict
    now: dt.datetime = field(default_factory=now)

    @property
    def vault(self) -> Path:
        return self.root / self.cfg["brain"]["vault"]

    def path(self, key: str) -> Path:
        """A path from [paths], resolved inside the vault."""
        return self.vault / self.cfg["paths"][key]

    @property
    def gates(self) -> dict:
        return self.cfg["gates"]

    @property
    def assistant(self) -> dict:
        return self.cfg["assistant"]

    @property
    def stamp(self) -> str:
        return f"{self.now:%Y-%m-%d %H:%M}"

    @property
    def today(self) -> dt.date:
        return self.now.date()

    def rel(self, p: Path) -> str:
        """Path relative to the vault, with forward slashes, for messages."""
        return p.relative_to(self.vault).as_posix()


def open_brain(root: str | Path | None = None) -> Brain:
    """Open the brain at root, at $BRAIN_ROOT, or at the nearest brain.toml above the current folder."""
    chosen = root or os.environ.get(ROOT_ENV)
    path = Path(chosen).resolve() if chosen else find_root()
    if path is None or not (path / CONFIG_FILE).is_file():
        raise BrainError(f"No {CONFIG_FILE} found. Run inside a brain folder or pass --root.", code=1)
    return Brain(root=path, cfg=merge(defaults(), load_toml(path / CONFIG_FILE)))
