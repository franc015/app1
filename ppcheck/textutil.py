"""Small text helpers: accent folding, tokenisation, crude stemming, numbers."""
import re
import unicodedata

STOPWORDS = set("""
le la les l un une des du de d et ou au aux en dans par pour sur sous avec sans
ce cet cette ces se sa son ses leur leurs qui que quoi dont est sont etre a ont
avoir il elle ils elles on ne pas plus tout tous toute toutes comme afin ainsi
the a an of to and or in on for with by is are be as at this that these those
doit doivent devra devront devrait aux entre vers chez lors selon
""".split())

_APOS = str.maketrans({"’": "'", "‘": "'", " ": " ", " ": " "})


def fold(s: str) -> str:
    """Lowercase, strip accents, normalise apostrophes and whitespace."""
    s = s.translate(_APOS)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def stem(tok: str) -> str:
    # Crude prefix stemming: good enough to match 'disponibilite'/'disponible'.
    return tok[:6] if len(tok) > 6 else tok


def tokens(s: str, keep_numbers: bool = True):
    out = []
    for t in re.findall(r"[a-z0-9]+", fold(s)):
        if t in STOPWORDS:
            continue
        if t.isdigit() and not keep_numbers:
            continue
        out.append(stem(t))
    return out


_UNITS = {
    "%": "%", "h": "h", "heure": "h", "heures": "h",
    "jour": "j", "jours": "j", "mois": "mois", "an": "an", "ans": "an",
    "minute": "min", "minutes": "min", "min": "min",
    "go": "go", "to": "to", "mo": "mo", "ms": "ms",
    "€": "eur", "euro": "eur", "euros": "eur", "k€": "keur",
}
_NUM_RE = re.compile(
    r"(?<![\w.])(\d+(?:[ .]\d{3})*(?:[.,]\d+)?)\s*"
    r"(%|heures?\b|h\b|jours?\b|mois\b|ans?\b|minutes?\b|min\b|go\b|to\b|mo\b|ms\b|k?€|euros?\b)?"
)


def numbers(s: str):
    """Return the set of (value, unit) worth comparing.

    Kept: numbers with a unit, decimals, or 3+ digit numbers (27001, 256).
    """
    found = set()
    for m in _NUM_RE.finditer(fold(s).replace("€", "€")):
        raw, unit = m.group(1), m.group(2)
        val_txt = raw.replace(" ", "")
        if re.fullmatch(r"\d+(?:\.\d{3})+", val_txt):      # 1.000.000 style
            val_txt = val_txt.replace(".", "")
        val_txt = val_txt.replace(",", ".")
        try:
            val = float(val_txt)
        except ValueError:
            continue
        u = _UNITS.get(unit) if unit else None
        if u is None and not ("." in val_txt or len(val_txt.split(".")[0]) >= 3):
            continue
        found.add((val, u))
    return found


def fmt_num(v, u):
    txt = ("%g" % v).replace(".", ",")
    return f"{txt} {u}" if u else txt
