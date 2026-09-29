"""Internal consistency: cross-references to articles/annexes that do not exist."""
import re
from dataclasses import dataclass
from typing import List

from .document import Document, Quote, Span
from .textutil import fold

REF = re.compile(r"\b(?:articles?|art\.)\s+(\d+(?:\.\d+)*)|\b(annexe|appendix)\s+([0-9a-z]+)\b")
EXTERNAL = re.compile(r"^\s*(?:du|de la|de l'|des|of the)\s+(?:code|loi|reglement|arrete|decret|directive)")


@dataclass
class DanglingRef:
    target: str
    quote: Quote


def dangling_refs(doc: Document) -> List[DanglingRef]:
    defined = {s.label.lower() for s in doc.sections if s.label}
    out = []
    for sec in doc.sections:
        for sp in doc.sentences(sec):
            raw = doc.slice(sp)
            folded = fold(raw)
            for m in REF.finditer(folded):
                if EXTERNAL.match(folded[m.end():m.end() + 40]):
                    continue
                target = m.group(1) if m.group(1) else f"annexe {m.group(3)}"
                if target.lower() not in defined:
                    out.append(DanglingRef(target, Quote(doc, sp, sec.node_id)))
    return out
