import unittest
from pathlib import Path

from ppcheck.checklists import CHECKLISTS
from ppcheck.completeness import check_completeness
from ppcheck.document import Document, Quote, Span
from ppcheck.refs import dangling_refs
from ppcheck.requirements import extract_requirements
from ppcheck.verify import ABSENT, A_VERIFIER, CONFORME, check

S = Path(__file__).resolve().parent.parent / "samples"


def load(name):
    return Document(name, (S / name).read_text(encoding="utf-8"))


class StructureTests(unittest.TestCase):
    def test_breadcrumb_and_articles(self):
        d = load("contrat.md")
        art = next(s for s in d.sections if s.title.startswith("Article 5"))
        self.assertEqual(art.breadcrumb, "Contrat de prestation de services > Article 5 - Confidentialite")
        self.assertEqual(art.label, "5")

    def test_pages_from_form_feed(self):
        d = Document("x", "# T\n\n## A\ntexte un.\f## B\ntexte deux.")
        b = next(s for s in d.sections if s.title == "B")
        sp = d.sentences(b)[0]
        self.assertEqual(d.page_at(sp.a), 2)
        self.assertEqual(d.slice(sp), "texte deux.")

    def test_abbreviation_not_split(self):
        d = Document("x", "# T\nVoir art. 12 pour le detail. Autre phrase.")
        sents = [d.slice(s) for s in d.sentences(d.sections[1])]
        self.assertEqual(sents, ["Voir art. 12 pour le detail.", "Autre phrase."])

    def test_quote_verify_detects_altered_claim(self):
        d = load("offre.md")
        sec = next(x for x in d.sections if x.title.startswith("2.1"))
        sp = d.sentences(sec)[0]
        self.assertTrue(Quote(d, sp, sec.node_id).verify())
        self.assertFalse(Quote(d, sp, sec.node_id, claimed="disponibilite de 99,99 %").verify())
        self.assertFalse(Quote(d, Span(0, 0), sec.node_id, claimed="x").verify())

    def test_from_text_finds_only_real_text(self):
        d = load("offre.md")
        q = Quote.from_text(d, "Les donnees sont chiffrees   au repos (AES-256)")
        self.assertIsNotNone(q)
        self.assertTrue(q.verify())
        self.assertEqual(q.breadcrumb.split(" > ")[-1], "3.1 Chiffrement")
        self.assertIsNone(Quote.from_text(d, "Les donnees sont chiffrees au repos (AES-512)"))


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.reqs = extract_requirements(load("cahier_des_charges.md"))
        self.res = {r.req.rid: r for r in check(self.reqs, load("offre.md"))}

    def test_requirement_count(self):
        self.assertEqual(len(self.reqs), 9)

    def test_verdicts(self):
        self.assertEqual(self.res["R001"].status, A_VERIFIER)   # 99,9 % vs 99,5 %
        self.assertEqual(self.res["R004"].status, ABSENT)       # ISO 27001 missing
        self.assertEqual(self.res["R006"].status, ABSENT)       # incident notification missing
        self.assertEqual(self.res["R007"].status, ABSENT)       # EU hosting not stated
        self.assertEqual(self.res["R008"].status, CONFORME)
        self.assertEqual(self.res["R009"].status, CONFORME)

    def test_never_conforme_when_number_differs(self):
        for rid in ("R001", "R003", "R005"):
            self.assertNotEqual(self.res[rid].status, CONFORME)

    def test_all_quotes_verbatim(self):
        for r in self.res.values():
            for q in r.quotes:
                self.assertTrue(q.verify())
                self.assertIn(q.text, q.doc.text)


class CompletenessTests(unittest.TestCase):
    def test_contract(self):
        items = {i.key: i for i in check_completeness(load("contrat.md"), "contract")}
        for k in ("force_majeure", "reversibilite", "assurance", "sous_traitance", "pi"):
            self.assertEqual(items[k].status, "ABSENT", k)
        for k in ("objet", "resiliation", "juridiction", "droit"):
            self.assertEqual(items[k].status, "PRESENT", k)

    def test_all_checklists_have_patterns(self):
        for name, items in CHECKLISTS.items():
            for key, label, pats in items:
                self.assertTrue(pats, (name, key))

    def test_dangling_refs(self):
        targets = sorted(d.target for d in dangling_refs(load("contrat.md")))
        self.assertEqual(targets, ["12", "25"])      # Code civil article 1240 is external


if __name__ == "__main__":
    unittest.main()
