"""Markdown / JSON reports."""
import json
from collections import Counter


def _one(s: str) -> str:
    return " ".join(s.split())


def _cite(q) -> str:
    return f"p.{q.page}, l.{q.line}, `{q.breadcrumb}`"


def check_md(results, spec, offer) -> str:
    c = Counter(r.status for r in results)
    L = [f"# Verification de conformite\n", f"Cahier des charges : `{spec.doc_id}` - Offre : `{offer.doc_id}`\n",
         "Resume : " + ", ".join(f"{k} {v}" for k, v in c.most_common()) + f" (sur {len(results)} exigences)\n",
         "> Verdicts heuristiques (recouvrement lexical + comparaison de valeurs). Les citations sont, elles, "
         "reprises mot pour mot du document et verifiees. Toute ligne autre que CONFORME est a relire.\n",
         "| Id | Verdict | Exigence | Passage de l'offre |", "|---|---|---|---|"]
    for r in results:
        first = _one(r.quotes[0].text)[:110] + "..." if r.quotes else "-"
        L.append(f"| {r.req.rid} | {r.status} | {_one(r.req.text)[:110]} | {first} |")
    L.append("\n## Detail\n")
    for r in results:
        L.append(f"### {r.req.rid} - {r.status} (couverture {r.coverage:.0%})")
        L.append(f"**Exigence** ({_cite(r.req.quote)}) : \"{_one(r.req.text)}\"")
        for n in r.notes:
            L.append(f"- Note : {n}")
        for q in r.quotes:
            L.append(f"- **Offre** ({_cite(q)}) : \"{_one(q.text)}\"")
        L.append("")
    return "\n".join(L)


def completeness_md(items, doc, name) -> str:
    miss = [i for i in items if i.status == "ABSENT"]
    L = [f"# Completude ({name}) - `{doc.doc_id}`\n", f"{len(items) - len(miss)}/{len(items)} elements trouves.\n",
         "> Une absence signifie : aucun motif FR/EN de la liste n'a ete trouve. A confirmer par relecture "
         "(formulation atypique possible).\n", "| Element | Statut | Preuve |", "|---|---|---|"]
    for i in items:
        ev = "; ".join(f'"{_one(q.text)[:90]}" ({_cite(q)})' for q in i.quotes) or "-"
        L.append(f"| {i.label} | {i.status} | {ev} |")
    return "\n".join(L)


def refs_md(dangling, doc) -> str:
    L = [f"# References internes - `{doc.doc_id}`\n"]
    if not dangling:
        return "\n".join(L + ["Aucune reference orpheline detectee."])
    L.append("References vers un article/une annexe introuvable :\n")
    for d in dangling:
        L.append(f"- **{d.target}** - {_cite(d.quote)} : \"{_one(d.quote.text)}\"")
    return "\n".join(L)


def check_json(results) -> str:
    return json.dumps([{
        "id": r.req.rid, "status": r.status, "coverage": round(r.coverage, 3), "notes": r.notes,
        "requirement": {"text": r.req.text, "page": r.req.quote.page, "span": [r.req.quote.span.a, r.req.quote.span.b]},
        "evidence": [{"text": q.text, "page": q.page, "breadcrumb": q.breadcrumb, "span": [q.span.a, q.span.b], "verified": q.verify()} for q in r.quotes],
    } for r in results], ensure_ascii=False, indent=2)
