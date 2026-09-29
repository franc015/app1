"""Extract normative requirements ('doit', 'devra', 'shall'...) from a spec."""
import re
from dataclasses import dataclass
from typing import List

from .document import Document, Quote
from .textutil import fold

NORMATIVE = re.compile(
    r"\b(doit|doivent|devra|devront|est tenu|sont tenus|s'engage|s'engagent|"
    r"obligatoire|exige|exiges|requis|imperatif|shall|must|is required|are required)\b"
)


@dataclass
class Requirement:
    rid: str
    quote: Quote

    @property
    def text(self) -> str:
        return " ".join(self.quote.text.split())


def extract_requirements(doc: Document) -> List[Requirement]:
    reqs = []
    for sec in doc.sections:
        for sp in doc.sentences(sec):
            if NORMATIVE.search(fold(doc.slice(sp))):
                reqs.append(Requirement(f"R{len(reqs) + 1:03d}", Quote(doc, sp, sec.node_id)))
    return reqs
