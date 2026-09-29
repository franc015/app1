# ppcheck - prototype de verification de conformite et de completude

Prototype en Python pur (aucune dependance, aucun LLM, aucun appel reseau) inspire de
Proxy-Pointer RAG. Il sert a tester la mecanique sur des contrats et cahiers des charges.

## Principes
- **Arbre squelette** : titres (`#`, `Article N`, `Annexe X`, `1.2 Titre`) -> sections avec fil d'Ariane (breadcrumb).
- **Pointeurs, pas de reecriture** : chaque passage cite est un intervalle de caracteres du document
  source (page, ligne, section). Le texte affiche est relu dans la source.
- **Citations verifiees** : `Quote.verify()` compare le texte annonce par un juge a la source.
  `Quote.from_text()` retrouve un extrait annonce, ou renvoie `None` s'il n'existe pas.
- **Recherche** : BM25 par sections, avec breadcrumb injecte dans les chunks.

## Commandes
```
python3 -m ppcheck outline samples/contrat.md
python3 -m ppcheck check samples/cahier_des_charges.md samples/offre.md [--json]
python3 -m ppcheck completeness samples/contrat.md --checklist contract|security|all
python3 -m ppcheck refs samples/contrat.md
python3 -m unittest discover -s tests
```
Entrees : `.md` / `.txt` (un saut de page `\f` est compte comme changement de page).

## Ce que fait chaque commande
- `check` : extrait les exigences du cahier des charges (phrases avec *doit, devra, shall...*), cherche les
  passages de l'offre les plus proches, rend CONFORME / PARTIEL / A VERIFIER / ABSENT et cite l'offre mot pour mot.
  Les valeurs chiffrees (99,9 %, 24 h, TLS 1.2...) sont comparees ; une valeur differente n'est **jamais** CONFORME.
- `completeness` : liste de clauses attendues (contrat, securite), presence avec preuve, sinon ABSENT.
- `refs` : renvois a un article/une annexe qui n'existe pas.

## Limites connues (a lire)
- **Le verdict est heuristique** (recouvrement de mots + comparaison de nombres). Il ne comprend ni les synonymes
  ("uptime" / "disponibilite"), ni le sens d'un seuil (minimum ou maximum), ni les exceptions. Un mauvais
  rapprochement est possible : toute ligne autre que CONFORME est a relire, et un CONFORME reste a echantillonner.
- **ABSENT = motif non trouve**, pas preuve d'absence. Les motifs sont FR/EN et incomplets.
- Pas de lecteur PDF : convertir d'abord en Markdown/texte (Docling, LlamaParse...). Non teste sur de vrais documents ;
  les exemples de `samples/` sont synthetiques et ecrits pour le prototype.
- La detection de titres numerotes peut prendre une puce numerotee courte pour un titre.
- Le stemming est un simple prefixe de 6 lettres.

## Etapes suivantes
1. Lecteur PDF + Markdown structure ; tester sur 3 a 5 vrais documents.
2. Remplacer `verify.Judge` par un juge LLM qui renvoie des extraits ; `Quote.from_text` rejette les citations inventees.
3. Ajouter embeddings + re-ranking pour le rappel, garder BM25 (numeros d'articles, sigles).
4. Jeu d'evaluation etiquete (rappel, fausses absences).
5. Traiter le texte des documents comme des donnees (injection de prompt) si un LLM est branche.
