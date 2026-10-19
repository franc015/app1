"""Affichage des donnees de session et du contexte Claude Code.

Source : le journal de session (JSONL) ecrit par Claude Code dans
~/.claude/projects/<projet>/<session>.jsonl, plus quelques variables d'environnement
non sensibles (liste blanche : aucun jeton, aucun e-mail).
"""
import json
import os
from pathlib import Path

ENV_KEYS = [
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_REMOTE_SESSION_ID", "CLAUDE_CODE_VERSION",
    "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE", "CLAUDE_EFFORT",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
]


class SessionError(Exception):
    pass


def find_transcript(session_id=None, root=None):
    root = Path(root) if root else Path.home() / ".claude" / "projects"
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if session_id:
        hits = list(root.glob(f"*/{session_id}.jsonl"))
        if hits:
            return hits[0]
        raise SessionError(f"journal introuvable pour la session {session_id} dans {root}")
    hits = sorted(root.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not hits:
        raise SessionError(f"aucun journal de session dans {root}")
    return hits[-1]


def _text(content):
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def load(path) -> dict:
    """Resume un journal JSONL : identite, modele, messages, jetons, contexte courant."""
    info = {"fichier": str(path), "messages": {"user": 0, "assistant": 0}, "outils": {},
            "jetons": {"entree": 0, "cache_lecture": 0, "cache_ecriture": 0, "sortie": 0},
            "modeles": [], "contexte": None, "par_modele": {}}
    seen = set()
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        raise SessionError(f"{path}: {e.strerror}")
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        for src, dst in (("sessionId", "session_id"), ("version", "version"), ("cwd", "cwd"),
                         ("gitBranch", "branche"), ("entrypoint", "point_entree"), ("effort", "effort")):
            if d.get(src):
                info[dst] = d[src]
        if d.get("timestamp"):
            info.setdefault("debut", d["timestamp"])
            info["fin"] = d["timestamp"]
        t, m = d.get("type"), d.get("message")
        if t not in ("user", "assistant") or not isinstance(m, dict):
            continue
        info["messages"][t] += 1
        if t == "assistant":
            if m.get("model") and m["model"] not in info["modeles"]:
                info["modeles"].append(m["model"])
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    info["outils"][b["name"]] = info["outils"].get(b["name"], 0) + 1
            u = m.get("usage")
            key = d.get("requestId") or d.get("uuid")
            if u and key not in seen:
                seen.add(key)
                j = info["jetons"]
                pm = info["par_modele"].setdefault(m.get("model") or "?", {"requetes": 0, **dict.fromkeys(j, 0)})
                pm["requetes"] += 1
                pm["entree"] += u.get("input_tokens", 0)
                pm["cache_lecture"] += u.get("cache_read_input_tokens", 0)
                pm["cache_ecriture"] += u.get("cache_creation_input_tokens", 0)
                pm["sortie"] += u.get("output_tokens", 0)
                j["entree"] += u.get("input_tokens", 0)
                j["cache_lecture"] += u.get("cache_read_input_tokens", 0)
                j["cache_ecriture"] += u.get("cache_creation_input_tokens", 0)
                j["sortie"] += u.get("output_tokens", 0)
                info["contexte"] = (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                                    + u.get("cache_creation_input_tokens", 0))
    info["env"] = {k: os.environ[k] for k in ENV_KEYS if k in os.environ}
    return info


def _n(v):
    return f"{v:,}".replace(",", " ")


def render(info: dict, window=None) -> str:
    out = ["# Session Claude Code", ""]
    rows = [("Session", info.get("session_id")), ("Version", info.get("version")),
            ("Point d'entree", info.get("point_entree")), ("Repertoire", info.get("cwd")),
            ("Branche git", info.get("branche")), ("Niveau d'effort", info.get("effort")),
            ("Debut", info.get("debut")), ("Dernier evenement", info.get("fin")),
            ("Modele(s)", ", ".join(info["modeles"]) or None)]
    out += [f"- **{k}** : {v}" for k, v in rows if v]
    m = info["messages"]
    out += ["", "## Messages", f"- utilisateur : {m['user']}", f"- assistant : {m['assistant']}"]
    out += ["", "## Contexte", ]
    if info["contexte"] is None:
        out.append("- aucune donnee d'utilisation dans le journal")
    else:
        c = info["contexte"]
        line = f"- jetons envoyes au dernier tour : {c:,}".replace(",", " ")
        if window:
            line += f" / {window:,} ({100 * c / window:.1f} %)".replace(",", " ")
        out.append(line)
    j = info["jetons"]
    out += ["", "## Jetons cumules (par requete distincte)"]
    out += [f"- {k.replace('_', ' ')} : {v:,}".replace(",", " ") for k, v in j.items()]
    entrants = j["entree"] + j["cache_lecture"] + j["cache_ecriture"]
    out += [f"- **total entrant** : {_n(entrants)}", f"- **total (entrant + sortie)** : {_n(entrants + j['sortie'])}"]
    if entrants:
        out.append(f"- part servie par le cache : {100 * j['cache_lecture'] / entrants:.1f} %")
    if len(info["par_modele"]) > 0:
        out += ["", "## Par modele", "", "| Modele | Requetes | Entree | Cache lect. | Cache ecr. | Sortie |", "|---|---|---|---|---|---|"]
        for k, v in info["par_modele"].items():
            out.append(f"| {k} | {v['requetes']} | {_n(v['entree'])} | {_n(v['cache_lecture'])} | {_n(v['cache_ecriture'])} | {_n(v['sortie'])} |")
    if info["outils"]:
        out += ["", "## Appels d'outils"]
        out += [f"- {k} : {v}" for k, v in sorted(info["outils"].items(), key=lambda kv: -kv[1])]
    if info["env"]:
        out += ["", "## Environnement (liste blanche)"]
        out += [f"- {k}={v}" for k, v in info["env"].items()]
    out += ["", f"Source : `{info['fichier']}`"]
    return "\n".join(out)
