"""Completeness: which expected clauses exist, with verbatim evidence."""
import re
from dataclasses import dataclass, field
from typing import List

from .checklists import CHECKLISTS
from .document import Document, Quote
from .textutil import fold

FOUND, MISSING = "PRESENT", "ABSENT"


@dataclass
class ItemResult:
    key: str
    label: str
    status: str
    quotes: List[Quote] = field(default_factory=list)


def check_completeness(doc: Document, checklist: str = "contract", max_quotes: int = 2) -> List[ItemResult]:
    units = []      # (Span, section, folded text): headings first, then body sentences
    for sec in doc.sections:
        hs = doc.heading_span(sec)
        if hs:
            units.append((hs, sec, fold(doc.slice(hs))))
        units.extend((sp, sec, fold(doc.slice(sp))) for sp in doc.sentences(sec))
    out = []
    for key, label, pats in CHECKLISTS[checklist]:
        rx = [re.compile(p) for p in pats]
        quotes, used = [], set()
        for sp, sec, txt in units:
            if any(r.search(txt) for r in rx) and sec.node_id not in used:
                q = Quote(doc, sp, sec.node_id)
                assert q.verify()
                quotes.append(q)
                used.add(sec.node_id)
                if len(quotes) == max_quotes:
                    break
        out.append(ItemResult(key, label, FOUND if quotes else MISSING, quotes))
    return out
