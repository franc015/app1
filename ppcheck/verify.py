"""Requirement-by-requirement verification against an offer/contract.

Pipeline per requirement: wide recall (BM25 over sections) -> best sentences
-> heuristic verdict -> verbatim, machine-verified quotes.
The verdict logic is a deliberately simple, replaceable heuristic
(see `Judge`); the evidence handling is what must stay strict.
"""
import re
from dataclasses import dataclass, field
from typing import List

from .document import Document, Quote
from .index import Index
from .requirements import Requirement
from .textutil import fmt_num, fold, numbers, stem, tokens

T_ABSENT, T_OK, MIN_GAIN, T_NUM = 0.35, 0.60, 0.15, 0.40
NEGATION = re.compile(r"\b(ne \w+ pas|sans|hors|exclu\w*|excepte\w*|not|except|excluding)\b")

CONFORME, PARTIEL, A_VERIFIER, ABSENT = "CONFORME", "PARTIEL", "A VERIFIER", "ABSENT"


@dataclass
class Result:
    req: Requirement
    status: str
    coverage: float
    quotes: List[Quote] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class Judge:
    """Heuristic judge. Swap for an LLM judge that returns the same fields."""

    def __init__(self, offer: Document, k_sections: int = 8):
        self.offer, self.index, self.k = offer, Index(offer), k_sections

    def _cands(self, req: Requirement):
        """Sentences of the top sections, scored by weighted term coverage."""
        q_terms = [t for t in dict.fromkeys(tokens(req.text, keep_numbers=False))]
        total = sum(self.index.idf(t) for t in q_terms) or 1.0
        out = []
        for node_id, _ in self.index.search(req.text, self.k):
            sec = self.offer.by_id[node_id]
            for sp in self.offer.sentences(sec):
                st = set(tokens(self.offer.slice(sp), keep_numbers=False)) | set(tokens(sec.title, keep_numbers=False))
                cov = sum(self.index.idf(t) for t in q_terms if t in st) / total
                out.append((cov, sp, sec))
        out.sort(key=lambda x: -x[0])
        return out

    def judge(self, req: Requirement) -> Result:
        cands = self._cands(req)
        if not cands or cands[0][0] < T_ABSENT:
            return Result(req, ABSENT, cands[0][0] if cands else 0.0,
                          notes=["aucun passage suffisamment proche dans l'offre"])
        q_terms = list(dict.fromkeys(tokens(req.text, keep_numbers=False)))
        total = sum(self.index.idf(t) for t in q_terms) or 1.0

        def terms(cov_item):
            _, sp, sec = cov_item
            return set(tokens(self.offer.slice(sp), keep_numbers=False)) | set(tokens(sec.title, keep_numbers=False))

        top, seen = [cands[0]], terms(cands[0])
        for item in cands[1:]:          # 2nd passage: same section, and only if it brings new query terms
            if item[2].node_id != cands[0][2].node_id:
                continue
            gain = sum(self.index.idf(t) for t in q_terms if t in terms(item) and t not in seen) / total
            if gain >= MIN_GAIN:
                top.append(item)
                seen |= terms(item)
                break
        cov = sum(self.index.idf(t) for t in q_terms if t in seen) / total
        quotes = [Quote(self.offer, sp, sec.node_id) for _, sp, sec in top]
        notes, status = [], CONFORME if cov >= T_OK else PARTIEL

        want = numbers(req.text)
        have = set().union(*(numbers(q.text) for q in quotes))
        for v, u in sorted(want, key=str):
            if any(v == hv and (u is None or hu is None or u == hu) for hv, hu in have):
                continue
            same_unit = [hv for hv, hu in have if hu == u and hv != v and (u is not None or hv != int(hv))]
            if same_unit and cov >= T_NUM:
                notes.append(f"valeur differente : exigence {fmt_num(v, u)}, offre {', '.join(fmt_num(x, u) for x in sorted(same_unit))}")
                status = A_VERIFIER
            else:
                notes.append(f"valeur {fmt_num(v, u)} non retrouvee dans les passages cites")
                if status == CONFORME:
                    status = PARTIEL
        offer_txt = fold(" ".join(q.text for q in quotes))
        if NEGATION.search(offer_txt) and not NEGATION.search(fold(req.text)):
            notes.append("negation/exclusion dans le passage : relire")
            if status == CONFORME:
                status = A_VERIFIER
        for q in quotes:
            assert q.verify(), "quote does not match source"
        return Result(req, status, cov, quotes, notes)


def check(spec_reqs: List[Requirement], offer: Document, judge=None) -> List[Result]:
    judge = judge or Judge(offer)
    return [judge.judge(r) for r in spec_reqs]
