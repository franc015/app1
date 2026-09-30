# HANDOFF - Session Claude Code (cloud) -> Claude Code Desktop

Date de la session : 2026-09-29. Langue de travail de l'utilisateur : français.
Ce document résume toute la conversation. Les éléments non connus sont marqués **À vérifier**.

---

## 1. Objectif du projet

À l'origine, l'utilisateur voulait comprendre l'article *Proxy-Pointer RAG: Achieving Vectorless Accuracy at Vector RAG Scale and Cost* (Partha Sarkar, Towards Data Science, 5 avril 2026), puis savoir comment l'appliquer à son cas.

**Cas d'usage final de l'utilisateur** : documents longs (plus de 100 pages), **contrats et cahiers des charges**, avec :
- recherche de **conformité** (exigences vs offre/contrat) ;
- vérification de **complétude** (clauses attendues présentes ?) ;
- renvoi de **clauses exactes** (citations mot pour mot) ;
- **vérification de sécurité** (interprétée de deux façons, voir section 3 ; l'utilisateur n'a pas tranché : **À vérifier**).

Le livrable actuel est un **prototype** en Python pur (`ppcheck`), sans LLM, à faire évoluer.

## 2. Contexte fonctionnel et technique

### 2.1 L'article (résumé)
- PageIndex ("Vectorless RAG") construit un arbre hiérarchique de résumés LLM ; un LLM le parcourt à la requête. Très précis, mais environ 137 appels LLM par document de 131 pages (5 à 10 min/doc), peu adapté au multi-documents.
- Le RAG vectoriel classique est rapide et bon marché, mais perd la structure (chunks arbitraires).
- **Proxy-Pointer** : 5 techniques à coût nul : (1) arbre squelette par regex (sans LLM), (2) pointeurs de métadonnées (`doc_id`, `node_id`, `title`, `start_line`, `end_line`) pour renvoyer la section complète au LLM, (3) injection de breadcrumbs dans les chunks avant embedding, (4) découpage guidé par la structure (jamais à travers une section, sections < 100 caractères ignorées), (5) filtrage du bruit (sommaire, résumé exécutif, abréviations, remerciements, références).
- Benchmark de l'article : 10 requêtes sur un rapport de la Banque mondiale (131 pages) : PageIndex 2, Proxy-Pointer 4, égalités 4 (juge : Claude). Benchmark ultérieur (résumé de recherche seulement) : 66 questions sur quatre 10-K, 100 % à k=5.
- L'article suppose des documents avec des titres exploitables ; benchmarks faits par l'auteur (pas d'évaluation indépendante trouvée).

### 2.2 Dépôt officiel Proxy-Pointer (lu via l'outil de récupération web, extraits résumés, pas les fichiers entiers)
- https://github.com/Proxy-Pointer/Proxy-Pointer-RAG (MIT). 105 étoiles, 24 forks, 0 issue, 13 commits au moment de la lecture.
- Variantes : texte seul (`src/pprag_text_only/`), multimodale, comparateur de documents. CLI `pprag text index --fresh`, `pprag text ask`.
- Valeurs : `RecursiveCharacterTextSplitter`, chunk 2000 caractères, chevauchement 200, section minimale 100 caractères, breadcrumb `f"{breadcrumb} > {title}"`, embeddings `gemini-embedding-001` (1536 dim), FAISS via LangChain, LLM `gemini-3.1-flash-lite`.
- Différences avec l'article : filtre de bruit **par LLM** (JSON `noise_nodes`), et étape de **re-ranking LLM** sur les chemins (rappel k=200, liste plafonnée à 50 par `PPRAG_RERANK_LIMIT`, top 5). Constructeur d'arbre autonome (~150 lignes), sans PageIndex.
- Aucune limite de taille de contexte dans le code ; index FAISS chargé avec désérialisation pickle (ne pas charger un index de source inconnue).
- Articles de suite sur Towards Data Science (multimodal, comparateur, graphes de connaissances) : titres vus seulement, non lus.

### 2.3 Écosystème (recherche web, chiffres non tous vérifiés en ouvrant les pages)
- LightRAG ~39,8 k étoiles ; Microsoft GraphRAG ~36,1 k ; PageIndex ~23 k (mars 2026) puis ~31,8 k (mai 2026).
- Approches éprouvées sans PageIndex : parent-child (`ParentDocumentRetriever` LangChain ; `HierarchicalNodeParser` + `AutoMergingRetriever` LlamaIndex), découpage structuré (Unstructured, Docling), RAPTOR, GraphRAG/LightRAG (coûteux en LLM).
- Issues ouvertes PageIndex (12 visibles) : PDF chiffrés, nœuds frères identiques, couverture FinanceBench 50 %, demande de mises à jour incrémentales.

### 2.4 Architecture du prototype `ppcheck`
Python 3.11, **aucune dépendance obligatoire** ; `pypdf` uniquement pour lire les PDF.

| Fichier | Rôle |
|---|---|
| `ppcheck/document.py` | Modèle `Document` : texte complet, pages (séparées par `\f`), arbre de sections (`#`, `Article N`, `Annexe X`, `1.2 Titre`), breadcrumbs, `label` (numéro d'article/annexe), unités (paragraphes/puces/lignes de tableau), phrases, `Span`, `Quote` (voir 4). |
| `ppcheck/textutil.py` | `fold` (minuscules sans accents), tokens, stemming par préfixe de 6 lettres, stopwords FR/EN, extraction de nombres avec unités (`numbers`, `fmt_num`). |
| `ppcheck/index.py` | Index BM25 par sections, breadcrumb injecté dans les chunks (~900 caractères), `search` renvoie des sections dédoublonnées. |
| `ppcheck/requirements.py` | Extraction des exigences : phrases contenant doit/devra/shall/must, etc. IDs `R001`... |
| `ppcheck/verify.py` | `Judge` heuristique : candidats BM25, couverture pondérée par idf, comparaison des nombres, détection de négation ; verdicts CONFORME / PARTIEL / A VERIFIER / ABSENT. Seuils : `T_ABSENT=0.35`, `T_OK=0.60`, `MIN_GAIN=0.15`, `T_NUM=0.40`. |
| `ppcheck/checklists.py` | Listes de clauses attendues : `CONTRACT` (18) et `SECURITY` (11), motifs regex FR/EN sur texte replié. |
| `ppcheck/completeness.py` | Présence/absence de chaque clause avec citations (titres + phrases). |
| `ppcheck/refs.py` | Renvois orphelins (article/annexe inexistants) ; renvois à un code externe ignorés. |
| `ppcheck/report.py` | Rapports Markdown et JSON. |
| `ppcheck/pdfread.py` | Lecteur PDF (pypdf) : voir 4. |
| `ppcheck/cli.py`, `__main__.py`, `__init__.py` | CLI `python3 -m ppcheck ...`. |
| `samples/*.md` | Documents **synthétiques** écrits pour le prototype (cahier des charges, offre, contrat). |
| `tests/` | `test_ppcheck.py`, `test_pdf.py`, `pdfmaker.py` (mini-générateur de PDF sans dépendance), `__init__.py`. |
| `README.md`, `requirements.txt` (`pypdf>=4`), `.gitignore` | Documentation et dépendances. |

## 3. Décisions déjà prises

- **Approche recommandée à l'utilisateur** : structure d'abord (arbre de sections + breadcrumbs + pointeurs), citations reprises **mécaniquement de la source** (jamais générées par un LLM), vérification **exigence par exigence** (pas un simple top-k), rappel large + re-ranking sur les chemins, BM25 en complément des vecteurs, revue humaine des cas douteux, jeu d'évaluation étiqueté par un juriste.
- **Prototype demandé "sans ces éléments"** (sans documents réels, sans choix de LLM) : donc Python pur, heuristique, données synthétiques.
- **Choix techniques du prototype** : pas de FAISS ni d'embeddings pour l'instant (BM25 maison) ; pas de LLM ; `Judge` remplaçable par un juge LLM qui renverrait les mêmes champs ; `Quote.from_text` prévu pour rejeter les citations inventées ; ABSENT signifie "motif non trouvé", pas preuve d'absence ; une valeur chiffrée différente n'est jamais CONFORME.
- **Lecteur PDF** : pypdf, PDF avec couche texte uniquement (scans refusés, OCR non intégré), test avec un générateur PDF maison pour éviter une dépendance de test.
- **Sécurité** (deux lectures proposées à l'utilisateur, aucune confirmation reçue) : (A) sécurité du système (où partent les documents, chiffrement, contrôle d'accès, injection de prompt, cloisonnement), (B) exigences de sécurité **dans** les documents (ISO 27001, RGPD, chiffrement, notification d'incident...). Le prototype implémente (B) via la checklist `security` ; (A) n'est pas implémenté.
- Aucune PR créée, sur instruction du cadre de la session (seulement sur demande explicite).

## 4. Modifications déjà réalisées

**Git** : dépôt `franc015/app1`, branche `claude/nice-brahmagupta-07pin6`, suivie sur `origin`. Le dépôt était vide au départ (aucun commit).

| Commit | Contenu |
|---|---|
| `b93fcc3` | Prototype `ppcheck` complet (structure, index, exigences, vérification, complétude, renvois, rapports, CLI, exemples, tests, README). |
| `ebef08e` | Lecteur PDF (`pdfread.py`), commande `pdf2txt`, `requirements.txt`, tests PDF, correctif d'abréviations, message propre pour fichier introuvable, mise à jour du README. |

Les deux commits sont poussés (`git status` : branche à jour avec `origin`). Arbre de travail propre avant la création de ce fichier.

**Commandes du prototype** :
```
python3 -m ppcheck outline FICHIER
python3 -m ppcheck check SPEC OFFRE [--json]
python3 -m ppcheck completeness DOC [--checklist contract|security|all]
python3 -m ppcheck refs DOC
python3 -m ppcheck pdf2txt FICHIER.pdf [-o SORTIE]
python3 -m unittest discover -s tests -t .
```
Entrées acceptées : `.pdf`, `.md`, `.txt`.

**Détails du lecteur PDF** : pages jointes par `\f` (numéros de page dans les citations) ; suppression des lignes répétées en haut/bas d'au moins la moitié des pages (documents d'au moins 3 pages) et des numéros de page ; ligatures développées ; trait d'union de fin de ligne : lignes recollées en gardant le trait d'union ; refus explicite si PDF chiffré, illisible ou avec peu/pas de texte.

**Citations** : `Quote` porte un intervalle de caractères (`Span`) et un texte annoncé (`claimed`) ; `verify()` compare l'annoncé à la source ; `Quote.from_text()` retrouve un extrait (espaces normalisés) ou renvoie `None`.

**Résultats observés sur les exemples synthétiques** (identiques en `.md` et en PDF construit à partir des `.md`) :
- `check` : R001 A VERIFIER (99,9 % vs 99,5 %), R002 PARTIEL, R003 A VERIFIER (24 h/24 vs 9h-18h), R004 ABSENT (ISO 27001), R005 A VERIFIER (TLS 1.2 vs 1.3), R006 ABSENT (notification d'incident), R007 ABSENT (hébergement UE), R008 CONFORME, R009 CONFORME.
- `completeness --checklist contract` sur `contrat.md` : 12/18 trouvés (6 absents : recette, propriété intellectuelle, assurance, sous-traitance, force majeure, réversibilité).
- `refs` : articles 12 et 25 introuvables ; l'article 1240 du Code civil n'est pas signalé.
- Tests : 17 tests, tous OK.

## 5. Commandes exécutées (hors prototype)

- Lecture du PDF de l'article : outil de lecture refusé (`pdftoppm` absent) ; `pip install pypdf` ; puis `pip install cffi` (voir erreurs) ; extraction du texte avec pypdf (32 pages, ~31 600 caractères) dans le répertoire scratchpad de la session.
- Tentative `apt-get install -y poppler-utils` (sortie masquée, échec apparent : `which pdftotext` ne renvoie rien).
- Recherches web et lectures de pages GitHub (dépôt Proxy-Pointer, `config.py`, `build_pp_index.py`, `pp_rag_bot.py`, issues PageIndex, README brut).
- Création de fichiers, `python3 -m unittest`, `git add/commit/push -u origin claude/nice-brahmagupta-07pin6` (deux fois), génération de PDF de test dans le scratchpad (non versionnés).

## 6. Erreurs rencontrées et résolutions

| Erreur | Résolution |
|---|---|
| Lecture PDF impossible (`pdftoppm` absent, aucune bibliothèque PDF Python) | Mode plan actif : question posée à l'utilisateur ; après sa réponse, sortie du mode plan et installation de pypdf. |
| pypdf : panique `_cffi_backend` (bibliothèque `cryptography` système cassée) | `pip install cffi` a résolu le problème **dans ce conteneur**. **À vérifier** sur la machine de l'utilisateur. |
| `apt-get install poppler-utils` sans effet visible | Contourné avec pypdf. |
| Sites bloqués par le proxy du conteneur : `towardsdatascience.com`, `groundingnodes.com`, `sjramblings.io`, `florinelchis.medium.com` | Contenu non lu ; on s'est appuyé sur les résumés de recherche et le dépôt GitHub. |
| Faux positif de complétude : un CONFORME trompeur sur "notification d'incident" (union de deux passages sans rapport) | Le 2e passage doit être dans la **même section** que le 1er et apporter des termes nouveaux ; `T_ABSENT` remonté de 0,30 à 0,35 ; bruit des nombres sans unité réduit. |
| `Quote.verify()` ne vérifiait rien (comparaison du texte à lui-même) | Ajout du champ `claimed` et de `Quote.from_text` ; tests correspondants. |
| Clause "juridiction" déclarée absente alors que le contrat dit "tribunaux" | Motif corrigé (`tribunaux?`, `competents?`). |
| Test cassé (`sections[3]` sans phrase) | Test réécrit avec la section ciblée par titre. |
| Renvoi "(art. 40)" non détecté : phrase coupée après "(art." | Abréviations reconnues même entre parenthèses (`re.sub(r"\W", "", ...)`) + test. |
| Validation PDF manuelle faussée par mon script (lignes tronquées à 95 caractères) | Refait avec `textwrap` ; résultats identiques au Markdown. |
| Découverte tests : `unittest discover -s tests` ne trouve pas `tests.pdfmaker` | Lancer avec `-t .` (`python3 -m unittest discover -s tests -t .`). |
| Rectificatif : j'avais annoncé 7 clauses absentes sur 18 dans le contrat d'exemple | Le bon chiffre est 6 (après correction du motif "juridiction"). |

## 7. Tâches restantes

1. Tester le lecteur PDF sur **3 à 5 vrais documents** (tableaux, colonnes multiples, titres non numérotés, contrats scannés).
2. Brancher un **juge LLM** à la place du juge heuristique (modèle autorisé pour données sensibles à choisir : **À vérifier** avec l'utilisateur) ; utiliser `Quote.from_text` pour rejeter les citations inventées.
3. Ajouter embeddings + re-ranking pour le rappel (garder BM25 pour les numéros d'articles et sigles).
4. Construire un **jeu d'évaluation étiqueté** (50 à 100 vérifications) : rappel, exactitude des citations, taux de fausses absences.
5. Traiter le texte des documents comme des **données** (injection de prompt) dès qu'un LLM est branché ; limiter ses droits.
6. Prévoir l'OCR pour les PDF scannés (non fait).
7. Gestion des sections très longues (plafond de contexte / repli sur sous-nœuds) : non implémentée.
8. Sécurité du système (option A section 3) : chiffrement au repos, contrôle d'accès, journalisation, cloisonnement : non implémentée.
9. Améliorations possibles : détection des titres non numérotés, seuils sens (minimum/maximum), synonymes.
10. Si souhaité : créer une **pull request** (non demandé jusqu'ici).

## 8. Points à vérifier

- **PR** : l'utilisateur a dit "Je vérifie la PR". Aucune PR n'a été créée par cette session. **À vérifier** s'il s'agit d'une PR ouverte de son côté.
- Le fichier PDF de l'article est dans `/root/.claude/uploads/15b6b364-668e-58ad-8e34-2e80e6704af0/` du conteneur cloud (**pas dans le dépôt**, probablement absent de la session Desktop). Le texte extrait était dans le scratchpad du conteneur (non versionné).
- Le plan de session `/root/.claude/plans/root-claude-uploads-15b6b364-668e-58ad-wiggly-milner.md` existe dans le conteneur uniquement (non versionné, non essentiel).
- Interprétation de "vérification de sécurité" (A système vs B contenu des documents) : **À vérifier** avec l'utilisateur.
- Langue et nature des vrais documents (PDF natifs ou scans ? FR/EN ? volume ? mises à jour ?), type de questions (clause précise, comparaison entre contrats, conformité d'un cahier des charges vs offre) et **LLM autorisé** (API ou local) : questions posées, **aucune réponse reçue**.
- Chiffres d'étoiles GitHub : issus de résultats de recherche, non tous confirmés en ouvrant les pages.
- `pypdf` sur la machine cible : installer via `pip install -r requirements.txt` ; l'erreur `cffi` est **À vérifier** localement.
- Le lecteur PDF n'a été testé que sur des PDF synthétiques simples (police Helvetica, une colonne).
- La suppression des en-têtes/pieds de page peut retirer à tort une ligne légitime répétée en haut/bas de page.
- Une puce numérotée courte peut être prise pour un titre (détection par regex).
- Statut de poppler-utils : non installé dans le conteneur ; **À vérifier** ailleurs.

## 9. Prochaine action recommandée

1. Cloner le dépôt et basculer sur la branche :
   ```
   git clone https://github.com/franc015/app1.git
   cd app1 && git checkout claude/nice-brahmagupta-07pin6
   pip install -r requirements.txt
   python3 -m unittest discover -s tests -t .
   python3 -m ppcheck check samples/cahier_des_charges.md samples/offre.md
   ```
2. Fournir 1 à 3 **vrais PDF** (anonymisés si besoin) et exécuter `python3 -m ppcheck pdf2txt fichier.pdf` pour contrôler l'extraction, puis `outline`, `completeness`, `refs`.
3. Répondre aux questions ouvertes de la section 8 (type de PDF, langue, volume, LLM autorisé, sens de "sécurité"), puis décider : brancher le juge LLM (tâche 2) ou d'abord le jeu d'évaluation (tâche 4). **Recommandation** : commencer par le test sur vrais documents, puis le jeu d'évaluation, avant d'ajouter un LLM.

## 10. Notes pour la reprise dans Claude Desktop

- Les commits sont sur `origin/claude/nice-brahmagupta-07pin6` ; le travail n'est pas fusionné dans une branche principale (la branche principale du dépôt : **À vérifier**).
- Respecter la contrainte de la session : ne pas créer de PR sans demande explicite.
- Ne pas inclure d'identifiant de modèle dans les commits, PR ou fichiers du dépôt.
- Les commits de la session portent un trailer `Co-Authored-By` (Claude) et un trailer `Claude-Session` (lien de la session cloud `session_0157bP12DqiLxdHpemDXcCJQ`). À adapter à la nouvelle session (**À vérifier**).
