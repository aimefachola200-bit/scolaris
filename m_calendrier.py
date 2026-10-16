# -*- coding: utf-8 -*-
"""
Calendrier scolaire officiel et thèmes d'unité pédagogique (UP), conférences pédagogiques et formations
groupées — rubriques du tableau synoptique (toutes éditions).

* **Calendrier scolaire** (table `calendrier_officiel_lignes`, par école et par année scolaire) : périodes,
  congés, jours fériés. Préchargé pour 2026-2027 avec l'arrêté interministériel N°017/MEMP/MES/MESRS-FT/…
  du 28 juillet 2026 ; modifiable (ajouter, modifier, supprimer), import / export Excel, PDF, réinitialisation.
  Pour une autre année scolaire, le tableau est vide : on le renseigne (ou on l'importe) à chaque rentrée.
* **Thèmes d'UP** (table `themes_up_lignes`) : planning d'exécution des thèmes d'unité pédagogique 2026-2027
  (maternelle, primaire), thèmes de conférences pédagogiques et de formations groupées (DIIP, MEMP).
  Mêmes onglets : ajouter, modifier, supprimer, import / export Excel, PDF, réinitialiser.

**Demi-journées de classe** : le calendrier sert à compter les jours et demi-journées de classe de l'année
(`demi_journees()`). Une ligne « période de classe » (les trimestres) est comptée du lundi au vendredi ; sont retirés
les congés qui la recoupent (le jour où un congé commence « après les cours » reste un jour de classe) et les jours
fériés tombant un jour ouvré. Un jour = 2 demi-journées (matin, après-midi) ; l'emploi du temps officiel du primaire
laisse le mercredi après-midi libre : le total « emploi du temps du primaire » en tient compte.

Fonctions partagées (autres modules, transmission CS) :
`H.calendrier_officiel(annee=None, ecole_id=None)` -> liste de périodes / événements ;
`H.demi_journees(annee=None, ecole_id=None)` -> dict de comptage (jours, demi-journées, détail par période) ;
`H.themes_up(annee=None, ecole_id=None)` -> liste de thèmes (n°, thème, axes, dates préparation /
interprétation / administration, observations).
Droits : lecture pour tout utilisateur connecté ; écriture avec le droit `synoptique`.
"""
import io
import re
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, url_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS calendrier_officiel_lignes (
    id INTEGER PRIMARY KEY,
    ecole_id INTEGER NOT NULL,
    annee TEXT NOT NULL,
    ordre INTEGER DEFAULT 0,
    categorie TEXT NOT NULL,              -- periode | conge | ferie | autre
    intitule TEXT NOT NULL,
    debut TEXT,                           -- AAAA-MM-JJ
    fin TEXT,
    duree TEXT,
    observations TEXT,
    classe INTEGER DEFAULT 0,             -- 1 = période de classe (comptée dans les demi-journées)
    maj TEXT, maj_par INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cal_off ON calendrier_officiel_lignes (ecole_id, annee);
CREATE TABLE IF NOT EXISTS themes_up_lignes (
    id INTEGER PRIMARY KEY,
    ecole_id INTEGER NOT NULL,
    annee TEXT NOT NULL,
    ordre INTEGER DEFAULT 0,
    categorie TEXT NOT NULL,              -- maternelle | primaire | conference | formation
    numero TEXT,
    theme TEXT NOT NULL,
    axes TEXT,
    preparation TEXT,
    interpretation TEXT,
    administration TEXT,
    observations TEXT,
    maj TEXT, maj_par INTEGER
);
CREATE INDEX IF NOT EXISTS idx_themes_up ON themes_up_lignes (ecole_id, annee);
"""

CATEGORIES_CAL = {"periode": "Période de travail", "conge": "Congés / vacances", "ferie": "Fête / jour férié",
                  "autre": "Autre événement"}
CATEGORIES_UP = {"maternelle": "Unité pédagogique — Maternelle", "primaire": "Unité pédagogique — Primaire",
                 "conference": "Conférences pédagogiques", "formation": "Formations groupées"}
ANNEE_OFFICIELLE = "2026-2027"
SOURCE_CAL = ("Arrêté interministériel année 2026 N°017/MEMP/MES/MESRS-FT/DC/SGM/DIIP/DEP/DEM/DEC/IGPM/DESG/DESTFP/"
              "SA 015SGG26 du 28 juillet 2026 fixant le calendrier de l'année scolaire 2026-2027")
SOURCE_UP = ("MEMP — Direction de l'Inspection et de l'Innovation Pédagogiques : planning d'exécution des thèmes d'unité "
             "pédagogique, de conférence pédagogique et de formation groupée au titre de l'année scolaire 2026-2027")

# (catégorie, intitulé, début, fin, durée, observations)
CALENDRIER_2026_2027 = [
    ("periode", "Pré-rentrée scolaire", "2026-09-07", "2026-09-11", "1 semaine", ""),
    ("periode", "Premier trimestre", "2026-09-14", "2026-12-18", "14 semaines de travail", "Jusqu'à la fin des cours de l'après-midi"),
    ("conge", "Congés de fin du premier trimestre", "2026-12-18", "2027-01-03", "2 semaines", "À partir de la fin des cours de l'après-midi du 18/12/2026"),
    ("periode", "Deuxième trimestre", "2027-01-04", "2027-03-24", "10 semaines 3 jours de travail", "Jusqu'à la fin des cours"),
    ("conge", "Congés de détente", "2027-02-19", "2027-02-28", "1 semaine", "À partir de la fin des cours de l'après-midi du 19/02/2027"),
    ("conge", "Congés de fin du deuxième trimestre", "2027-03-24", "2027-04-07", "2 semaines", "À partir de la fin des cours du 24/03/2027"),
    ("periode", "Troisième trimestre", "2027-04-08", "2027-06-25", "11 semaines 2 jours de travail", "Jusqu'à la fin des cours de l'après-midi"),
    ("conge", "Grandes vacances", "2027-06-25", "2027-09-12", "", "À partir de la fin des cours de l'après-midi du 25/06/2027"),
    ("periode", "Reprise des activités pédagogiques 2027-2028", "2027-09-13", "2027-09-13", "", "Article 3 de l'arrêté"),
    ("ferie", "Fête des cultes et traditions du Bénin", "2027-01-07", "2027-01-08", "", "Jeudi 07 et vendredi 08 janvier 2027"),
    ("ferie", "Fête de l'Ascension", "2027-05-06", "2027-05-06", "", "Jeudi"),
    ("ferie", "Lundi de Pentecôte", "2027-05-17", "2027-05-17", "", "Lundi"),
]

_AX_COMMUN_2 = ("Clarification conceptuelle ; Typologie des « voleurs de temps » ; Diagnostic des facteurs chronophages ; "
                "Leviers organisationnels, pédagogiques, institutionnels et recommandations pratiques")
_AX_DIFF = ("Clarification conceptuelle ; Principes de la pédagogie différenciée ; Stratégies d'adaptation pédagogique "
            "(méthodes actives, supports variés, évaluation adaptée) ; Technologies d'assistance (tablettes, logiciels "
            "spécialisés, etc.) ; Gestion de la diversité et valorisation des talents de tous")
_TITRE_2 = ("Chasser les facteurs chronophages à l'école : stratégies organisationnelles et pédagogiques au service de la "
            "réussite scolaire")
_TITRE_4 = "La pédagogie différenciée et l'adaptation des pratiques en classe inclusive"
_DATES = ["09/10/2026", "23/10/2026", "06/11/2026", "20/11/2026", "04/12/2026", "15/01/2027", "29/01/2027",
          "12/02/2027", "05/03/2027", "19/03/2027", "23/04/2027", "07/05/2027"]
_IMPL = "Implications pédagogiques"
_CLAR = "Clarification conceptuelle"

# (n°, thème, axes, observation)
THEMES_MATERNELLE = [
    ("1", "Renouvellement des bureaux", "", ""),
    ("2", _TITRE_2, _AX_COMMUN_2, "Animation libre"),
    ("3", "Le projet pédagogique à l'enseignement maternel : élaboration et mise en œuvre",
     f"{_CLAR} ; Intérêt du projet pédagogique à l'EM ; Étapes d'élaboration d'un projet pédagogique ; Démarche de mise en œuvre ; {_IMPL}",
     "Animation libre"),
    ("4", _TITRE_4, _AX_DIFF, "Animation libre"),
    ("5", "Impact de l'utilisation du coin bibliothèque sur le développement cognitif de l'enfant",
     f"{_CLAR} ; Importance de l'exploitation du coin bibliothèque ; Aménagement et accessibilité du coin bibliothèque ; "
     "Rôle de l'enseignant dans l'animation du coin bibliothèque ; Impact du coin bibliothèque dans le développement "
     "socio-cognitif de l'enfant", "Animation mixte"),
    ("6", "La place du matériel dans la mise en œuvre de l'Observation à l'EM",
     f"{_CLAR} ; Importance du matériel dans la mise en œuvre de l'Observation ; Choix et préparation du matériel en "
     "fonction des objectifs de l'activité ; Utilisation du matériel par l'enfant au cours de l'activité ; Rôle de "
     "l'enseignant dans l'exploitation du matériel", "Animation libre"),
    ("7", "Les activités de vie pratique à l'EM : fondements et démarche de mise en œuvre",
     f"{_CLAR} ; Fondements et objectifs des activités de vie pratique ; Typologie des activités de vie pratique ; "
     f"Démarche de mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("8", "La satisfaction des besoins de l'enfant à l'EM : enjeux, difficultés et approches de solution",
     f"{_CLAR} ; Besoins fondamentaux de l'enfant à la maternelle ; Nécessité de la prise en compte des besoins "
     "fondamentaux de l'enfant ; Difficultés liées à la satisfaction des besoins de l'enfant ; Approches de solution "
     "pour une prise en charge efficace des besoins fondamentaux de l'enfant", "Animation libre"),
    ("9", "La dramatisation du conte à l'EM : démarche de mise en œuvre",
     f"{_CLAR} ; Importance de la dramatisation dans le développement du langage et de l'imaginaire de l'enfant ; "
     f"Étapes de la dramatisation d'un conte ; Démarche de mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("10", "Le jeu comme levier d'apprentissage à l'école maternelle : apports des sciences cognitives et pratiques pédagogiques",
     f"{_CLAR} ; Jeu et exploration de l'environnement ; Apports des sciences cognitives et apprentissage par le jeu ; "
     f"Jeu et intentions pédagogiques ; Posture de l'animateur et accompagnement de l'enfant ; {_IMPL}", "Animation libre"),
    ("11", "La poésie à l'EM : démarche de mise en œuvre",
     f"{_CLAR} ; Importance de la poésie dans le développement du langage de l'enfant ; Critères de choix d'une poésie "
     f"adaptée à l'EM ; Démarche de mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("12", "Bilan", "", ""),
]
THEMES_PRIMAIRE = [
    ("1", "Renouvellement des bureaux", "", ""),
    ("2", _TITRE_2, _AX_COMMUN_2, "Animation libre"),
    ("3", "Construction des figures symétriques par rapport à un point, à une droite et par glissement",
     "Compréhension des notions de symétrie axiale, symétrie centrale et symétrie par glissement ; Identification et "
     "utilité des instruments géométriques ; Construction des figures symétriques par les enseignants (exercices pratiques)",
     "Animation libre"),
    ("4", _TITRE_4, _AX_DIFF, "Animation libre"),
    ("5", "L'enseignement-apprentissage-évaluation de la géométrie au CM",
     f"{_CLAR} ; Explicitation de la compétence disciplinaire concernée ; Démarche disciplinaire de la géométrie ; {_IMPL}",
     "Animation mixte"),
    ("6", "La mise en œuvre de la lecture individuelle au niveau 1 à l'EP : démarche pratique",
     f"{_CLAR} ; Objectifs de la lecture individuelle au niveau 1 ; Démarche de mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("7", "Le vocabulaire fonctionnel au CE1 : importance et démarche d'enseignement",
     f"{_CLAR} ; Importance du vocabulaire fonctionnel dans les apprentissages ; Critères de sélection du vocabulaire "
     f"fonctionnel ; Démarche d'enseignement-apprentissage-évaluation ; {_IMPL}", "Animation mixte"),
    ("8", "Le tâtonnement scientifique dans l'enseignement de la mesure au CM : démarche de mise en œuvre",
     f"{_CLAR} ; Principes du tâtonnement scientifique ; Étapes de la démarche au CM ; {_IMPL}", "Animation mixte"),
    ("9", "La dictée préparée : importance et démarche de mise en œuvre",
     f"{_CLAR} ; Importance de la dictée préparée dans l'apprentissage de l'orthographe ; Étapes de préparation ; "
     f"Démarche de mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("10", "L'enseignement-apprentissage de l'EPS au niveau 1 : spécificités au CE1",
     f"{_CLAR} ; Objectifs et importance ; Organisation de la classe et de l'espace au CE1 ; {_IMPL}", "Animation mixte"),
    ("11", "La poésie au CM : préparation et mise en œuvre",
     f"{_CLAR} ; Critères de choix d'une poésie au CM ; Étapes de préparation d'une séance de poésie ; Démarche de "
     f"mise en œuvre ; {_IMPL}", "Animation mixte"),
    ("12", "Bilan", "", ""),
]
CONFERENCES = [
    ("1", "La place des ressources numériques dans la réussite de l'acte pédagogique",
     f"{_CLAR} ; Typologie des ressources numériques mobilisables en classe ; Apports et limites des ressources "
     f"numériques dans l'acte pédagogique ; {_IMPL}", ""),
    ("2", "Des déchets aux ressources : apprendre à transformer les déchets en ressources pour protéger l'environnement",
     f"{_CLAR} ; Types de déchets ; Gestion des déchets et leur transformation pour l'environnement ; Impacts des "
     f"déchets aux ressources dans l'environnement ; {_IMPL}", ""),
    ("3", "Le leadership du directeur d'école : enjeux et responsabilités pour une gestion réussie",
     f"{_CLAR} ; Enjeux du leadership pédagogique et administratif du directeur ; Documents administratifs et outils de "
     "gestion de l'école ; Responsabilités du directeur pour une gestion réussie", ""),
    ("4", "La gestion des erreurs des apprenants dans le processus enseignement-apprentissage-évaluation",
     f"{_CLAR} ; Typologie des erreurs des apprenants ; Stratégies de gestion et de remédiation des erreurs ; {_IMPL}", ""),
    ("5", "L'utilisation pédagogique de l'intelligence artificielle par l'enseignant",
     f"{_CLAR} ; Potentialités de l'IA pour la préparation et l'animation des enseignements ; Précautions et limites "
     f"d'usage ; {_IMPL}", ""),
]
FORMATIONS = [
    ("1", "La Pédagogie Explicite en français et en mathématiques au CI – CP : fondements cognitifs et démarche de mise en œuvre en classe",
     "Apport des sciences cognitives et les quatre piliers de l'apprentissage ; Étapes du processus d'enseignement – "
     "apprentissage en français au CI – CP ; Démarche disciplinaire des mathématiques au CI – CP ; Articulation des "
     "piliers de l'apprentissage avec les étapes du français et la démarche des mathématiques au CI - CP",
     "Ce thème est à développer obligatoirement au cours du premier trimestre de l'année scolaire 2026-2027"),
    ("2", "La pédagogie de l'intégration : approches et mise en œuvre",
     f"{_CLAR} ; Fondements de la pédagogie de l'intégration ; Démarche de mise en œuvre en classe ; {_IMPL}", ""),
    ("3", "La gestion de la remédiation en évaluation formative",
     f"{_CLAR} ; Étapes de l'évaluation formative ; Stratégies de remédiation adaptées aux besoins des apprenants ; {_IMPL}", ""),
    ("4", "La différenciation pédagogique : focus sur les groupes de besoins",
     f"{_CLAR} ; Critères de constitution des groupes de besoins ; Démarche de mise en œuvre de la différenciation "
     f"pédagogique ; {_IMPL}", ""),
    ("5", "L'accord du participe passé employé avec l'auxiliaire avoir et des verbes pronominaux",
     "Rappel des règles de base ; Cas particuliers d'accord ; Démarche d'enseignement-apprentissage-évaluation ; "
     "Exercices d'application", ""),
]
NOTE_UP = ("Conformément à l'arrêté N°003/MEMP/DC/SGM/DPAF/DEM/DEP/DIIP/SP 041 SGG25 du 17 février 2026, dérouler par "
           "trimestre un thème de conférence pédagogique et un thème de formation groupée.")


def classe_par_defaut(categorie, intitule):
    """Les trimestres sont des périodes de classe ; pré-rentrée, congés, fêtes et reprise ne le sont pas."""
    return 1 if categorie == "periode" and "trimestre" in (intitule or "").lower() and "reprise" not in (intitule or "").lower() else 0


def jours_ouvres(debut, fin):
    """Dates du lundi au vendredi de `debut` à `fin` inclus (objets date)."""
    from datetime import timedelta
    out, d = [], debut
    while d <= fin:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def compter_demi_journees(lignes):
    """lignes : [{categorie, intitule, debut, fin, classe}] -> dict de comptage (voir demi_journees)."""
    from datetime import timedelta
    conges, feries = [], set()
    for x in lignes:
        try:
            d1, d2 = date.fromisoformat(x["debut"]), date.fromisoformat(x["fin"] or x["debut"])
        except (TypeError, ValueError):
            continue
        if x["categorie"] == "conge":
            conges.append((d1 + timedelta(days=1), d2))     # le jour de début reste un jour de classe (« après les cours »)
        elif x["categorie"] == "ferie":
            feries |= set(jours_ouvres(d1, d2))
    par, vus, retires_c, retires_f = [], set(), 0, 0
    for x in lignes:
        if not x.get("classe"):
            continue
        try:
            d1, d2 = date.fromisoformat(x["debut"]), date.fromisoformat(x["fin"] or x["debut"])
        except (TypeError, ValueError):
            continue
        jours = [d for d in jours_ouvres(d1, d2) if d not in vus]
        c = [d for d in jours if any(a <= d <= b for a, b in conges)]
        f = [d for d in jours if d in feries and d not in c]
        gardes = [d for d in jours if d not in c and d not in f]
        vus |= set(jours)
        retires_c += len(c)
        retires_f += len(f)
        par.append({"intitule": x["intitule"], "debut": x["debut"], "fin": x["fin"], "jours": len(gardes),
                    "demi": 2 * len(gardes), "conges": len(c), "feries": len(f),
                    "mercredis": sum(1 for d in gardes if d.weekday() == 2)})
    jours = sum(p_["jours"] for p_ in par)
    mercredis = sum(p_["mercredis"] for p_ in par)
    return {"par_periode": par, "jours": jours, "demi_journees": 2 * jours, "mercredis": mercredis,
            "demi_journees_primaire": 2 * jours - mercredis, "conges_retires": retires_c, "feries_retires": retires_f}


def themes_officiels():
    """[(catégorie, n°, thème, axes, préparation, interprétation, administration, observations)]."""
    out = []
    for cat, lst in (("maternelle", THEMES_MATERNELLE), ("primaire", THEMES_PRIMAIRE)):
        for i, (n, th, ax, obs) in enumerate(lst):
            out.append((cat, n, th, ax, "" if n == "1" or n == "12" else "PM", "" if n == "1" or n == "12" else "PM",
                        _DATES[i], obs))
    for cat, lst in (("conference", CONFERENCES), ("formation", FORMATIONS)):
        for n, th, ax, obs in lst:
            out.append((cat, n, th, ax, "", "", "PM", obs))
    return out


# ------------------------------------------------------------------ dates
def en_iso(v):
    """Date saisie (AAAA-MM-JJ, JJ/MM/AAAA, objet date/datetime) -> 'AAAA-MM-JJ' ; '' si vide ; None si illisible."""
    if v in (None, ""):
        return ""
    if isinstance(v, (date, datetime)):
        return v.strftime("%Y-%m-%d")
    t = str(v).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
        try:
            date.fromisoformat(t)
            return t
        except ValueError:
            return None
    m = re.fullmatch(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})", t)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


def fr(iso):
    try:
        return date.fromisoformat(iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return iso or ""


JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def fr_long(iso):
    try:
        d = date.fromisoformat(iso)
        return f"{JOURS_FR[d.weekday()]} {d.strftime('%d/%m/%Y')}"
    except (TypeError, ValueError):
        return iso or ""


def enregistrer(app, H):
    q, ex, config = H.q, H.ex, H.config
    H.schema(SCHEMA)
    try:                                   # bases créées avant l'ajout de la colonne « classe »
        ex("ALTER TABLE calendrier_officiel_lignes ADD COLUMN classe INTEGER DEFAULT 0")
    except Exception:  # noqa: BLE001 - colonne déjà présente
        pass

    def uid():
        from flask import g
        return g.user["id"] if g.get("user") else None

    def peut_ecrire():
        return H.peut("synoptique")

    def ecriture():
        if not peut_ecrire():
            abort(403)

    def annee_demandee():
        a = (request.values.get("annee") or "").strip()
        return a if re.fullmatch(r"\d{4}-\d{4}", a) else (config.ANNEE_ACTIVE or ANNEE_OFFICIELLE)

    def ident():
        """Identité de l'école (dict) : H.synoptique_identite renvoie [{cle, libelle, valeur}] ; `cs` vient de la fiche école."""
        d = {"epp": "", "ddemp": "", "cs": ""}
        f = getattr(H, "synoptique_identite", None)
        if f:
            d.update({x["cle"]: x["valeur"] for x in f(H.eco())})
        e = q("SELECT cs FROM ecoles WHERE id=?", (H.eco(),), un=True)
        d["cs"] = (e["cs"] if e and e["cs"] else "") or d.get("cs", "")
        return d

    def annees_connues():
        s = {config.ANNEE_ACTIVE or ANNEE_OFFICIELLE, ANNEE_OFFICIELLE}
        for t in ("calendrier_officiel_lignes", "themes_up_lignes"):
            s |= {r["annee"] for r in q(f"SELECT DISTINCT annee FROM {t} WHERE ecole_id=?", (H.eco(),))}
        return sorted(s)

    # ------------------------------------------------------------ données
    def initialiser_calendrier(ecole_id, annee):
        if annee != ANNEE_OFFICIELLE:
            return
        for i, (cat, intit, d1, d2, dur, obs) in enumerate(CALENDRIER_2026_2027, 1):
            ex("INSERT INTO calendrier_officiel_lignes (ecole_id, annee, ordre, categorie, intitule, debut, fin, duree, "
               "observations, classe, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
               (ecole_id, annee, i * 10, cat, intit, d1, d2, dur, obs, classe_par_defaut(cat, intit), H.maintenant(), uid()))

    def initialiser_themes(ecole_id, annee):
        if annee != ANNEE_OFFICIELLE:
            return
        for i, (cat, n, th, ax, prep, interp, adm, obs) in enumerate(themes_officiels(), 1):
            ex("INSERT INTO themes_up_lignes (ecole_id, annee, ordre, categorie, numero, theme, axes, preparation, "
               "interpretation, administration, observations, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (ecole_id, annee, i * 10, cat, n, th, ax, prep, interp, adm, obs, H.maintenant(), uid()))

    def lignes_calendrier(annee=None, ecole_id=None):
        ecole_id, annee = ecole_id or H.eco(), annee or config.ANNEE_ACTIVE or ANNEE_OFFICIELLE
        if not q("SELECT 1 FROM calendrier_officiel_lignes WHERE ecole_id=? AND annee=? LIMIT 1", (ecole_id, annee), un=True) \
                and ecole_id == H.eco():
            initialiser_calendrier(ecole_id, annee)
        return [dict(r) for r in q("SELECT * FROM calendrier_officiel_lignes WHERE ecole_id=? AND annee=? "
                                   "ORDER BY ordre, debut, id", (ecole_id, annee))]

    def lignes_themes(annee=None, ecole_id=None):
        ecole_id, annee = ecole_id or H.eco(), annee or config.ANNEE_ACTIVE or ANNEE_OFFICIELLE
        if not q("SELECT 1 FROM themes_up_lignes WHERE ecole_id=? AND annee=? LIMIT 1", (ecole_id, annee), un=True) \
                and ecole_id == H.eco():
            initialiser_themes(ecole_id, annee)
        return [dict(r) for r in q("SELECT * FROM themes_up_lignes WHERE ecole_id=? AND annee=? ORDER BY ordre, id",
                                   (ecole_id, annee))]

    def calendrier_officiel(annee=None, ecole_id=None):
        """Périodes / événements du calendrier scolaire : [{categorie, intitule, debut, fin, duree, observations}]."""
        return lignes_calendrier(annee, ecole_id)

    def themes_up(annee=None, ecole_id=None):
        """Thèmes : [{categorie, numero, theme, axes, preparation, interpretation, administration, observations}]."""
        return lignes_themes(annee, ecole_id)

    def demi_journees(annee=None, ecole_id=None):
        """Jours et demi-journées de classe de l'année scolaire d'après le calendrier (voir compter_demi_journees)."""
        return compter_demi_journees(lignes_calendrier(annee, ecole_id))

    def calendrier_section():
        """Section « calendrier » du paquet de transmission : calendrier scolaire, jours et demi-journées de classe, thèmes
        d'UP de l'école courante (année active)."""
        annee = config.ANNEE_ACTIVE or ANNEE_OFFICIELLE
        cal, th = lignes_calendrier(annee), lignes_themes(annee)
        dj = compter_demi_journees(cal)
        return {"annee": annee,
                "calendrier": [{k: x[k] for k in ("categorie", "intitule", "debut", "fin", "duree", "observations", "classe")}
                               for x in cal],
                "jours_classe": dj["jours"], "demi_journees": dj["demi_journees"],
                "demi_journees_primaire": dj["demi_journees_primaire"],
                "themes_up": [{k: x[k] for k in ("categorie", "numero", "theme", "preparation", "interpretation",
                                                 "administration", "observations")} for x in th]} if cal or th else None

    def synoptique_section():
        """Section « synoptique » du paquet de transmission : identité du tableau synoptique et comités de l'école courante
        (le personnel est déjà transmis par la section « personnel »)."""
        f = getattr(H, "synoptique_identite", None)
        if not f:
            return None
        ident_ = {x["cle"]: x["valeur"] for x in f(H.eco()) if x.get("valeur")}
        comites = {}
        for r in q("SELECT comite, nom_prenoms, qualite, origine, contact FROM synoptique_membres WHERE ecole_id=? "
                   "ORDER BY comite, ordre, id", (H.eco(),)):
            comites.setdefault(r["comite"], []).append({"nom_prenoms": r["nom_prenoms"], "qualite": r["qualite"] or "",
                                                         "origine": r["origine"] or "", "contact": r["contact"] or ""})
        return {"annee": config.ANNEE_ACTIVE, "identite": ident_, "comites": comites} if ident_ or comites else None

    H.calendrier_section, H.synoptique_section = calendrier_section, synoptique_section
    H.calendrier_officiel = calendrier_officiel
    H.demi_journees = demi_journees
    H.themes_up = themes_up

    def ctx(onglet, annee, **extra):
        return dict(onglet=onglet, ecrire=peut_ecrire(), ident=ident(), annee_sel=annee, annees=annees_connues(),
                    fr=fr, fr_long=fr_long, **extra)

    # ------------------------------------------------------------ calendrier : pages
    def lire_ligne_cal(form):
        err = []
        v = {"categorie": form.get("categorie") if form.get("categorie") in CATEGORIES_CAL else "periode",
             "intitule": (form.get("intitule") or "").strip()[:200], "duree": (form.get("duree") or "").strip()[:80],
             "observations": (form.get("observations") or "").strip()[:500]}
        v["debut"], v["fin"] = en_iso(form.get("debut")), en_iso(form.get("fin"))
        v["classe"] = 1 if form.get("classe") else 0
        brut = (form.get("ordre") or "").strip()
        v["ordre"] = int(brut) if brut.isdigit() else 0
        if not v["intitule"]:
            err.append("L'intitulé est obligatoire.")
        if v["debut"] is None or v["fin"] is None:
            err.append("Date illisible : saisissez JJ/MM/AAAA.")
            v["debut"] = v["debut"] or ""
            v["fin"] = v["fin"] or ""
        elif v["debut"] and v["fin"] and v["fin"] < v["debut"]:
            err.append("La date de fin précède la date de début.")
        return v, err

    @app.route("/synoptique/calendrier", endpoint="calendrier_officiel")      # nom d'endpoint imposé par le contrat
    @H.connexion_requise()
    def calendrier_officiel_page():
        annee = annee_demandee()
        return render_template("calendrier_officiel.html", **ctx("calendrier", annee, lst=lignes_calendrier(annee),
                               dj=demi_journees(annee), CATS=CATEGORIES_CAL, source=SOURCE_CAL, officiel=annee == ANNEE_OFFICIELLE))

    @app.route("/synoptique/calendrier/<int:lid>", methods=["GET", "POST"])
    @H.connexion_requise("synoptique")
    def calendrier_ligne_form(lid):
        annee = annee_demandee()
        a = None
        if lid:
            a = q("SELECT * FROM calendrier_officiel_lignes WHERE id=? AND ecole_id=?", (lid, H.eco()), un=True)
            if not a:
                abort(404)
            a = dict(a)
            annee = a["annee"]
        if request.method == "POST":
            v, err = lire_ligne_cal(request.form)
            if err:
                for e_ in err:
                    flash(e_, "danger")
                return render_template("calendrier_form.html", **ctx("calendrier", annee, a=a, v=v, CATS=CATEGORIES_CAL)), 400
            if lid:
                ex("UPDATE calendrier_officiel_lignes SET categorie=?, intitule=?, debut=?, fin=?, duree=?, observations=?, "
                   "classe=?, ordre=?, maj=?, maj_par=? WHERE id=?", (v["categorie"], v["intitule"], v["debut"], v["fin"], v["duree"],
                                                                    v["observations"], v["classe"], v["ordre"], H.maintenant(), uid(), lid))
            else:
                lignes_calendrier(annee)
                if not v["ordre"]:
                    v["ordre"] = (q("SELECT COALESCE(MAX(ordre),0) m FROM calendrier_officiel_lignes WHERE ecole_id=? AND annee=?",
                                    (H.eco(), annee), un=True)["m"] or 0) + 10
                ex("INSERT INTO calendrier_officiel_lignes (ecole_id, annee, ordre, categorie, intitule, debut, fin, duree, "
                   "observations, classe, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                   (H.eco(), annee, v["ordre"], v["categorie"], v["intitule"], v["debut"], v["fin"], v["duree"],
                    v["observations"], v["classe"], H.maintenant(), uid()))
            H.journal("synoptique", f"calendrier {annee} : « {v['intitule']} » {'modifié' if a else 'ajouté'}")
            flash("Calendrier scolaire mis à jour.", "success")
            return redirect(url_for("calendrier_officiel", annee=annee))
        return render_template("calendrier_form.html", **ctx("calendrier", annee, a=a, v=a or {}, CATS=CATEGORIES_CAL))

    @app.route("/synoptique/calendrier/<int:lid>/supprimer", methods=["POST"])
    @H.connexion_requise("synoptique")
    def calendrier_ligne_supprimer(lid):
        a = q("SELECT * FROM calendrier_officiel_lignes WHERE id=? AND ecole_id=?", (lid, H.eco()), un=True)
        if not a:
            abort(404)
        ex("DELETE FROM calendrier_officiel_lignes WHERE id=?", (lid,))
        H.journal("synoptique", f"calendrier {a['annee']} : « {a['intitule']} » supprimé")
        flash("Ligne supprimée du calendrier.", "warning")
        return redirect(url_for("calendrier_officiel", annee=a["annee"]))

    @app.route("/synoptique/calendrier/reinitialiser", methods=["POST"])
    @H.connexion_requise("synoptique")
    def calendrier_reinitialiser():
        annee = annee_demandee()
        ex("DELETE FROM calendrier_officiel_lignes WHERE ecole_id=? AND annee=?", (H.eco(), annee))
        initialiser_calendrier(H.eco(), annee)
        H.journal("synoptique", f"calendrier {annee} réinitialisé")
        flash("Calendrier réinitialisé" + (" (arrêté officiel)." if annee == ANNEE_OFFICIELLE
                                          else " : tableau vide, ajoutez les périodes de cette année."), "success")
        return redirect(url_for("calendrier_officiel", annee=annee))

    # ------------------------------------------------------------ thèmes UP : pages
    def lire_ligne_theme(form):
        err = []
        v = {"categorie": form.get("categorie") if form.get("categorie") in CATEGORIES_UP else "primaire",
             "numero": (form.get("numero") or "").strip()[:10], "theme": (form.get("theme") or "").strip()[:400],
             "axes": (form.get("axes") or "").strip()[:2000]}
        for k in ("preparation", "interpretation", "administration"):
            brut = (form.get(k) or "").strip()
            iso = en_iso(brut)
            v[k] = fr(iso) if iso else brut[:40]          # date normalisée JJ/MM/AAAA ou texte libre (« PM »)
        v["observations"] = (form.get("observations") or "").strip()[:500]
        brut = (form.get("ordre") or "").strip()
        v["ordre"] = int(brut) if brut.isdigit() else 0
        if not v["theme"]:
            err.append("Le thème est obligatoire.")
        return v, err

    @app.route("/synoptique/themes-up", endpoint="themes_up")                 # nom d'endpoint imposé par le contrat
    @H.connexion_requise()
    def themes_up_page():
        annee = annee_demandee()
        lst = lignes_themes(annee)
        groupes = [(c, lib, [x for x in lst if x["categorie"] == c]) for c, lib in CATEGORIES_UP.items()]
        return render_template("themes_up.html", **ctx("themes_up", annee, groupes=groupes, CATS=CATEGORIES_UP,
                               source=SOURCE_UP, note=NOTE_UP if annee == ANNEE_OFFICIELLE else ""))

    @app.route("/synoptique/themes-up/<int:tid>", methods=["GET", "POST"])
    @H.connexion_requise("synoptique")
    def themes_up_form(tid):
        annee = annee_demandee()
        a = None
        if tid:
            a = q("SELECT * FROM themes_up_lignes WHERE id=? AND ecole_id=?", (tid, H.eco()), un=True)
            if not a:
                abort(404)
            a = dict(a)
            annee = a["annee"]
        if request.method == "POST":
            v, err = lire_ligne_theme(request.form)
            if err:
                for e_ in err:
                    flash(e_, "danger")
                return render_template("themes_up_form.html", **ctx("themes_up", annee, a=a, v=v, CATS=CATEGORIES_UP)), 400
            if tid:
                ex("UPDATE themes_up_lignes SET categorie=?, numero=?, theme=?, axes=?, preparation=?, interpretation=?, "
                   "administration=?, observations=?, ordre=?, maj=?, maj_par=? WHERE id=?",
                   (v["categorie"], v["numero"], v["theme"], v["axes"], v["preparation"], v["interpretation"],
                    v["administration"], v["observations"], v["ordre"], H.maintenant(), uid(), tid))
            else:
                lignes_themes(annee)
                if not v["ordre"]:
                    v["ordre"] = (q("SELECT COALESCE(MAX(ordre),0) m FROM themes_up_lignes WHERE ecole_id=? AND annee=?",
                                    (H.eco(), annee), un=True)["m"] or 0) + 10
                ex("INSERT INTO themes_up_lignes (ecole_id, annee, ordre, categorie, numero, theme, axes, preparation, "
                   "interpretation, administration, observations, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (H.eco(), annee, v["ordre"], v["categorie"], v["numero"], v["theme"], v["axes"], v["preparation"],
                    v["interpretation"], v["administration"], v["observations"], H.maintenant(), uid()))
            H.journal("synoptique", f"thème d'UP {annee} : « {v['theme'][:60]} » {'modifié' if a else 'ajouté'}")
            flash("Thèmes d'UP mis à jour.", "success")
            return redirect(url_for("themes_up", annee=annee))
        return render_template("themes_up_form.html", **ctx("themes_up", annee, a=a, v=a or {}, CATS=CATEGORIES_UP))

    @app.route("/synoptique/themes-up/<int:tid>/supprimer", methods=["POST"])
    @H.connexion_requise("synoptique")
    def themes_up_supprimer(tid):
        a = q("SELECT * FROM themes_up_lignes WHERE id=? AND ecole_id=?", (tid, H.eco()), un=True)
        if not a:
            abort(404)
        ex("DELETE FROM themes_up_lignes WHERE id=?", (tid,))
        H.journal("synoptique", f"thème d'UP {a['annee']} : « {a['theme'][:60]} » supprimé")
        flash("Thème supprimé.", "warning")
        return redirect(url_for("themes_up", annee=a["annee"]))

    @app.route("/synoptique/themes-up/reinitialiser", methods=["POST"])
    @H.connexion_requise("synoptique")
    def themes_up_reinitialiser():
        annee = annee_demandee()
        ex("DELETE FROM themes_up_lignes WHERE ecole_id=? AND annee=?", (H.eco(), annee))
        initialiser_themes(H.eco(), annee)
        H.journal("synoptique", f"thèmes d'UP {annee} réinitialisés")
        flash("Thèmes réinitialisés" + (" (planning officiel)." if annee == ANNEE_OFFICIELLE
                                        else " : tableau vide, ajoutez les thèmes de cette année."), "success")
        return redirect(url_for("themes_up", annee=annee))

    # ------------------------------------------------------------ Excel : export, import
    ENT_CAL = ["Catégorie", "Intitulé", "Début", "Fin", "Durée", "Observations", "Période de classe"]
    ENT_UP = ["Catégorie", "N°", "Thème", "Axes de réflexion / contenus", "Préparation", "Interprétation",
              "Administration / date", "Observations"]

    def th_haut(titre, annee):
        d = ident()
        return [f"{d.get('epp') or config.ECOLE.get('nom', '')} — {titre}", f"Année scolaire {annee}"]

    @app.route("/synoptique/calendrier.xlsx")
    @H.connexion_requise()
    def calendrier_xlsx():
        annee = annee_demandee()
        lignes = [[CATEGORIES_CAL.get(x["categorie"], x["categorie"]), x["intitule"], fr(x["debut"]), fr(x["fin"]), x["duree"],
                   x["observations"], "Oui" if x.get("classe") else "Non"] for x in lignes_calendrier(annee)]
        return H.xlsx.reponse_xlsx(f"calendrier_scolaire_{annee}.xlsx", ENT_CAL, lignes, titre="Calendrier",
                                   titre_haut=th_haut("Calendrier scolaire", annee))

    @app.route("/synoptique/themes-up.xlsx")
    @H.connexion_requise()
    def themes_up_xlsx():
        annee = annee_demandee()
        lignes = [[CATEGORIES_UP.get(x["categorie"], x["categorie"]), x["numero"], x["theme"], x["axes"], x["preparation"],
                   x["interpretation"], x["administration"], x["observations"]] for x in lignes_themes(annee)]
        return H.xlsx.reponse_xlsx(f"themes_up_{annee}.xlsx", ENT_UP, lignes, titre="Thèmes UP",
                                   titre_haut=th_haut("Thèmes d'unité pédagogique", annee))

    def lire_classeur(fichier, mot_cle):
        """Première feuille dont une ligne (parmi les 15 premières) a une cellule égale à `mot_cle` -> (entetes, lignes) ;
        l'égalité exacte évite de prendre pour en-tête le titre de l'export (« … — Thèmes d'unité pédagogique »)."""
        openpyxl = H.xlsx._openpyxl()
        try:
            wb = openpyxl.load_workbook(io.BytesIO(fichier.read()), read_only=True, data_only=True)
        except Exception as e_:  # noqa: BLE001
            raise ValueError("Fichier Excel illisible : enregistrez-le au format .xlsx.") from e_
        for ws in wb.worksheets:
            brutes = [list(r) for r in ws.iter_rows(values_only=True)][:2000]
            idx = next((i for i, r in enumerate(brutes[:15]) if any(H.xlsx.normaliser(v) == mot_cle for v in r if v)), None)
            if idx is not None:
                entetes = [str(v).strip() if v is not None else "" for v in brutes[idx]]
                return entetes, [r for r in brutes[idx + 1:] if any(v not in (None, "") for v in r)]
        raise ValueError(f"Aucune feuille exploitable : la ligne d'en-tête doit contenir « {mot_cle} ».")

    def categorie_depuis(txt, table):
        n = H.xlsx.normaliser(txt)
        for k, lib in table.items():
            if n in (k, H.xlsx.normaliser(lib)) or (n and (k in n or n in H.xlsx.normaliser(lib))):
                return k
        return None

    @app.route("/synoptique/calendrier/import", methods=["POST"])
    @H.connexion_requise("synoptique")
    def calendrier_import():
        annee = annee_demandee()
        f = request.files.get("fichier")
        if not f or not f.filename:
            flash("Choisissez un fichier Excel (.xlsx).", "danger")
            return redirect(url_for("calendrier_officiel", annee=annee))
        try:
            entetes, lignes = lire_classeur(f, "intitule")
        except (ValueError, H.xlsx.ExcelIndisponible) as e_:
            flash(str(e_), "danger")
            return redirect(url_for("calendrier_officiel", annee=annee))
        ic = {k: H.xlsx.colonne(entetes, *c) for k, c in {
            "categorie": ("Catégorie", "Categorie", "Type"), "intitule": ("Intitulé", "Intitule", "Libellé"),
            "debut": ("Début", "Debut", "Du", "Date de début"), "fin": ("Fin", "Au", "Date de fin"),
            "duree": ("Durée", "Duree"), "obs": ("Observations", "Observation"),
            "classe": ("Période de classe", "Periode de classe", "Classe")}.items()}
        n = erreurs = 0
        for l in lignes:
            def cell(k):
                i = ic[k]
                return l[i] if i is not None and i < len(l) and l[i] is not None else ""
            intit = str(cell("intitule")).strip()
            d1, d2 = en_iso(cell("debut")), en_iso(cell("fin"))
            if not intit or d1 is None or d2 is None:
                erreurs += 1
                continue
            cat = categorie_depuis(str(cell("categorie")), CATEGORIES_CAL) or "periode"
            brut_classe = H.xlsx.normaliser(cell("classe"))
            classe = (1 if brut_classe in ("oui", "1", "x", "vrai") else 0) if brut_classe else classe_par_defaut(cat, intit)
            ordre = (q("SELECT COALESCE(MAX(ordre),0) m FROM calendrier_officiel_lignes WHERE ecole_id=? AND annee=?",
                       (H.eco(), annee), un=True)["m"] or 0) + 10
            ex("INSERT INTO calendrier_officiel_lignes (ecole_id, annee, ordre, categorie, intitule, debut, fin, duree, "
               "observations, classe, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
               (H.eco(), annee, ordre, cat, intit[:200], d1, d2, str(cell("duree")).strip()[:80],
                str(cell("obs")).strip()[:500], classe, H.maintenant(), uid()))
            n += 1
        H.journal("synoptique", f"calendrier {annee} : import Excel ({n} ligne(s))")
        flash(f"Import terminé : {n} ligne(s) ajoutée(s)" + (f", {erreurs} ignorée(s) (intitulé ou date illisible)." if erreurs else "."),
              "success" if n else "warning")
        return redirect(url_for("calendrier_officiel", annee=annee))

    @app.route("/synoptique/themes-up/import", methods=["POST"])
    @H.connexion_requise("synoptique")
    def themes_up_import():
        annee = annee_demandee()
        f = request.files.get("fichier")
        if not f or not f.filename:
            flash("Choisissez un fichier Excel (.xlsx).", "danger")
            return redirect(url_for("themes_up", annee=annee))
        try:
            entetes, lignes = lire_classeur(f, "theme")
        except (ValueError, H.xlsx.ExcelIndisponible) as e_:
            flash(str(e_), "danger")
            return redirect(url_for("themes_up", annee=annee))
        ic = {k: H.xlsx.colonne(entetes, *c) for k, c in {
            "categorie": ("Catégorie", "Categorie", "Type"), "numero": ("N°", "No", "Numéro", "Numero", "N"),
            "theme": ("Thème", "Theme", "Thèmes"), "axes": ("Axes", "Axes de réflexion", "Contenus"),
            "prep": ("Préparation", "Preparation"), "interp": ("Interprétation", "Interpretation"),
            "adm": ("Administration", "Date"), "obs": ("Observations", "Observation", "Obs")}.items()}
        n = erreurs = 0
        for l in lignes:
            def cell(k):
                i = ic[k]
                v = l[i] if i is not None and i < len(l) and l[i] is not None else ""
                if isinstance(v, (date, datetime)):
                    return v.strftime("%d/%m/%Y")
                return str(v).strip()
            theme = cell("theme")
            if not theme:
                erreurs += 1
                continue
            cat = categorie_depuis(cell("categorie"), CATEGORIES_UP) or "primaire"
            ordre = (q("SELECT COALESCE(MAX(ordre),0) m FROM themes_up_lignes WHERE ecole_id=? AND annee=?",
                       (H.eco(), annee), un=True)["m"] or 0) + 10
            ex("INSERT INTO themes_up_lignes (ecole_id, annee, ordre, categorie, numero, theme, axes, preparation, "
               "interpretation, administration, observations, maj, maj_par) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (H.eco(), annee, ordre, cat, cell("numero")[:10], theme[:400], cell("axes")[:2000], cell("prep")[:40],
                cell("interp")[:40], cell("adm")[:40], cell("obs")[:500], H.maintenant(), uid()))
            n += 1
        H.journal("synoptique", f"thèmes d'UP {annee} : import Excel ({n} ligne(s))")
        flash(f"Import terminé : {n} thème(s) ajouté(s)" + (f", {erreurs} ignoré(s) (thème vide)." if erreurs else "."),
              "success" if n else "warning")
        return redirect(url_for("themes_up", annee=annee))

    # ------------------------------------------------------------ PDF
    def pdf(titre, entetes, lignes, largeurs, annee, sous_titres=None, apres=None):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        d = ident()
        buf = io.BytesIO()
        W, _h = landscape(A4)
        utile = W - 24 * mm
        bleu = colors.HexColor("#1f4e79")
        st_t = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, textColor=bleu, spaceAfter=3)
        st_s = ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=11, alignment=1, spaceAfter=8)
        st_c = ParagraphStyle("c", fontName="Helvetica", fontSize=7.5, leading=9.3)
        st_h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=7.5, leading=9.3, alignment=1, textColor=colors.white)
        st_g = ParagraphStyle("g", fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=bleu, spaceBefore=8, spaceAfter=3)

        def esc(v):
            return ("" if v is None else str(v)).replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")

        def table(rows):
            data = [[Paragraph(esc(h), st_h) for h in entetes]] + [[Paragraph(esc(c), st_c) for c in r] for r in rows]
            t = Table(data, colWidths=[utile * w for w in largeurs], repeatRows=1)
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), bleu), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                   ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fa")])]))
            return t

        h = [Paragraph(esc(f"DDEMP {d.get('ddemp') or ''} · CS {d.get('cs') or ''} · {d.get('epp') or config.ECOLE.get('nom', '')}"), st_s),
             Paragraph(esc(titre), st_t), Paragraph(f"Année scolaire {esc(annee)} — édité le {date.today().strftime('%d/%m/%Y')}", st_s)]
        if sous_titres:
            for ts, rows in sous_titres:
                h.append(Paragraph(esc(ts), st_g))
                h.append(table(rows))
        else:
            h.append(table(lignes))
        h.append(Spacer(1, 6))
        if apres:
            h.append(Paragraph(esc(apres), st_s))
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                                bottomMargin=12 * mm, title=titre, author="GESCOL")
        doc.build(h)
        return buf.getvalue()

    @app.route("/synoptique/calendrier.pdf")
    @H.connexion_requise()
    def calendrier_pdf():
        annee = annee_demandee()
        rows = [[CATEGORIES_CAL.get(x["categorie"], ""), x["intitule"], fr_long(x["debut"]),
                 fr_long(x["fin"]) if x["fin"] != x["debut"] else "—", x["duree"], x["observations"]]
                for x in lignes_calendrier(annee)]
        dj = demi_journees(annee)
        bilan = (f"Jours de classe : {dj['jours']} — demi-journées (matin et après-midi) : {dj['demi_journees']} — "
                 f"demi-journées avec mercredi après-midi libre (emploi du temps du primaire) : {dj['demi_journees_primaire']}.")
        return H.pdf_reponse(pdf("CALENDRIER SCOLAIRE", ["Catégorie", "Intitulé", "Du", "Au", "Durée", "Observations"], rows,
                                 [0.13, 0.27, 0.15, 0.15, 0.13, 0.17], annee, apres=bilan), f"calendrier_scolaire_{annee}.pdf")

    @app.route("/synoptique/themes-up.pdf")
    @H.connexion_requise()
    def themes_up_pdf():
        annee = annee_demandee()
        lst = lignes_themes(annee)
        groupes = []
        for c, lib in CATEGORIES_UP.items():
            rows = [[x["numero"], x["theme"], ("- " + x["axes"].replace(" ; ", "\n- ")) if x["axes"] else "",
                     x["preparation"], x["interpretation"], x["administration"], x["observations"]]
                    for x in lst if x["categorie"] == c]
            if rows:
                groupes.append((lib.upper(), rows))
        return H.pdf_reponse(pdf("PLANNING D'EXÉCUTION DES THÈMES D'UNITÉ PÉDAGOGIQUE",
                                 ["N°", "Thème", "Axes de réflexion / contenus", "Préparation", "Interprétation",
                                  "Administration", "Obs."], [], [0.04, 0.22, 0.40, 0.07, 0.08, 0.10, 0.09], annee,
                                 sous_titres=groupes), f"themes_up_{annee}.pdf")
