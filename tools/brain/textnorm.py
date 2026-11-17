"""Text normalisation for matching: one place that decides when two pieces of Vietnamese or English text are "the same".

Every search in the brain (brain where, brain kg ask, and brain search to come) compares text through fold(), so a
query matches a note whatever way either was typed:

  with or without diacritics   "thư viện" = "thu vien"        (marks removed)
  composed or decomposed        NFC "ư" = NFD "u" + U+031B     (both normalised before the marks go)
  đ / Đ                         "Đức" = "duc"                   (đ is a letter of its own, not d + a mark)
  upper or lower case           "PARA" = "para"                 (casefold)

Matching folds both sides; display never does. Notes, titles and triples keep the text exactly as written.
Standard library only, and it knows nothing about the vault, so kgcore can use it and stay portable.
"""
from __future__ import annotations

import re
import unicodedata

# đ and Đ do not decompose under NFD/NFKD; map them by hand. Other letters with a stroke, for non-Vietnamese names.
_STROKES = str.maketrans({"đ": "d", "Đ": "D", "ð": "d", "Ð": "D", "ł": "l", "Ł": "L", "ø": "o", "Ø": "O"})
_WORD = re.compile(r"[a-z0-9]+")


def nfc(text: str) -> str:
    """The text in composed form (NFC), so text pasted from macOS or the web compares equal to text typed on Windows."""
    return unicodedata.normalize("NFC", str(text or ""))


def fold(text: str) -> str:
    """Lower case, every combining mark removed, đ → d: the form two texts are compared in."""
    text = str(text or "").translate(_STROKES)
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text.casefold()


def words(text: str, stop=(), min_len: int = 2) -> list[str]:
    """The folded words of a text, in order: runs of a–z and 0–9, at least min_len long, stop words dropped.
    Stop words may be given with or without diacritics; they are folded too."""
    folded_stop = {fold(s) for s in stop}
    return [w for w in _WORD.findall(fold(text)) if len(w) >= min_len and w not in folded_stop]
