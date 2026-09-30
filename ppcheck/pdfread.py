"""PDF -> text reader (pypdf). Pages are joined with '\\f' so Document keeps page numbers.

Text-based PDFs only: a scanned PDF has no text layer and needs OCR first.
Cleaning done here (the cleaned text is the source of truth for quotes):
  - running headers/footers and bare page numbers are removed;
  - ligatures (fi, fl...) are expanded;
  - a line ending with '-' followed by a lowercase word is joined to the next line
    (the hyphen is kept: 'sous-\\ntraitance' -> 'sous-traitance').
"""
import re
from collections import Counter
from pathlib import Path
from typing import List

LIGATURES = {"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"}
PAGE_NUM = re.compile(r"^\s*(?:-\s*)?(?:page\s+)?\d+(?:\s*(?:/|sur|of)\s*\d+)?(?:\s*-)?\s*$", re.I)


class PdfError(Exception):
    pass


def _norm(line: str) -> str:
    return re.sub(r"\d+", "#", " ".join(line.split()).lower())


def strip_running_lines(pages: List[str]) -> List[str]:
    """Drop lines repeated in the top/bottom 2 lines of at least half the pages, and page numbers."""
    split = [p.split("\n") for p in pages]
    counts = Counter()
    for lines in split:
        nz = [i for i, l in enumerate(lines) if l.strip()]
        for i in set(nz[:2] + nz[-2:]):
            counts[_norm(lines[i])] += 1
    threshold = max(3, (len(pages) + 1) // 2) if len(pages) >= 3 else None
    out = []
    for lines in split:
        nz = [i for i, l in enumerate(lines) if l.strip()]
        edge = set(nz[:2] + nz[-2:])
        keep = []
        for i, l in enumerate(lines):
            if i in edge and l.strip():
                if PAGE_NUM.match(l) or (threshold and counts[_norm(l)] >= threshold):
                    continue
            keep.append(l)
        out.append("\n".join(keep))
    return out


def clean_page(text: str) -> str:
    for k, v in LIGATURES.items():
        text = text.replace(k, v)
    text = text.replace("­", "")                       # soft hyphen
    text = re.sub(r"[ \t]+\n", "\n", text.replace("\r", ""))
    return re.sub(r"(\w)-\n(?=[a-zà-ÿ])", r"\1-", text)


def read_pdf(path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:      # pragma: no cover
        raise PdfError("pypdf is required to read PDFs: pip install pypdf") from e
    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted and not reader.decrypt(""):
            raise PdfError(f"{path}: PDF protege par mot de passe")
        pages = [clean_page(p.extract_text() or "") for p in reader.pages]
    except PdfError:
        raise
    except Exception as e:
        raise PdfError(f"{path}: PDF illisible ({type(e).__name__}: {e})") from e
    chars = sum(len(p.strip()) for p in pages)
    if not pages or chars < 20 * len(pages):
        raise PdfError(f"{path}: peu ou pas de texte extractible ({chars} caracteres sur {len(pages)} pages) - "
                       "PDF scanne ? Passer d'abord par un OCR.")
    return "\f".join(strip_running_lines(pages))


def pdf_to_text_file(path, out=None) -> Path:
    out = Path(out) if out else Path(path).with_suffix(".txt")
    out.write_text(read_pdf(path), encoding="utf-8")
    return out
