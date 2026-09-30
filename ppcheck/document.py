"""Document model: skeleton tree of sections + exact character spans.

Same idea as Proxy-Pointer: sections carry breadcrumbs and line/char
pointers into the original text, so evidence is always re-read from the
source and never regenerated.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from typing import List, Optional

ABBREV = {"art", "al", "etc", "env", "cf", "p", "pp", "n", "no", "ex", "mme", "m", "dr", "vs", "resp", "ss"}

RE_MD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
RE_TOP = re.compile(r"^(chapitre|titre|partie|annexe|appendix|chapter|part)\s+([0-9IVXivx]+|[A-Z])\b(.*)$", re.I)
RE_ART = re.compile(r"^(article|art\.)\s+(\d+(?:\.\d+)*)\b(.*)$", re.I)
RE_NUM = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+([A-ZÀ-Ý].{0,78})$")
RE_BULLET = re.compile(r"^\s*(?:[-*•▪–]|\(?\d+[.)]|\(?[a-z][.)])\s+")
RE_SENT = re.compile(r"(?<=[.;!?])\s+(?=[A-ZÀ-Ý0-9«\"(])")


def _clean_title(t: str) -> str:
    return re.sub(r"^[\s:.\-–—]+", "", t).strip() or t.strip()


@dataclass
class Section:
    node_id: str
    title: str
    level: int
    breadcrumb: str
    start_line: int        # heading line
    end_line: int          # exclusive end of the section's OWN body
    parent: Optional[str]
    label: str = ""        # e.g. "12.3" or "annexe B" for cross-reference checks


@dataclass(frozen=True)
class Span:
    a: int
    b: int


class Document:
    def __init__(self, doc_id: str, raw: str):
        self.doc_id = doc_id
        pages = raw.split("\f")
        self.text = "\n".join(pages)
        self.page_starts, off = [], 0
        for p in pages:
            self.page_starts.append(off)
            off += len(p) + 1
        self.lines = self.text.split("\n")
        self.line_offsets, off = [], 0
        for ln in self.lines:
            self.line_offsets.append(off)
            off += len(ln) + 1
        self.sections: List[Section] = self._parse()
        self.by_id = {s.node_id: s for s in self.sections}

    # -- positions -------------------------------------------------------
    def page_at(self, offset: int) -> int:
        return bisect.bisect_right(self.page_starts, offset)

    def line_at(self, offset: int) -> int:
        return bisect.bisect_right(self.line_offsets, offset) - 1

    def slice(self, span: Span) -> str:
        return self.text[span.a:span.b]

    # -- structure -------------------------------------------------------
    def _heading(self, line: str, has_articles: bool):
        s = line.strip()
        if not s or s.startswith("|") or len(s) > 120:
            return None
        m = RE_MD.match(s)
        if m:
            return len(m.group(1)), m.group(2).strip()
        if s[-1] in ".;,":
            return None
        m = RE_TOP.match(s)
        if m:
            return 1, s
        m = RE_ART.match(s)
        if m:
            return 2, s
        m = RE_NUM.match(s)
        if m and s[-1] != ":":
            depth = m.group(1).count(".") + 1
            return depth + (1 if has_articles else 0), s
        return None

    @staticmethod
    def _label(title: str) -> str:
        t = title.lstrip("# ").strip()
        m = re.match(r"(?:article|art\.)\s+(\d+(?:\.\d+)*)", t, re.I)
        if m:
            return m.group(1)
        m = re.match(r"(annexe|appendix)\s+([0-9A-Za-z]+)", t, re.I)
        if m:
            return f"annexe {m.group(2).upper()}"
        m = re.match(r"(\d+(?:\.\d+)*)[.)]?\s", t + " ")
        return m.group(1) if m else ""

    def _parse(self) -> List[Section]:
        has_articles = any(RE_ART.match(l.strip()) for l in self.lines)
        heads = []
        for i, line in enumerate(self.lines):
            h = self._heading(line, has_articles)
            if h:
                heads.append((i, h[0], _clean_title(h[1]) if not line.strip().startswith("#") else h[1]))
        root = Section("0000", self.doc_id, 0, self.doc_id, -1, heads[0][0] if heads else len(self.lines), None)
        secs, stack = [root], [root]
        for n, (i, level, title) in enumerate(heads, start=1):
            while stack[-1].level >= level:
                stack.pop()
            parent = stack[-1]
            crumb = title if parent is root else f"{parent.breadcrumb} > {title}"
            sec = Section(f"{n:04d}", title, level, crumb, i, len(self.lines), parent.node_id, self._label(title))
            secs.append(sec)
            stack.append(sec)
        for a, b in zip(secs[1:], secs[2:]):
            a.end_line = b.start_line
        return secs

    # -- units and sentences ----------------------------------------------
    def units(self, sec: Section) -> List[Span]:
        """Paragraph / bullet / table-row spans of a section's own body."""
        out, cur = [], None

        def close():
            nonlocal cur
            if cur:
                out.append(Span(*cur))
            cur = None

        for li in range(sec.start_line + 1, sec.end_line):
            line, base = self.lines[li], self.line_offsets[li]
            stripped = line.strip()
            if not stripped:
                close()
                continue
            lead = len(line) - len(line.lstrip())
            end = base + len(line.rstrip())
            if stripped.startswith("|"):
                close()
                if not re.fullmatch(r"\|[\s:|\-]+\|?", stripped):
                    out.append(Span(base + lead, end))
                continue
            m = RE_BULLET.match(line)
            if m:
                close()
                cur = [base + m.end(), end]
            elif cur is None:
                cur = [base + lead, end]
            else:
                cur[1] = end
        close()
        return out

    def sentences(self, sec: Section) -> List[Span]:
        out = []
        for u in self.units(sec):
            txt, start = self.text[u.a:u.b], u.a
            pieces, last = [], 0
            for m in RE_SENT.finditer(txt):
                before = txt[last:m.start()].rsplit(None, 1)
                word = re.sub(r"\W", "", before[-1]).lower() if before else ""
                if word in ABBREV:
                    continue
                pieces.append((last, m.start()))
                last = m.end()
            pieces.append((last, len(txt)))
            out.extend(Span(start + x, start + y) for x, y in pieces if y > x)
        return out

    def heading_span(self, sec: Section) -> Optional[Span]:
        if sec.start_line < 0:
            return None
        line, base = self.lines[sec.start_line], self.line_offsets[sec.start_line]
        lead = len(line) - len(line.lstrip("# \t"))
        return Span(base + lead, base + len(line.rstrip()))

    def section_of(self, offset: int) -> Section:
        ln, best = self.line_at(offset), self.sections[0]
        for s in self.sections:
            if s.start_line <= ln:
                best = s
        return best


