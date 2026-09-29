"""Expected-clause checklists (regexes run on accent-folded, lowercase text, FR + EN)."""

CONTRACT = [
    ("objet", "Objet du contrat", [r"\bobjet\b", r"\bscope\b"]),
    ("duree", "Duree / entree en vigueur", [r"\bduree\b", r"\bentre en vigueur\b", r"\bprend effet\b", r"\breconduction\b", r"\bterm of\b"]),
    ("prix", "Prix / facturation", [r"\bprix\b", r"\bredevance\b", r"\bfacturation\b", r"\btarif", r"\bfees?\b"]),
    ("paiement", "Conditions de paiement", [r"\bpaiement\b", r"\breglement\b", r"\bpayment\b"]),
    ("sla", "Niveaux de service (SLA)", [r"\bsla\b", r"\bniveaux? de service\b", r"\bservice levels?\b"]),
    ("penalites", "Penalites", [r"\bpenalit", r"\bliquidated damages\b"]),
    ("recette", "Recette / reception", [r"\brecette\b", r"\breception\b", r"\bacceptance\b"]),
    ("confidentialite", "Confidentialite", [r"\bconfidentialit", r"\bconfidential\b"]),
    ("pi", "Propriete intellectuelle", [r"\bpropriete intellectuelle\b", r"\bintellectual property\b"]),
    ("responsabilite", "Responsabilite / plafond", [r"\bresponsabilit", r"\bplafon", r"\bliabilit"]),
    ("assurance", "Assurance", [r"\bassurance", r"\binsurance\b"]),
    ("sous_traitance", "Sous-traitance", [r"\bsous-?traita", r"\bsubcontract"]),
    ("donnees_perso", "Donnees personnelles (RGPD)", [r"\brgpd\b", r"\bgdpr\b", r"\bdonnees (?:a caractere )?personnelles?\b"]),
    ("force_majeure", "Force majeure", [r"\bforce majeure\b", r"\bcas fortuit"]),
    ("resiliation", "Resiliation", [r"\bresili", r"\btermination\b"]),
    ("reversibilite", "Reversibilite / restitution", [r"\breversibilit", r"\brestitution\b", r"\bexit plan\b"]),
    ("droit", "Droit applicable", [r"\bdroit applicable\b", r"\bloi applicable\b", r"\bregi par le droit\b", r"\bgoverning law\b"]),
    ("juridiction", "Juridiction competente", [r"\btribunaux?\b", r"\bjuridiction", r"\bjurisdiction\b", r"\bcompetents?\b"]),
]

SECURITY = [
    ("certif", "Certification securite (ISO 27001 / SecNumCloud / HDS)", [r"\biso\s*/?\s*(?:iec\s*)?27001\b", r"\bsecnumcloud\b", r"\bhds\b", r"\bsoc ?2\b"]),
    ("chiffrement", "Chiffrement", [r"\bchiffr", r"\bencrypt", r"\baes\b", r"\btls\b"]),
    ("acces", "Controle d'acces / authentification", [r"\bcontrole d'acces\b", r"\bauthentification\b", r"\bmfa\b", r"\bmoindre privilege\b", r"\bhabilitation", r"\baccess control\b"]),
    ("journalisation", "Journalisation / tracabilite", [r"\bjournalis", r"\blogs?\b", r"\btracabilite\b", r"\baudit trail\b"]),
    ("sauvegarde", "Sauvegarde / continuite (PCA-PRA)", [r"\bsauvegarde", r"\bpca\b", r"\bpra\b", r"\bplan de (?:continuite|reprise)\b", r"\bbackup"]),
    ("incident", "Notification d'incident de securite", [r"\bincidents?\b.{0,80}\b(?:notifi|inform|signal|declar)", r"\b(?:notifi|inform|signal|declar)\w*.{0,80}\bincidents?\b"]),
    ("localisation", "Hebergement / localisation des donnees", [r"\bheberg", r"\blocalis\w+ des donnees\b", r"\bunion europeenne\b", r"\bdata residency\b"]),
    ("audit", "Droit d'audit", [r"\baudit"]),
    ("vulnerabilites", "Gestion des vulnerabilites / tests d'intrusion", [r"\bvulnerabilit", r"\btests? d'intrusion\b", r"\bpentest", r"\bpatch"]),
    ("suppression", "Suppression / destruction des donnees", [r"\bsuppression\b", r"\bdestruction\b", r"\beffacement\b"]),
    ("sous_traitants_secu", "Securite chez les sous-traitants", [r"\bsous-?traita\w*.{0,100}\bsecurit", r"\bsecurit\w*.{0,100}\bsous-?traita"]),
]

CHECKLISTS = {"contract": CONTRACT, "security": SECURITY}
