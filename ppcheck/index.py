"""Section-aware BM25 index (breadcrumb injection, chunks stay inside sections)."""
import math
from collections import Counter
from dataclasses import dataclass
from typing import List

from .document import Document, Span
from .textutil import tokens

K1, B, CHUNK_CHARS = 1.5, 0.75, 900


@dataclass
class Chunk:
    node_id: str
    spans: List[Span]
    toks: List[str]


class Index:
    def __init__(self, doc: Document):
        self.doc = doc
        self.chunks: List[Chunk] = []
        for sec in doc.sections:
            cur, size = [], 0
            for sp in doc.sentences(sec):
                cur.append(sp)
                size += sp.b - sp.a
                if size >= CHUNK_CHARS:
                    self._add(sec, cur)
                    cur, size = [], 0
            if cur:
                self._add(sec, cur)
            if sec.start_line >= 0 and not doc.sentences(sec):
                self._add(sec, [])   # heading-only sections stay findable
        self.df = Counter()
        for c in self.chunks:
            self.df.update(set(c.toks))
        self.n = max(len(self.chunks), 1)
        self.avg = sum(len(c.toks) for c in self.chunks) / self.n or 1.0

    def _add(self, sec, spans):
        text = sec.breadcrumb + " " + " ".join(self.doc.slice(s) for s in spans)   # breadcrumb injection
        self.chunks.append(Chunk(sec.node_id, spans, tokens(text)))

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 5):
        """Top-k *sections* (deduplicated) as (node_id, score)."""
        q = tokens(query)
        best = {}
        for c in self.chunks:
            tf, score = Counter(c.toks), 0.0
            for t in q:
                if t in tf:
                    f = tf[t]
                    score += self.idf(t) * f * (K1 + 1) / (f + K1 * (1 - B + B * len(c.toks) / self.avg))
            if score > 0 and score > best.get(c.node_id, 0):
                best[c.node_id] = score
        return sorted(best.items(), key=lambda kv: -kv[1])[:k]
