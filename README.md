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
python3 -m ppcheck pdf2txt contrat.pdf
python3 -m unittest discover -s tests -t .
```
Entrees : `.pdf`, `.md`, `.txt` (un saut de page `\f` est compte comme changement de page).
Installation : `pip install -r requirements.txt` (pypdf, necessaire uniquement pour les PDF).
`python3 -m ppcheck pdf2txt fichier.pdf` ecrit le texte extrait pour verifier l'extraction avant analyse.

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
- **Lecteur PDF (pypdf)** : PDF avec couche texte uniquement. Un PDF scanne est refuse avec un message (OCR necessaire) ;
  un PDF protege par mot de passe aussi. Les en-tetes/pieds de page repetes et les numeros de page sont retires,
  les ligatures developpees, les mots coupes en fin de ligne recolles (trait d'union conserve).
  Pas de reconnaissance des tableaux ni des colonnes multiples : verifier avec `pdf2txt`.
  Teste sur des PDF synthetiques generes par les tests et sur des PDF construits depuis `samples/` (memes resultats
  que les fichiers Markdown), **pas sur de vrais contrats** ; les exemples de `samples/` sont synthetiques.
- La detection de titres numerotes peut prendre une puce numerotee courte pour un titre.
- Le stemming est un simple prefixe de 6 lettres.

## Etapes suivantes
1. Tester le lecteur PDF sur 3 a 5 vrais documents (tableaux, colonnes, titres non numerotes).
2. Remplacer `verify.Judge` par un juge LLM qui renvoie des extraits ; `Quote.from_text` rejette les citations inventees.
3. Ajouter embeddings + re-ranking pour le rappel, garder BM25 (numeros d'articles, sigles).
4. Jeu d'evaluation etiquete (rappel, fausses absences).
5. Traiter le texte des documents comme des donnees (injection de prompt) si un LLM est branche.