@dataclass
class Quote:
    """Evidence pointer. `text` is always sliced from the source.

    `claimed` is what a judge said the passage reads (a heuristic judge
    copies it from the source; an LLM judge could invent or alter it).
    `verify()` checks the claim against the source at the span.
    """
    doc: Document
    span: Span
    node_id: str
    claimed: Optional[str] = None

    def __post_init__(self):
        if self.claimed is None:
            self.claimed = self.doc.slice(self.span)

    @classmethod
    def from_text(cls, doc: Document, text: str) -> Optional["Quote"]:
        """Locate a claimed quote in the source (whitespace-insensitive); None if absent."""
        words = text.split()
        if not words:
            return None
        m = re.search(r"\s+".join(re.escape(w) for w in words), doc.text)
        if not m:
            return None
        span = Span(m.start(), m.end())
        return cls(doc, span, doc.section_of(span.a).node_id, text)

    @property
    def text(self) -> str:
        return self.doc.slice(self.span)

    @property
    def page(self) -> int:
        return self.doc.page_at(self.span.a)

    @property
    def breadcrumb(self) -> str:
        return self.doc.by_id[self.node_id].breadcrumb

    @property
    def line(self) -> int:
        return self.doc.line_at(self.span.a) + 1

    def verify(self) -> bool:
        """True only if the source, re-read at the span, matches the claim."""
        src = self.doc.slice(self.span)
        return bool(src.strip()) and " ".join(src.split()) == " ".join((self.claimed or "").split())
