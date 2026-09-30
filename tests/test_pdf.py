import tempfile
import unittest
from pathlib import Path

from ppcheck.document import Document
from ppcheck.pdfread import PdfError, clean_page, read_pdf, strip_running_lines
from ppcheck.refs import dangling_refs
from tests.pdfmaker import make_pdf


def header(n):
    return ["Contrat Exemple - Confidentiel", ""], [f"Page {n} / 3"]


def build(tmp):
    bodies = [
        ["Article 1 - Objet", "Le present contrat a pour objet la fourniture d'un service heberge.", "Il est regi par l'article 9."],
        ["Article 2 - Duree", "Le contrat prend effet pour 36 mois. Le sous-", "traitant est tenu de respecter l'article 2."],
        ["Article 3 - Resiliation", "Chaque partie peut resilier en cas de manquement grave (art. 40)."],
    ]
    pages = []
    for i, b in enumerate(bodies, 1):
        h, f = header(i)
        pages.append(h + b + [""] + f)
    p = Path(tmp) / "contrat.pdf"
    p.write_bytes(make_pdf(pages))
    return p


class PdfReadTests(unittest.TestCase):
    def test_pages_headers_footers_and_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = read_pdf(build(tmp))
        self.assertEqual(text.count("\f"), 2)                       # 3 pages
        self.assertNotIn("Confidentiel", text)                       # running header removed
        self.assertNotIn("Page 1 / 3", text)                         # page number removed
        self.assertIn("sous-traitant est tenu", text)                # line-end hyphen joined, hyphen kept
        doc = Document("contrat", text)
        titles = [s.title for s in doc.sections[1:]]
        self.assertEqual(titles, ["Article 1 - Objet", "Article 2 - Duree", "Article 3 - Resiliation"])
        art3 = doc.sections[3]
        self.assertEqual(doc.page_at(doc.heading_span(art3).a), 3)

    def test_dangling_refs_on_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Document("c", read_pdf(build(tmp)))
        found = sorted(d.target for d in dangling_refs(doc))
        self.assertEqual(found, ["40", "9"])                          # 'art. 40' and 'article 9' do not exist

    def test_scanned_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "scan.pdf"
            p.write_bytes(make_pdf([[], []]))
            with self.assertRaises(PdfError):
                read_pdf(p)

    def test_garbage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.pdf"
            p.write_bytes(b"not a pdf")
            with self.assertRaises(PdfError):
                read_pdf(p)

    def test_helpers(self):
        self.assertEqual(clean_page("ﬁn de contrat"), "fin de contrat")
        pages = ["Hdr 1\ntexte a\n1", "Hdr 2\ntexte b\n2", "Hdr 3\ntexte c\n3"]
        self.assertEqual(strip_running_lines(pages), ["texte a", "texte b", "texte c"])


if __name__ == "__main__":
    unittest.main()
