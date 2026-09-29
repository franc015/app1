import argparse
import sys
from pathlib import Path

from . import report
from .completeness import check_completeness
from .checklists import CHECKLISTS
from .document import Document
from .refs import dangling_refs
from .requirements import extract_requirements
from .verify import check


def load(path: str) -> Document:
    p = Path(path)
    if p.suffix.lower() not in {".md", ".txt"}:
        sys.exit(f"{path}: prototype reads .md/.txt only (convert PDFs to Markdown first).")
    return Document(p.stem, p.read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ppcheck", description="Compliance / completeness checks with verbatim evidence.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="verify offer against spec requirements")
    c.add_argument("spec"); c.add_argument("offer"); c.add_argument("--json", action="store_true")
    m = sub.add_parser("completeness", help="expected-clause checklist")
    m.add_argument("doc"); m.add_argument("--checklist", choices=[*CHECKLISTS, "all"], default="all")
    r = sub.add_parser("refs", help="dangling cross-references")
    r.add_argument("doc")
    o = sub.add_parser("outline", help="print the section tree")
    o.add_argument("doc")
    a = ap.parse_args(argv)

    if a.cmd == "check":
        spec, offer = load(a.spec), load(a.offer)
        res = check(extract_requirements(spec), offer)
        print(report.check_json(res) if a.json else report.check_md(res, spec, offer))
    elif a.cmd == "completeness":
        doc = load(a.doc)
        for name in (CHECKLISTS if a.checklist == "all" else [a.checklist]):
            print(report.completeness_md(check_completeness(doc, name), doc, name), "\n")
    elif a.cmd == "refs":
        doc = load(a.doc)
        print(report.refs_md(dangling_refs(doc), doc))
    else:
        doc = load(a.doc)
        for s in doc.sections:
            print(f"{'  ' * s.level}{s.node_id} L{s.level} {s.title}  [lignes {s.start_line + 1}-{s.end_line}]")


if __name__ == "__main__":
    main()
