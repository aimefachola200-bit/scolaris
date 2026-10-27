# -*- coding: utf-8 -*-
"""v1.18 — Préparation de classe de l'enseignant : programmes et progressions, guides pédagogiques, fiches de
préparation (bibliothèque APC et fiches personnelles), fiches et guides manquants.

Corpus : static/pedafiche_corpus.json.gz, construit par outils/pedafiche (construire_corpus.py + concues.py) à partir
des deux applications PédaFiche Pro fournies par l'utilisateur (1 012 fiches APC CI → CM2 et maternelle, programmes
de Français CE1 / CM1, Mathématiques CE2, EST CI → CM2, Éducation sociale CM1, démarches et guides) ; les fiches et
guides ajoutés pour combler les manques portent la mention « Conçue selon l'APC — à valider par le conseiller
pédagogique » et ne sont jamais présentés comme officiels.

* ``/preparation`` : « Cette semaine » pour chacune de SES classes : ce que prévoient la planification mensuelle de la
  classe (semaine en cours) ou, à défaut, la planification annuelle du cours (mois en cours) — m_synoptique — et les
  fiches de la bibliothèque correspondantes (SA / unité / dossier cités), téléchargeables d'un coup (« fiches de la
  semaine », un PDF).
* ``/preparation/programmes`` : programmes et progressions par cours et matière (unités, dossiers, SA, semaines).
* ``/preparation/guides`` : guides méthodologiques et démarches par matière, lisibles et en PDF.
* ``/preparation/fiches`` : bibliothèque filtrable (cours, matière, sous-matière, SA, séance, texte, « de la semaine »),
  fiche affichée, PDF A4 au format APC (en-tête officiel, école, classe, date, effectif, CD, CT, contenus, stratégies,
  matériel, déroulement phases × activités × résultats, évaluation, signatures et QR de vérification), Word (.doc).
* ``/preparation/preparer`` : préparer une fiche (vierge, d'après un modèle ou en adaptant une fiche de la
  bibliothèque), pour une de SES classes ; ``/preparation/mes-fiches`` : ses fiches (modifier, dupliquer, supprimer,
  PDF, Word). Le directeur consulte les fiches de son école.
* ``/preparation/manquants`` : matrice cours × matière (fiches, guides, SA prévues par la planification sans fiche),
  avant et après les fiches conçues ; v1.19 : état de l'inventaire CM1 (séances de référence, présentes, conçues), lot 2
  (fiches transmises par la CS importées, recueils de référence, guide officiel CP) et doublons fusionnés.
* v1.19 — ``/preparation/resumes`` : « Résumés — l'essentiel à retenir » (Mathématiques CE1 → CM2, Français CM1,
  révision CEP : règle, méthode, exemple, 3 exercices corrigés), version enseignant (corrigé) et version élève
  imprimable (sans les réponses), PDF à l'unité ou par lot (collection / cours / matière).
* v1.23 — résumés pour chaque cours (CI → CM2) dans chaque matière (Français, Mathématiques, Éducation sociale, EST,
  EPS, Éducation artistique), rattachés aux SA / unités : tableau cours × matière dans l'onglet Résumés et « Résumés de la
  semaine » à côté des fiches dans la planification (vue semaine).
Droit « preparation » (app.DROITS) : enseignant, directeur, administrateur, conseillers et responsables (CS / DDEMP,
lecture). L'enseignant n'écrit que pour ses classes (H.classes_autorisees()).
"""
import gzip
import html as _html
import io
import json
import re
from datetime import date, datetime, timedelta
from html.parser import HTMLParser

from flask import Response, abort, flash, g, redirect, render_template, request, url_for

COURS = ["MAT", "CI", "CP", "CE1", "CE2", "CM1", "CM2"]
COURS_LIB = {"MAT": "Maternelle", "CI": "CI", "CP": "CP", "CE1": "CE1", "CE2": "CE2", "CM1": "CM1", "CM2": "CM2"}
NIVEAU_COURS = {"Maternelle 1": "MAT", "Maternelle 2": "MAT", "CI": "CI", "CP": "CP", "CE1": "CE1", "CE2": "CE2", "CM1": "CM1", "CM2": "CM2"}
NIVEAU_SYNO = {"Maternelle 1": "maternelle1", "Maternelle 2": "maternelle2", "CI": "ci", "CP": "cp", "CE1": "ce1", "CE2": "ce2",
               "CM1": "cm1", "CM2": "cm2"}
MOIS_FR = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
# colonnes de la planification annuelle / lignes de la planification mensuelle (m_synoptique) -> matière du corpus
COL_MATIERE = {"francais": "francais", "maths": "maths", "es_morale": "es", "es_civisme": "es", "es_histoire": "es",
               "es_geographie": "es", "est": "est", "eps": "eps", "ea_chant": "ea", "ea_poesie": "ea", "ea_conte": "ea",
               "ea_dessin": "ea", "ea_couture": "ea"}
ORDRE_MAT = ["francais", "maths", "es", "est", "eps", "ea", "dg"]
CHAMPS = [("titre", "Titre de la séance"), ("intitule", "Intitulé / thème"), ("sous_matiere", "Sous-matière / activité"),
          ("unite", "Unité / dossier / SA"), ("duree", "Durée"), ("cd", "Compétence disciplinaire"),
          ("ct", "Compétences transversales / transdisciplinaires"), ("contenus", "Contenus de formation (connaissances et techniques)"),
          ("objectifs", "Objectifs"), ("strategies", "Stratégies objet d'apprentissage / d'enseignement"),
          ("materiel", "Matériel"), ("evaluation", "Évaluation"), ("projection", "Projection / réinvestissement"),
          ("je_retiens", "Je retiens"), ("observations", "Observations de l'enseignant")]
CLES_TEXTE = [c for c, _l in CHAMPS]
MAX_LIGNES = 20
PAR_PAGE = 30
PAR_MATIERE = 6      # fiches proposées par matière pour la semaine (la liste complète reste filtrable)

SCHEMA = """
CREATE TABLE IF NOT EXISTS prep_fiches (
    id INTEGER PRIMARY KEY,
    ecole_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    classe_id INTEGER,
    date_seance TEXT,
    cours TEXT, matiere TEXT, sa INTEGER, seance INTEGER,
    titre TEXT NOT NULL,
    donnees TEXT NOT NULL,                -- JSON : champs APC + deroulement [[phase, activités, résultats]]
    source_id TEXT,                       -- fiche de la bibliothèque adaptée (id du corpus), modèle « modele:<id> »
    cree_le TEXT, maj_le TEXT
);
CREATE INDEX IF NOT EXISTS idx_prep_fiches ON prep_fiches (ecole_id, user_id, classe_id);
"""

_CORPUS = {}


def corpus():
    """Corpus pédagogique (chargé une fois) + index."""
    if not _CORPUS:
        import pdfs
        p = pdfs.fichier_static("pedafiche_corpus.json.gz")
        with gzip.open(p, "rt", encoding="utf-8") as f:
            c = json.load(f)
        for x in c["fiches"] + c["programmes"]:
            for k in ("sa", "seance", "num", "dossier"):
                v = x.get(k)
                if isinstance(v, str):
                    x[k] = int(v) if v.strip().isdigit() else None
        c["fiche_par_id"] = {x["id"]: x for x in c["fiches"]}
        c["guide_par_id"] = {x["id"]: x for x in c["guides"]}
        c["prog_par_id"] = {x["id"]: x for x in c["programmes"]}
        c["modele_par_id"] = {x["id"]: x for x in c["modeles"]}
        _CORPUS.update(c)
    return _CORPUS


def nom_matiere(m):
    return corpus()["matieres"].get(m, m)


def references(texte):
    """« U1 semaine2 à U3 semaine 1 », « D1 SA1 Séq 8 à 15 SA2 et 3 », « SA2 Séq3 à SA3 » -> numéros cités."""
    t = str(texte or "")
    sa = set()
    for m in re.finditer(r"SA\s*(\d+)((?:\s*(?:,|et|à|-)\s*\d+)*)", t, re.I):
        sa.add(int(m.group(1)))
        nums = [int(x) for x in re.findall(r"\d+", m.group(2) or "")]
        if re.search(r"à|-", m.group(2) or "") and nums:
            sa.update(range(int(m.group(1)), max(nums) + 1) if max(nums) - int(m.group(1)) < 12 else nums)
        else:
            sa.update(nums)
    u = {int(x) for x in re.findall(r"\bU\s*(\d+)", t)}
    dd = {int(x) for x in re.findall(r"\bD\s*(\d+)", t)}
    plages = re.findall(r"\bU\s*(\d+)[^U]*?à\s*U\s*(\d+)", t)
    for a, b in plages:
        if 0 <= int(b) - int(a) < 12:
            u.update(range(int(a), int(b) + 1))
    return {"sa": sorted(sa), "u": sorted(u), "d": sorted(dd)}


def num_unite(f):
    m = re.search(r"(\d+)", f.get("unite") or "")
    return int(m.group(1)) if m else None


def fiches_filtrees(cours=None, matiere=None, smat=None, sa=None, seance=None, texte=None, statut=None):
    out = corpus()["fiches"]
    if cours:
        out = [f for f in out if f["cours"] == cours]
    if matiere:
        out = [f for f in out if f["matiere"] == matiere]
    if smat:
        out = [f for f in out if (f.get("sous_matiere") or "") == smat]
    if sa:
        out = [f for f in out if f.get("sa") == sa]
    if seance:
        out = [f for f in out if f.get("seance") == seance]
    if statut in ("source", "concue"):
        out = [f for f in out if f.get("statut") == statut]
    if texte:
        mots = [_sans_accent(m) for m in texte.split() if m.strip()]

        def ok(f):
            h = _sans_accent(" ".join(str(f.get(k) or "") for k in ("titre", "intitule", "sous_matiere", "contenus", "unite", "source")))
            return all(m in h for m in mots)
        out = [f for f in out if ok(f)]
    return sorted(out, key=lambda f: (COURS.index(f["cours"]) if f["cours"] in COURS else 9,
                                      ORDRE_MAT.index(f["matiere"]) if f["matiere"] in ORDRE_MAT else 9,
                                      num_unite(f) or 0, f.get("sa") or 0, f.get("seance") or 0, f.get("titre") or ""))


def _sans_accent(t):
    import unicodedata
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()


def correspondances(cours, matiere, refs):
    """Fiches de la bibliothèque qui correspondent aux numéros cités par la planification (unités en français,
    dossiers puis SA en mathématiques, SA ailleurs)."""
    if not (refs["sa"] or refs["u"] or refs["d"]):
        return []
    out = []
    for f in fiches_filtrees(cours=cours, matiere=matiere):
        nu = num_unite(f)
        if matiere == "francais" and refs["u"]:
            ok = nu in refs["u"]
        elif matiere == "maths" and refs["d"]:
            ok = nu in refs["d"]          # les SA des fiches de mathématiques recommencent à chaque dossier
        else:
            ok = bool(refs["sa"]) and f.get("sa") in refs["sa"]
        if ok:
            out.append(f)
    return out


def refs_de_la_semaine(refs, matiere, jour):
    """Planification annuelle (un mois) : ne garder que l'unité / la SA de la semaine du mois en cours."""
    cle = "u" if matiere == "francais" and refs["u"] else "sa" if refs["sa"] else None
    if not cle or len(refs[cle]) < 2:
        return refs
    k = min(3, (jour.day - 1) // 7)
    liste = refs[cle]
    return dict(refs, **{cle: [liste[min(len(liste) - 1, k * len(liste) // 4)]]})


# ---------------------------------------------------------------- texte : HTML et PDF
def txt_html(t):
    """Texte de fiche (« **gras** », sauts de ligne, ▪) -> HTML échappé."""
    s = _html.escape(str(t or ""))
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    return s.replace("\n", "<br>")


def txt_pdf(t):
    s = str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("▪", "•").replace("\u25aa", "•").replace("\u2610", "□")   # glyphes absents de Helvetica
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s, flags=re.S)
    return s.replace("\n", "<br/>")


class _GuideVersPdf(HTMLParser):
    """HTML nettoyé d'un guide -> flowables reportlab (titres, paragraphes, listes, tableaux)."""

    def __init__(self, styles, largeur):
        super().__init__(convert_charrefs=True)
        self.st, self.largeur, self.out = styles, largeur, []
        self.tampon, self.bloc, self.liste, self.table, self.ligne, self.cellule = [], None, 0, None, None, None

    def _vider(self):
        t = "".join(self.tampon).strip()
        self.tampon = []
        if not t:
            return
        from reportlab.platypus import Paragraph
        st = {"h2": self.st["h2"], "h3": self.st["h3"], "h4": self.st["h4"]}.get(self.bloc, self.st["p"])
        if self.liste and self.bloc == "li":
            self.out.append(Paragraph("• " + t, self.st["li"]))
        else:
            self.out.append(Paragraph(t, st))

    def handle_starttag(self, tag, attrs):
        if tag in ("b", "strong", "i", "em", "u"):
            self.tampon.append({"strong": "<b>", "em": "<i>"}.get(tag, f"<{tag}>"))
        elif tag == "br":
            self.tampon.append("<br/>")
        elif tag == "table":
            self._vider()
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.ligne = []
        elif tag in ("td", "th") and self.ligne is not None:
            self.cellule = []
        elif tag in ("ul", "ol"):
            self._vider()
            self.liste += 1
        elif tag in ("h2", "h3", "h4", "p", "li"):
            self._vider()
            self.bloc = tag

    def handle_endtag(self, tag):
        if tag in ("b", "strong", "i", "em", "u"):
            t = {"strong": "</b>", "em": "</i>"}.get(tag, f"</{tag}>")
            (self.cellule if self.cellule is not None else self.tampon).append(t)
        elif tag in ("td", "th") and self.cellule is not None:
            self.ligne.append("".join(self.cellule).strip())
            self.cellule = None
        elif tag == "tr" and self.ligne is not None:
            self.table.append(self.ligne)
            self.ligne = None
        elif tag == "table" and self.table is not None:
            from reportlab.lib import colors
            from reportlab.platypus import Paragraph, Table, TableStyle
            n = max((len(r) for r in self.table), default=0)
            if n:
                data = [[Paragraph(c, self.st["td"]) for c in r] + [""] * (n - len(r)) for r in self.table]
                t = Table(data, colWidths=[self.largeur / n] * n, repeatRows=1)
                t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#667085")),
                                       ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                self.out.append(t)
            self.table = None
        elif tag in ("ul", "ol"):
            self._vider()
            self.liste = max(0, self.liste - 1)
        elif tag in ("h2", "h3", "h4", "p", "li"):
            self._vider()
            self.bloc = None

    def handle_data(self, data):
        d = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if self.cellule is not None:
            self.cellule.append(d)
        elif self.table is None:
            self.tampon.append(d)


# ---------------------------------------------------------------- v1.19 : résumés (PDF enseignant / élève)
COLLECTIONS_RES = [("maths", "Mathématiques CI → CM2"), ("francais", "Français CI → CM2"), ("francais-cm1", "Français CM1 (par unité)"),
                   ("es", "Éducation sociale CI → CM2"), ("est", "Éducation scientifique et technologique CI → CM2"),
                   ("eps", "Éducation physique et sportive CI → CM2"), ("ea", "Éducation artistique CI → CM2"), ("cep", "Révision CEP")]
COLLECTION_DE = {"Mathématiques": "maths", "Français": "francais", "Français CM1": "francais-cm1", "Éducation sociale": "es",
                 "Éducation scientifique et technologique": "est", "Éducation physique et sportive": "eps",
                 "Éducation artistique": "ea", "Révision CEP": "cep"}
COURS_RES = ["CI", "CP", "CE1", "CE2", "CM1", "CM2"]
MATS_RES = ["francais", "maths", "es", "est", "eps", "ea"]


def table_resumes(rs):
    """v1.23 — nombre de résumés par cours × matière (toutes collections confondues)."""
    t = {(c, m): 0 for c in COURS_RES for m in MATS_RES}
    for r in rs:
        if (r["cours"], r["matiere"]) in t:
            t[(r["cours"], r["matiere"])] += 1
    return t


def _num_fiche(f):
    """Numéro de SA / unité / dossier d'une fiche (Français : numéro d'unité)."""
    if f.get("matiere") == "francais":
        m = re.search(r"(\d+)", str(f.get("unite") or ""))
        if m:
            return int(m.group(1))
    for k in ("sa", "dossier"):
        if isinstance(f.get(k), int):
            return f[k]
    m = re.search(r"(?:SA|DOSSIER|UNIT[EÉ])\s*N?°?\s*(\d+)", str(f.get("unite") or ""), re.I)
    return int(m.group(1)) if m else None


def resumes_semaine(cours, fiches_par_mat):
    """v1.23 — résumés « l'essentiel à retenir » qui accompagnent les fiches d'une semaine : même cours, même matière,
    même SA / unité (champ « sa » du résumé) et, si le résumé en porte, une sous-matière concordante (« mots_cles »)."""
    out = {}
    rs = [r for r in corpus().get("resumes") or [] if r["cours"] == cours and r.get("collection") != "Révision CEP"]
    for mat, fiches in fiches_par_mat.items():
        if not fiches:
            continue
        nums = {_num_fiche(f) for f in fiches} - {None}
        sous = " | ".join((f.get("sous_matiere") or "").lower() for f in fiches).strip(" |")
        liste = []
        for r in rs:
            if r["matiere"] != mat:
                continue
            sa, mc = r.get("sa") or [], r.get("mots_cles") or []
            mc_ok = any(k in sous for k in mc)
            if sa:
                if not set(sa) & nums or (mc and sous and not mc_ok):
                    continue
            elif not mc_ok:
                continue
            liste.append(r)
        if liste:
            out[mat] = liste
    return out
_GLYPHES = {"→": "->", "−": "-", "ᵉ": "e", "ɔ": "o", "≈": "~", "≤": "<=", "≥": ">="}


def _res_txt(t):
    s = txt_pdf(t)
    for a, b in _GLYPHES.items():
        s = s.replace(a, b.replace("<", "&lt;").replace(">", "&gt;"))
    return s


def pdf_resumes(rs, eleve=False, titre_lot=None):
    """Résumés -> PDF A4 : règle, méthode, exemple, exercices ; corrigé (enseignant) ou lignes de réponse (élève)."""
    import pdfs
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    W, Hh = A4
    marge = 15 * mm
    larg = W - 2 * marge
    P = lambda n, **k: ParagraphStyle(n, **{"fontName": "Helvetica", "fontSize": 9.5, "leading": 12.5, **k})  # noqa: E731
    st = {"t": P("t", fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=colors.white),
          "s": P("s", fontSize=8, textColor=colors.HexColor("#475467")),
          "h": P("h", fontName="Helvetica-Bold", fontSize=9.5, textColor=pdfs.BLEU, spaceBefore=4, spaceAfter=1),
          "p": P("p"), "q": P("q", leftIndent=12, firstLineIndent=-12),
          "r": P("r", fontName="Helvetica-Oblique", textColor=colors.HexColor("#067647"), leftIndent=12),
          "l": P("l", textColor=colors.HexColor("#98A2B3"), leftIndent=12),
          "m": P("m", fontName="Helvetica-Oblique", fontSize=7, textColor=colors.grey)}
    histoire = []
    if titre_lot:
        histoire += [Paragraph(("FICHES DE RÉVISION — " if eleve else "RÉSUMÉS — L'ESSENTIEL À RETENIR — ") + _html.escape(titre_lot.upper()),
                               P("lot", fontName="Helvetica-Bold", fontSize=13, alignment=1, textColor=pdfs.BLEU, leading=17)),
                     Paragraph(f"{len(rs)} résumé(s)" + (" — version élève (sans les réponses)" if eleve else " — version enseignant (avec corrigé)"),
                               P("lot2", fontSize=8.5, alignment=1)), Spacer(1, 6)]
    for i, r in enumerate(rs):
        bandeau = Table([[Paragraph(_res_txt(r["titre"]), st["t"])]], colWidths=[larg])
        bandeau.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), pdfs.BLEU), ("TOPPADDING", (0, 0), (-1, -1), 4),
                                     ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
        regle = Table([[Paragraph("<b>Je retiens</b><br/>" + _res_txt(r["regle"]), st["p"])]], colWidths=[larg])
        regle.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF4FB")), ("BOX", (0, 0), (-1, -1), 0.6, pdfs.BLEU),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
        bloc = [bandeau, Paragraph(_html.escape(f"{r['collection']} · {r['cours']} · {r['domaine']}" + (f" · {r['etape']}" if r.get("etape") else "")), st["s"]),
                Spacer(1, 3), regle, Paragraph("Méthode", st["h"]), Paragraph(_res_txt(r["methode"]), st["p"]),
                Paragraph("Exemple", st["h"]), Paragraph(_res_txt(r["exemple"]), st["p"]), Paragraph("Exercices", st["h"])]
        for j, e in enumerate(r["exercices"], 1):
            bloc.append(Paragraph(f"{j}. " + _res_txt(e["q"]), st["q"]))
            bloc += ([Paragraph("…" * 46, st["l"])] if eleve else [Paragraph("Réponse : " + _res_txt(e["r"]), st["r"])])
        if not eleve:
            bloc.append(Paragraph(_html.escape(r.get("mention", "")), st["m"]))
        bloc.append(Spacer(1, 10))
        histoire.append(KeepTogether(bloc))
        if eleve and len(rs) > 1 and i % 2 == 1 and i + 1 < len(rs):
            histoire.append(PageBreak())

    def deco(c, doc):
        pdfs._entete_primaire(c, W, Hh, marge, None, None)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.grey)
        if eleve:
            c.drawString(marge, 7 * mm, "Nom : ………………………………………   Classe : ……………   Date : ……………")
        c.drawRightString(W - marge, 7 * mm, f"Page {doc.page}")
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=marge + 30 * mm, bottomMargin=13 * mm,
                      title=titre_lot or rs[0]["titre"], author="SCOLARIS").build(histoire, onFirstPage=deco, onLaterPages=deco, canvasmaker=pdfs.GCanvas)
    return buf.getvalue()


def enregistrer(app, H):
    q, ex, config = H.q, H.ex, H.config
    H.schema(SCHEMA)

    @app.template_filter("prep_txt")
    def _f_txt(t):
        from markupsafe import Markup
        return Markup(txt_html(t))

    @app.context_processor
    def _ctx():
        return {"PREP_COURS_LIB": COURS_LIB, "prep_nom_matiere": nom_matiere}

    # ------------------------------------------------------------ outils
    def classes():
        return [c for c in H.classes_autorisees() if c["niveau"] in NIVEAU_COURS]

    def peut_ecrire(cid):
        return g.user["role"] in ("enseignant", "directeur", "admin", "fondateur") and cid in {c["id"] for c in classes()}

    def effectif(cid):
        r = q("SELECT SUM(CASE WHEN sexe='M' THEN 1 ELSE 0 END) g, SUM(CASE WHEN sexe='F' THEN 1 ELSE 0 END) f, COUNT(*) t "
              "FROM eleves WHERE classe_id=? AND statut='inscrit'", (cid,), un=True)
        return {"g": r["g"] or 0, "f": r["f"] or 0, "t": r["t"] or 0}

    def mois_courant(auj=None):
        auj = auj or date.today()
        return auj if auj.month not in (7, 8) else date(auj.year, 9, 1)

    def plan_annuel(niveau_syno, mois_lib):
        import m_synoptique as S
        r = q("SELECT contenu FROM synoptique_planification WHERE ecole_id=? AND niveau=?", (H.eco(), niveau_syno), un=True)
        lignes = json.loads(r["contenu"]) if r else S.planification_defaut(niveau_syno)
        return next((l for l in lignes if _sans_accent(l.get("mois", "")) == _sans_accent(mois_lib)), None)

    def plan_semaine(cl, auj):
        """Cases de la planification mensuelle de la classe pour la semaine en cours : {matière: texte}, (du, au)."""
        try:
            liste = H.planification_mensuelle(H.eco(), config.ANNEE_ACTIVE, cl["id"])
        except Exception:  # noqa: BLE001
            return {}, None
        mois = f"{auj.year}-{auj.month:02d}"
        pm = next((p for p in liste if p.get("mois") == mois), None)
        if not pm:
            return {}, None
        iso = auj.isoformat()
        k = next((i for i, s in enumerate(pm["semaines"]) if s.get("du") and s.get("au") and s["du"] <= iso <= s["au"]), None)
        if k is None:
            return {}, None
        out = {}
        for code, cases in (pm.get("contenu") or {}).items():
            m = "francais" if code.startswith("fr_") else COL_MATIERE.get(code) or ("ea" if code.startswith("ea_") else
                                                                                   "es" if code.startswith("es_") else None)
            v = (cases[k] if k < len(cases) else "").strip()
            if m and v and re.search(r"\d", v):      # une case citant une SA / unité / dossier (pas un gabarit vide)
                out[m] = (out.get(m, "") + " ; " + v).strip(" ;")
        return out, (pm["semaines"][k]["du"], pm["semaines"][k]["au"])

    def cette_semaine(cl, auj=None):
        auj = auj or date.today()
        cours = NIVEAU_COURS.get(cl["niveau"])
        niv = NIVEAU_SYNO.get(cl["niveau"])
        mc = mois_courant(auj)
        ligne = plan_annuel(niv, MOIS_FR[mc.month - 1]) if niv else None
        semaine, bornes = plan_semaine(cl, auj)
        mats = []
        for m in ORDRE_MAT:
            ann = "; ".join(str(ligne.get(k) or "") for k, mm in COL_MATIERE.items() if mm == m and (ligne or {}).get(k)) if ligne else ""
            sem = semaine.get(m, "")
            if not (ann or sem):
                continue
            refs = references(sem or ann)
            if not sem:
                refs = refs_de_la_semaine(refs, m, auj)
            toutes = correspondances(cours, m, refs)
            mats.append({"matiere": m, "nom": nom_matiere(m), "annuel": ann, "semaine": sem, "refs": refs,
                         "fiches": toutes[:PAR_MATIERE], "total": len(toutes), "ids": [f["id"] for f in toutes]})
        return {"classe": cl, "cours": cours, "mois": MOIS_FR[mc.month - 1], "bornes": bornes, "matieres": mats}

    def fiche_corpus(fid):
        f = corpus()["fiche_par_id"].get(fid)
        if not f:
            abort(404)
        return f

    def ma_fiche(mid, ecrire=False):
        r = q("SELECT * FROM prep_fiches WHERE id=? AND ecole_id=?", (mid, H.eco()), un=True)
        if not r:
            abort(404)
        if g.user["role"] == "enseignant" and r["user_id"] != g.user["id"]:
            abort(403)
        if ecrire and r["user_id"] != g.user["id"]:
            abort(403)
        d = json.loads(r["donnees"])
        d.update({"id": r["id"], "classe_id": r["classe_id"], "date_seance": r["date_seance"], "cours": r["cours"],
                  "matiere": r["matiere"], "sa": r["sa"], "seance": r["seance"], "titre": r["titre"], "source_id": r["source_id"],
                  "user_id": r["user_id"], "maj_le": r["maj_le"]})
        return d

    def lire_formulaire(f):
        d = {k: (f.get(k) or "").strip()[:4000] for k in CLES_TEXTE}
        d["matiere"] = f.get("matiere") if f.get("matiere") in corpus()["matieres"] else "francais"
        for k in ("sa", "seance"):
            v = (f.get(k) or "").strip()
            d[k] = int(v) if v.isdigit() and int(v) < 1000 else None
        lignes = []
        for i in range(MAX_LIGNES):
            ph, ac, re_ = (f.get(f"ph_{i}") or "").strip()[:500], (f.get(f"ac_{i}") or "").strip()[:6000], (f.get(f"re_{i}") or "").strip()[:2000]
            if ph or ac or re_:
                lignes.append([ph, ac, re_])
        d["deroulement"] = lignes
        ds = (f.get("date_seance") or "").strip()
        try:
            d["date_seance"] = datetime.strptime(ds, "%Y-%m-%d").date().isoformat() if ds else None
        except ValueError:
            d["date_seance"] = None
        try:
            d["classe_id"] = int(f.get("classe") or 0) or None
        except ValueError:
            d["classe_id"] = None
        return d

    def fiche_vierge(cl=None, matiere="francais"):
        return {"matiere": matiere, "cours": NIVEAU_COURS.get(cl["niveau"]) if cl else "", "titre": "", "duree": "45 min",
                "strategies": "Travail individuel — travail en groupe — travail collectif",
                "deroulement": [["**INTRODUCTION**\n\nMise en situation", "▪ Rappel / prérequis.\n▪ Situation de départ.\n▪ Proposition : aujourd'hui, tu vas apprendre …", "Réponses variables."],
                                ["**RÉALISATION**", "▪ Tâche / consignes.\n▪ Travail individuel, en groupe, mise en commun.\n▪ Synthèse.", ""],
                                ["**RETOUR ET PROJECTION**", "▪ Objectivation : dis ce que tu as appris et comment.\n▪ Évaluation.\n▪ Projection.", ""]]}

    def depuis_modele(m, cl):
        d = fiche_vierge(cl, m.get("matiere") or "francais")
        d.update({"titre": m.get("libelle", ""), "cd": m.get("cd", ""), "contenus": m.get("contenus", ""),
                  "strategies": m.get("strategies") or d["strategies"], "materiel": m.get("materiel", ""),
                  "deroulement": [["**INTRODUCTION**", m.get("introduction", ""), ""], ["**RÉALISATION**", m.get("realisation", ""), ""],
                                  ["**RETOUR ET PROJECTION**", m.get("retour", ""), ""]]})
        return d

    def entete_classe(d):
        cl = q("SELECT * FROM classes WHERE id=?", (d.get("classe_id"),), un=True) if d.get("classe_id") else None
        return cl, (effectif(cl["id"]) if cl else None)

    # ------------------------------------------------------------ PDF et Word
    def pdf_fiches(fiches, titre_doc="FICHE DE PRÉPARATION"):
        """Une ou plusieurs fiches (une par page au moins) au format APC ; document vérifiable (QR)."""
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        W, Hh = A4
        marge = 12 * mm
        utile = W - 2 * marge
        st = ParagraphStyle("c", fontName="Helvetica", fontSize=8.3, leading=10.3)
        stb = ParagraphStyle("b", parent=st, fontName="Helvetica-Bold")
        sth = ParagraphStyle("h", parent=stb, textColor=colors.white, alignment=1)
        sti = ParagraphStyle("ti", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, textColor=pdfs.BLEU)
        sts = ParagraphStyle("st", fontName="Helvetica", fontSize=9.5, leading=12, alignment=1, spaceAfter=4)
        stm = ParagraphStyle("m", parent=st, fontName="Helvetica-Oblique", textColor=colors.HexColor("#B54708"))
        eid = H.eco()
        s_dir = pdfs.image_data_url(H.signature(f"ecole:{eid}:directeur")) or pdfs.signature_directeur()
        histoire, cles = [], []
        for n, d in enumerate(fiches):
            cl, eff = entete_classe(d)
            if n:
                histoire.append(PageBreak())
            histoire.append(Paragraph(titre_doc, sti))
            histoire.append(Paragraph(f"{nom_matiere(d.get('matiere'))} — {COURS_LIB.get(d.get('cours'), d.get('cours') or '')}"
                                      + (f" — {txt_pdf(d.get('sous_matiere'))}" if d.get("sous_matiere") else ""), sts))
            infos = [("École", config.ECOLE.get("nom", "")), ("Classe", cl["nom"] if cl else (d.get("cours") or "")),
                     ("Date", datetime.strptime(d["date_seance"], "%Y-%m-%d").strftime("%d/%m/%Y") if d.get("date_seance") else "…… / …… / ……"),
                     ("Effectif", f"G : {eff['g']}   F : {eff['f']}   T : {eff['t']}" if eff else "G : ……  F : ……  T : ……"),
                     ("Unité / SA", " · ".join(x for x in [d.get("unite") or "", f"SA n°{d['sa']}" if d.get("sa") else "",
                                                           f"Séance n°{d['seance']}" if d.get("seance") else ""] if x) or "—"),
                     ("Durée", d.get("duree") or "—")]
            grille = []
            for i in range(0, len(infos), 2):
                ligne = []
                for lab, val in infos[i:i + 2]:
                    ligne += [Paragraph(f"<b>{lab}</b>", st), Paragraph(txt_pdf(val), st)]
                grille.append(ligne + [""] * (4 - len(ligne)))
            lw = 22 * mm
            ti = Table(grille, colWidths=[lw, utile / 2 - lw] * 2)
            ti.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, pdfs.BLEU), ("BACKGROUND", (0, 0), (-1, -1), pdfs.GRIS),
                                    ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
            histoire += [ti, Spacer(1, 4)]
            histoire.append(Paragraph(f"<b>Titre :</b> {txt_pdf(d.get('titre'))}" + (f" — <i>{txt_pdf(d.get('intitule'))}</i>" if d.get("intitule") and d.get("intitule") != d.get("titre") else ""), st))
            histoire.append(Spacer(1, 3))
            blocs = [(lib, d.get(k)) for k, lib in CHAMPS if k in ("cd", "ct", "contenus", "objectifs", "strategies", "materiel") and d.get(k)]
            if blocs:
                tb = Table([[Paragraph(f"<b>{lib}</b>", st), Paragraph(txt_pdf(v), st)] for lib, v in blocs], colWidths=[42 * mm, utile - 42 * mm])
                tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF4FA"))]))
                histoire += [tb, Spacer(1, 5)]
            lignes = d.get("deroulement") or []
            data = [[Paragraph("Phases / étapes", sth), Paragraph("Activités de l'enseignant(e) et des apprenant(e)s", sth),
                     Paragraph("Résultats attendus / évaluation", sth)]]
            data += [[Paragraph(txt_pdf(a), stb), Paragraph(txt_pdf(b), st), Paragraph(txt_pdf(c), st)] for a, b, c in [(l + ["", "", ""])[:3] for l in lignes]]
            td = Table(data, colWidths=[30 * mm, utile - 30 * mm - 42 * mm, 42 * mm], repeatRows=1)
            td.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#667085")), ("BACKGROUND", (0, 0), (-1, 0), pdfs.BLEU),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")])]))
            histoire += [Paragraph("<b>DÉROULEMENT</b>", st), Spacer(1, 2), td, Spacer(1, 5)]
            for k in ("evaluation", "projection", "je_retiens", "observations"):
                if d.get(k):
                    histoire.append(Paragraph(f"<b>{dict(CHAMPS)[k]} :</b><br/>{txt_pdf(d[k])}", st))
                    histoire.append(Spacer(1, 3))
            if d.get("mention"):
                histoire.append(Paragraph(txt_pdf(d["mention"]), stm))
            if d.get("source"):
                histoire.append(Paragraph(f"Source : {txt_pdf(d['source'])}", ParagraphStyle("so", parent=st, fontSize=7, textColor=colors.grey)))
            u = q("SELECT * FROM utilisateurs WHERE id=?", (d.get("user_id"),), un=True) if d.get("user_id") else None
            s_ens = pdfs.image_data_url(H.signature_enseignant(u["id"]) if u else (H.signature_titulaire(cl["id"]) if cl else None))
            sigs = [("L'enseignant(e)", (u["nom"] if u else ""), s_ens, False), ("Visa du directeur / de la directrice", "", s_dir, True)]
            cle_fiche = f"{d.get('id') or d.get('source_id') or ''}|{d.get('titre')}|{d.get('date_seance')}|{cl['nom'] if cl else ''}"
            cles.append(cle_fiche)
            code = pdfs.code_tableau(titre_doc, d.get("titre"), [("Classe", cl["nom"] if cl else d.get("cours")), ("Matière", nom_matiere(d.get("matiere")))],
                                     lignes, None, ("fiche_preparation", f"Fiche de préparation – {d.get('titre', '')[:120]} – {cl['nom'] if cl else d.get('cours', '')}"))
            histoire.append(Spacer(1, 4))
            histoire.append(KeepTogether([pdfs._BlocSignatures(sigs, utile, code=code)]))

        def deco(c, doc):
            pdfs._entete_primaire(c, W, Hh, marge, None, "maternelle" if fiches and fiches[0].get("cours") == "MAT" else None)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(colors.grey)
            c.drawString(marge, 7 * mm, f"SCOLARIS · {config.ECOLE.get('nom', '')} · {config.ANNEE_ACTIVE}")
            c.drawRightString(W - marge, 7 * mm, f"Page {doc.page} · imprimé le {date.today().strftime('%d/%m/%Y')}")
            c.setFillColor(colors.black)
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=marge + 30 * mm,
                                bottomMargin=13 * mm, title=titre_doc, author="SCOLARIS")
        doc.build(histoire, onFirstPage=deco, onLaterPages=deco, canvasmaker=pdfs.GCanvas)
        return buf.getvalue()

    def doc_word(fiches, titre_doc="FICHE DE PRÉPARATION"):
        parts = []
        for d in fiches:
            cl, eff = entete_classe(d)
            lignes = "".join(f"<tr><td><b>{txt_html(a)}</b></td><td>{txt_html(b)}</td><td>{txt_html(c)}</td></tr>"
                             for a, b, c in [(l + ['', '', ''])[:3] for l in d.get("deroulement") or []])
            blocs = "".join(f"<tr><th>{lib}</th><td>{txt_html(d.get(k))}</td></tr>" for k, lib in CHAMPS
                            if k in ("cd", "ct", "contenus", "objectifs", "strategies", "materiel") and d.get(k))
            fin = "".join(f"<p><b>{dict(CHAMPS)[k]} :</b><br>{txt_html(d[k])}</p>" for k in ("evaluation", "projection", "je_retiens", "observations") if d.get(k))
            parts.append(f"""<h1>{titre_doc}</h1><p class=c>{_html.escape(nom_matiere(d.get('matiere')))} — {_html.escape(COURS_LIB.get(d.get('cours'), d.get('cours') or ''))}
<br>{_html.escape(config.ECOLE.get('nom', ''))} · Classe : {_html.escape(cl['nom'] if cl else '')} · Date : {_html.escape(d.get('date_seance') or '……')}
· Effectif : {('G ' + str(eff['g']) + ' / F ' + str(eff['f']) + ' / T ' + str(eff['t'])) if eff else '……'}</p>
<p><b>Titre :</b> {txt_html(d.get('titre'))} · {txt_html(d.get('unite'))} {('SA n°' + str(d['sa'])) if d.get('sa') else ''} {('Séance n°' + str(d['seance'])) if d.get('seance') else ''} · Durée : {txt_html(d.get('duree'))}</p>
<table>{blocs}</table><h2>Déroulement</h2><table><tr><th>Phases / étapes</th><th>Activités de l'enseignant(e) et des apprenant(e)s</th><th>Résultats attendus / évaluation</th></tr>{lignes}</table>
{fin}{('<p><i>' + txt_html(d['mention']) + '</i></p>') if d.get('mention') else ''}""")
        corps = "<br style='page-break-before:always'>".join(parts)
        h = ("<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word'><head><meta charset='utf-8'>"
             f"<title>{titre_doc}</title><style>body{{font-family:Calibri,Arial;font-size:11pt}}table{{border-collapse:collapse;width:100%}}"
             "td,th{border:1px solid #666;padding:4px;vertical-align:top}th{background:#E4ECF5;text-align:left}h1{text-align:center;color:#1F4E79;font-size:16pt}"
             f".c{{text-align:center}}</style></head><body>{corps}</body></html>")
        return h

    def reponse_doc(contenu, nom):
        return Response("﻿" + contenu, mimetype="application/msword",
                        headers={"Content-Disposition": f"attachment; filename={nom}"})

    def nom_fichier(d, ext):
        base = re.sub(r"[^A-Za-z0-9]+", "_", _sans_accent(f"fiche_{d.get('cours', '')}_{d.get('matiere', '')}_{d.get('titre', '')}"))[:80].strip("_")
        return f"{base or 'fiche'}.{ext}"

    # ------------------------------------------------------------ pages
    @app.route("/preparation")
    @H.connexion_requise("preparation")
    def prep_accueil():
        semaines = [cette_semaine(c) for c in classes()]
        nb = q("SELECT COUNT(*) n FROM prep_fiches WHERE ecole_id=? AND user_id=?", (H.eco(), g.user["id"]), un=True)["n"]
        C = corpus()
        return render_template("prep_accueil.html", semaines=semaines, nb_mes=nb, nb_fiches=len(C["fiches"]),
                               nb_guides=len(C["guides"]), nb_prog=len(C["programmes"]), aujourd=date.today())

    @app.route("/preparation/programmes")
    @H.connexion_requise("preparation")
    def prep_programmes():
        C = corpus()
        cours = request.args.get("cours") or ""
        mat = request.args.get("matiere") or ""
        progs = [p for p in C["programmes"] if (not cours or p["cours"] == cours) and (not mat or p["matiere"] == mat)]
        progs.sort(key=lambda p: (COURS.index(p["cours"]) if p["cours"] in COURS else 9, ORDRE_MAT.index(p["matiere"]) if p["matiere"] in ORDRE_MAT else 9,
                                  p.get("dossier") or 0, p.get("num") or 0))
        dispo = sorted({(p["cours"], p["matiere"]) for p in C["programmes"]}, key=lambda x: (COURS.index(x[0]), ORDRE_MAT.index(x[1])))
        # planification annuelle officielle du cours (toutes matières) en complément
        import m_synoptique as S
        niv = {v: k for k, v in NIVEAU_COURS.items() if v != "MAT"}.get(cours)
        plan = None
        if niv:
            r = q("SELECT contenu FROM synoptique_planification WHERE ecole_id=? AND niveau=?", (H.eco(), NIVEAU_SYNO[niv]), un=True)
            plan = json.loads(r["contenu"]) if r else S.planification_defaut(NIVEAU_SYNO[niv])
        return render_template("prep_programmes.html", progs=progs, cours=cours, mat=mat, dispo=dispo, COURS=COURS,
                               MATS=[m for m in ORDRE_MAT], plan=plan, cols=S.COLS_PLAN)

    @app.route("/preparation/programmes/<pid>")
    @H.connexion_requise("preparation")
    def prep_programme(pid):
        p = corpus()["prog_par_id"].get(pid)
        if not p:
            abort(404)
        nums = [p.get("num")] if p.get("num") else []
        fiches = [f for f in fiches_filtrees(cours=p["cours"], matiere=p["matiere"])
                  if (p.get("type") == "unite" and num_unite(f) == p.get("num")) or (p.get("type") == "sa" and f.get("sa") in nums)]
        return render_template("prep_programme.html", p=p, fiches=fiches[:60])

    @app.route("/preparation/guides")
    @H.connexion_requise("preparation")
    def prep_guides():
        C = corpus()
        mat = request.args.get("matiere") or ""
        cours = request.args.get("cours") or ""
        gs = [x for x in C["guides"] if (not mat or x["matiere"] == mat) and (not cours or cours in (x.get("cours") or []))]
        groupes = {}
        for x in sorted(gs, key=lambda x: (ORDRE_MAT.index(x["matiere"]) if x["matiere"] in ORDRE_MAT else 9, x.get("groupe", ""), x["titre"])):
            groupes.setdefault(nom_matiere(x["matiere"]), []).append(x)
        return render_template("prep_guides.html", groupes=groupes, mat=mat, cours=cours, MATS=ORDRE_MAT, COURS=COURS)

    @app.route("/preparation/guides/<gid>")
    @H.connexion_requise("preparation")
    def prep_guide(gid):
        x = corpus()["guide_par_id"].get(gid)
        if not x:
            abort(404)
        from markupsafe import Markup
        return render_template("prep_guide.html", x=x, contenu=Markup(x["html"]))   # HTML nettoyé à la construction du corpus

    @app.route("/preparation/guides/<gid>.pdf")
    @H.connexion_requise("preparation")
    def prep_guide_pdf(gid):
        x = corpus()["guide_par_id"].get(gid)
        if not x:
            abort(404)
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
        W, Hh = A4
        marge = 15 * mm
        st = {"p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5, leading=12.5, spaceAfter=4),
              "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.5, leading=12.5, leftIndent=10, spaceAfter=2),
              "td": ParagraphStyle("td", fontName="Helvetica", fontSize=7.8, leading=9.5),
              "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=pdfs.BLEU, spaceBefore=6, spaceAfter=6),
              "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=pdfs.BLEU, spaceBefore=6, spaceAfter=3),
              "h4": ParagraphStyle("h4", fontName="Helvetica-Bold", fontSize=10, leading=13, spaceBefore=4, spaceAfter=2)}
        conv = _GuideVersPdf(st, W - 2 * marge)
        conv.feed(x["html"])
        conv.close()
        conv._vider()
        histoire = [Paragraph(f"GUIDE PÉDAGOGIQUE — {nom_matiere(x['matiere']).upper()}", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14, alignment=1, textColor=pdfs.BLEU, leading=18)),
                    Paragraph(f"{_html.escape(x['titre'])} · {', '.join(COURS_LIB.get(c, c) for c in x.get('cours') or [])}", ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, alignment=1, leading=12)),
                    Spacer(1, 6)] + conv.out
        if x.get("mention"):
            histoire += [Spacer(1, 6), Paragraph(_html.escape(x["mention"]), ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#B54708")))]
        histoire.append(Paragraph(f"Source : {_html.escape(x.get('source', ''))}", ParagraphStyle("so", fontName="Helvetica", fontSize=7, textColor=colors.grey)))

        def deco(c, doc):
            pdfs._entete_primaire(c, W, Hh, marge, None, None)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(colors.grey)
            c.drawRightString(W - marge, 7 * mm, f"Page {doc.page}")
        buf = io.BytesIO()
        SimpleDocTemplate(buf, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=marge + 30 * mm, bottomMargin=13 * mm,
                          title=x["titre"], author="SCOLARIS").build(histoire, onFirstPage=deco, onLaterPages=deco, canvasmaker=pdfs.GCanvas)
        return H.pdf_reponse(buf.getvalue(), re.sub(r"[^A-Za-z0-9]+", "_", _sans_accent("guide_" + x["titre"]))[:70] + ".pdf")

    @app.route("/preparation/fiches")
    @H.connexion_requise("preparation")
    def prep_fiches():
        a = request.args
        cours, mat, smat = a.get("cours") or "", a.get("matiere") or "", a.get("smat") or ""
        sa = a.get("sa", type=int)
        seance = a.get("seance", type=int)
        texte = (a.get("q") or "").strip()
        statut = a.get("statut") or ""
        cid = a.get("classe", type=int)
        semaine = None
        if a.get("semaine") and cid:
            cl = next((c for c in classes() if c["id"] == cid), None)
            if cl:
                semaine = cette_semaine(cl)
                ids = []
                for m in semaine["matieres"]:
                    if not mat or m["matiere"] == mat:
                        ids += m.get("ids") or [f["id"] for f in m["fiches"]]   # v1.19 : toutes les fiches de la semaine
                liste = [corpus()["fiche_par_id"][i] for i in ids]
            else:
                liste = []
        else:
            liste = fiches_filtrees(cours or None, mat or None, smat or None, sa, seance, texte or None, statut or None)
        page = max(1, a.get("page", 1, type=int))
        total = len(liste)
        smats = sorted({f.get("sous_matiere") for f in fiches_filtrees(cours or None, mat or None) if f.get("sous_matiere")})
        return render_template("prep_fiches.html", fiches=liste[(page - 1) * PAR_PAGE: page * PAR_PAGE], total=total, page=page,
                               pages=(total + PAR_PAGE - 1) // PAR_PAGE, cours=cours, mat=mat, smat=smat, sa=sa, seance=seance, q=texte,
                               statut=statut, smats=smats, COURS=COURS, MATS=ORDRE_MAT, classes=classes(), cid=cid, semaine=semaine)

    @app.route("/preparation/fiches/<fid>")
    @H.connexion_requise("preparation")
    def prep_fiche(fid):
        f = fiche_corpus(fid)
        return render_template("prep_fiche.html", f=f, classes=classes(), propre=False, CHAMPS=CHAMPS)

    @app.route("/preparation/fiches/<fid>.pdf")
    @H.connexion_requise("preparation")
    def prep_fiche_pdf(fid):
        f = dict(fiche_corpus(fid))
        cid = request.args.get("classe", type=int)
        if cid and any(c["id"] == cid and NIVEAU_COURS.get(c["niveau"]) == f.get("cours") for c in classes()):
            f["classe_id"] = cid
        f["source_id"] = fid
        H.journal("prep_fiche_pdf", f["titre"][:120])
        return H.pdf_reponse(pdf_fiches([f]), nom_fichier(f, "pdf"))

    @app.route("/preparation/fiches/<fid>.doc")
    @H.connexion_requise("preparation")
    def prep_fiche_doc(fid):
        f = dict(fiche_corpus(fid))
        cid = request.args.get("classe", type=int)
        if cid and any(c["id"] == cid and NIVEAU_COURS.get(c["niveau"]) == f.get("cours") for c in classes()):
            f["classe_id"] = cid
        return reponse_doc(doc_word([f]), nom_fichier(f, "doc"))

    @app.route("/preparation/semaine.pdf")
    @H.connexion_requise("preparation")
    def prep_semaine_pdf():
        cid = request.args.get("classe", type=int)
        cl = next((c for c in classes() if c["id"] == cid), None)
        if not cl:
            abort(404)
        s = cette_semaine(cl)
        fiches = [dict(f, classe_id=cid, source_id=f["id"]) for m in s["matieres"] for f in m["fiches"]]
        du, au = s["bornes"] or (None, None)
        mes = q("SELECT id FROM prep_fiches WHERE ecole_id=? AND user_id=? AND classe_id=? AND date_seance BETWEEN ? AND ? ORDER BY date_seance",
                (H.eco(), g.user["id"], cid, du or "0000", au or "9999")) if du else []
        fiches = [ma_fiche(r["id"]) for r in mes] + fiches
        if not fiches:
            flash("Aucune fiche pour cette semaine : la planification de la classe ne cite pas encore de SA, d'unité ou de dossier.", "warning")
            return redirect(url_for("prep_accueil"))
        H.journal("prep_semaine_pdf", f"{cl['nom']} : {len(fiches)} fiche(s)")
        return H.pdf_reponse(pdf_fiches(fiches), f"fiches_semaine_{re.sub(r'[^A-Za-z0-9]+', '_', cl['nom'])}.pdf")

    @app.route("/preparation/preparer", methods=["GET", "POST"])
    @H.connexion_requise("preparation")
    def prep_preparer():
        cls = classes()
        if not cls:
            flash("Aucune classe : la préparation d'une fiche se fait pour une de vos classes.", "warning")
            return redirect(url_for("prep_accueil"))
        if request.method == "POST":
            d = lire_formulaire(request.form)
            if not d["classe_id"] or not peut_ecrire(d["classe_id"]):
                abort(403)
            if not d["titre"]:
                flash("Le titre de la séance est obligatoire.", "danger")
                return render_template("prep_form.html", d=d, classes=cls, CHAMPS=CHAMPS, MATS=ORDRE_MAT, nouveau=True, MAX=MAX_LIGNES), 400
            cl = next(c for c in cls if c["id"] == d["classe_id"])
            maint = H.maintenant()
            mid = ex("INSERT INTO prep_fiches (ecole_id, user_id, classe_id, date_seance, cours, matiere, sa, seance, titre, donnees, source_id, cree_le, maj_le) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (H.eco(), g.user["id"], cl["id"], d["date_seance"], NIVEAU_COURS.get(cl["niveau"]), d["matiere"], d["sa"], d["seance"],
                      d["titre"][:300], json.dumps({k: d[k] for k in CLES_TEXTE + ["deroulement"]}, ensure_ascii=False),
                      (request.form.get("source_id") or "")[:80] or None, maint, maint))
            H.journal("prep_fiche_creee", f"{cl['nom']} : {d['titre'][:120]}")
            flash("Fiche enregistrée dans « Mes fiches ».", "success")
            return redirect(url_for("prep_ma_fiche", mid=mid))
        cid = request.args.get("classe", type=int)
        cl = next((c for c in cls if c["id"] == cid), cls[0])
        src = request.args.get("depuis") or ""
        mod = request.args.get("modele") or ""
        if src:
            f = fiche_corpus(src)
            d = {k: f.get(k, "") for k in CLES_TEXTE}
            d.update({"matiere": f["matiere"], "sa": f.get("sa"), "seance": f.get("seance"), "deroulement": [list(l) for l in f.get("deroulement") or []],
                      "source_id": src})
            if f.get("cours") != NIVEAU_COURS.get(cl["niveau"]):
                cl = next((c for c in cls if NIVEAU_COURS.get(c["niveau"]) == f.get("cours")), cl)
        elif mod and mod in corpus()["modele_par_id"]:
            d = depuis_modele(corpus()["modele_par_id"][mod], cl)
            d["source_id"] = "modele:" + mod
        else:
            d = fiche_vierge(cl, request.args.get("matiere") if request.args.get("matiere") in corpus()["matieres"] else "francais")
        d["classe_id"] = cl["id"]
        d["date_seance"] = request.args.get("date") or date.today().isoformat()
        modeles = sorted(corpus()["modeles"], key=lambda m: (ORDRE_MAT.index(m["matiere"]) if m["matiere"] in ORDRE_MAT else 9, m["libelle"]))
        return render_template("prep_form.html", d=d, classes=cls, CHAMPS=CHAMPS, MATS=ORDRE_MAT, nouveau=True, MAX=MAX_LIGNES, modeles=modeles)

    @app.route("/preparation/mes-fiches")
    @H.connexion_requise("preparation")
    def prep_mes_fiches():
        if g.user["role"] == "enseignant":
            rows = q("SELECT p.*, c.nom classe_nom FROM prep_fiches p LEFT JOIN classes c ON c.id=p.classe_id WHERE p.ecole_id=? AND p.user_id=? "
                     "ORDER BY COALESCE(p.date_seance, p.maj_le) DESC", (H.eco(), g.user["id"]))
        else:
            rows = q("SELECT p.*, c.nom classe_nom, u.nom auteur FROM prep_fiches p LEFT JOIN classes c ON c.id=p.classe_id "
                     "LEFT JOIN utilisateurs u ON u.id=p.user_id WHERE p.ecole_id=? ORDER BY COALESCE(p.date_seance, p.maj_le) DESC", (H.eco(),))
        return render_template("prep_mes_fiches.html", rows=rows)

    @app.route("/preparation/mes-fiches/<int:mid>", methods=["GET", "POST"])
    @H.connexion_requise("preparation")
    def prep_ma_fiche(mid):
        d = ma_fiche(mid)
        modif = request.args.get("modifier") or request.method == "POST"
        if request.method == "POST":
            ma_fiche(mid, ecrire=True)
            n = lire_formulaire(request.form)
            if not n["classe_id"] or not peut_ecrire(n["classe_id"]):
                abort(403)
            if not n["titre"]:
                flash("Le titre de la séance est obligatoire.", "danger")
                return render_template("prep_form.html", d={**d, **n}, classes=classes(), CHAMPS=CHAMPS, MATS=ORDRE_MAT, nouveau=False, MAX=MAX_LIGNES), 400
            cl = next(c for c in classes() if c["id"] == n["classe_id"])
            ex("UPDATE prep_fiches SET classe_id=?, date_seance=?, cours=?, matiere=?, sa=?, seance=?, titre=?, donnees=?, maj_le=? WHERE id=?",
               (cl["id"], n["date_seance"], NIVEAU_COURS.get(cl["niveau"]), n["matiere"], n["sa"], n["seance"], n["titre"][:300],
                json.dumps({k: n[k] for k in CLES_TEXTE + ["deroulement"]}, ensure_ascii=False), H.maintenant(), mid))
            H.journal("prep_fiche_modifiee", n["titre"][:120])
            flash("Fiche modifiée.", "success")
            return redirect(url_for("prep_ma_fiche", mid=mid))
        if modif and d["user_id"] == g.user["id"]:
            return render_template("prep_form.html", d=d, classes=classes(), CHAMPS=CHAMPS, MATS=ORDRE_MAT, nouveau=False, MAX=MAX_LIGNES)
        return render_template("prep_fiche.html", f=d, classes=classes(), propre=True, CHAMPS=CHAMPS,
                               auteur=d["user_id"] == g.user["id"])

    @app.route("/preparation/mes-fiches/<int:mid>/dupliquer", methods=["POST"])
    @H.connexion_requise("preparation")
    def prep_ma_fiche_dupliquer(mid):
        ma_fiche(mid, ecrire=True)
        maint = H.maintenant()
        nid = ex("INSERT INTO prep_fiches (ecole_id, user_id, classe_id, date_seance, cours, matiere, sa, seance, titre, donnees, source_id, cree_le, maj_le) "
                 "SELECT ecole_id, user_id, classe_id, NULL, cours, matiere, sa, seance, titre || ' (copie)', donnees, source_id, ?, ? FROM prep_fiches WHERE id=?",
                 (maint, maint, mid))
        flash("Fiche dupliquée : choisissez la date de la nouvelle séance.", "success")
        return redirect(url_for("prep_ma_fiche", mid=nid, modifier=1))

    @app.route("/preparation/mes-fiches/<int:mid>/supprimer", methods=["POST"])
    @H.connexion_requise("preparation")
    def prep_ma_fiche_supprimer(mid):
        d = ma_fiche(mid, ecrire=True)
        ex("DELETE FROM prep_fiches WHERE id=?", (mid,))
        H.journal("prep_fiche_supprimee", d["titre"][:120])
        flash("Fiche supprimée.", "success")
        return redirect(url_for("prep_mes_fiches"))

    @app.route("/preparation/mes-fiches/<int:mid>.pdf")
    @H.connexion_requise("preparation")
    def prep_ma_fiche_pdf(mid):
        d = ma_fiche(mid)
        return H.pdf_reponse(pdf_fiches([d]), nom_fichier(d, "pdf"))

    @app.route("/preparation/mes-fiches/<int:mid>.doc")
    @H.connexion_requise("preparation")
    def prep_ma_fiche_doc(mid):
        d = ma_fiche(mid)
        return reponse_doc(doc_word([d]), nom_fichier(d, "doc"))

    @app.route("/preparation/manquants")
    @H.connexion_requise("preparation")
    def prep_manquants():
        C = corpus()
        m = C.get("manquants") or {}
        concues = [f for f in C["fiches"] if f.get("statut") == "concue"]
        par = {}
        for f in concues:
            if not f["id"].startswith(("cm1i-", "l2c-", "cp22-", "lot3-")):      # inventaires (CM1, lot 2, CP, lot 3) : résumés dans leurs tableaux
                par.setdefault((f["cours"], f["matiere"]), []).append(f)
        guides_c = [x for x in C["guides"] if x.get("statut") == "concu"]
        return render_template("prep_manquants.html", avant=m.get("avant", []), apres=m.get("apres", []), par=par,
                               guides_c=guides_c, mention=m.get("mention", ""), inv=C.get("inventaire_cm1"),
                               nb_resumes=len(C.get("resumes") or []), lots=C.get("lots") or {}, doublons=C.get("doublons") or [])


    # ------------------------------------------------------------ v1.19 : résumés « l'essentiel à retenir »
    def resumes_filtres(col="", cours="", mat="", dom=""):
        rs = corpus().get("resumes") or []
        return [r for r in rs if (not col or COLLECTION_DE.get(r["collection"]) == col) and (not cours or r["cours"] == cours)
                and (not mat or r["matiere"] == mat) and (not dom or r["domaine"] == dom)]

    @app.route("/preparation/resumes")
    @H.connexion_requise("preparation")
    def prep_resumes():
        a = request.args
        col, cours, mat, dom = a.get("col") or "", a.get("cours") or "", a.get("matiere") or "", a.get("domaine") or ""
        tous = corpus().get("resumes") or []
        rs = resumes_filtres(col, cours, mat, dom)
        groupes = {}
        for r in rs:
            groupes.setdefault((r["collection"], r["cours"]), {}).setdefault(r["domaine"], []).append(r)
        ordre = sorted(groupes, key=lambda k: ([c for c, _l in COLLECTIONS_RES].index(COLLECTION_DE[k[0]]), COURS.index(k[1])))
        return render_template("prep_resumes.html", groupes=groupes, ordre=ordre, col=col, cours=cours, mat=mat, dom=dom, n=len(rs),
                               table=table_resumes(tous), COURS_RES=COURS_RES, MATS_RES=MATS_RES, COLLECTIONS=COLLECTIONS_RES, COURS=[c for c in COURS if any(r["cours"] == c for r in tous)],
                               MATS=[m for m in ORDRE_MAT if any(r["matiere"] == m for r in tous)],
                               DOMS=sorted({r["domaine"] for r in tous}))

    @app.route("/preparation/resumes/<rid>")
    @H.connexion_requise("preparation")
    def prep_resume(rid):
        r = next((x for x in corpus().get("resumes") or [] if x["id"] == rid), None)
        if not r:
            abort(404)
        meme = [x for x in resumes_filtres(COLLECTION_DE[r["collection"]], r["cours"], r["matiere"])]
        i = meme.index(r)
        return render_template("prep_resume.html", r=r, eleve=bool(request.args.get("eleve")),
                               prec=meme[i - 1] if i > 0 else None, suiv=meme[i + 1] if i + 1 < len(meme) else None)

    @app.route("/preparation/resumes/<rid>.pdf")
    @H.connexion_requise("preparation")
    def prep_resume_pdf(rid):
        r = next((x for x in corpus().get("resumes") or [] if x["id"] == rid), None)
        if not r:
            abort(404)
        eleve = bool(request.args.get("eleve"))
        nom = re.sub(r"[^A-Za-z0-9]+", "_", _sans_accent(("eleve_" if eleve else "resume_") + r["titre"]))[:70] + ".pdf"
        return H.pdf_reponse(pdf_resumes([r], eleve), nom)

    @app.route("/preparation/resumes.pdf")
    @H.connexion_requise("preparation")
    def prep_resumes_pdf():
        a = request.args
        rs = resumes_filtres(a.get("col") or "", a.get("cours") or "", a.get("matiere") or "", a.get("domaine") or "")
        if not rs:
            abort(404)
        eleve = bool(a.get("eleve"))
        lib = " ".join(x for x in [dict(COLLECTIONS_RES).get(a.get("col") or "", ""), a.get("cours") or "",
                                    nom_matiere(a["matiere"]) if a.get("matiere") else "", a.get("domaine") or ""] if x) or "tous"
        nom = re.sub(r"[^A-Za-z0-9]+", "_", _sans_accent(("eleve_" if eleve else "resumes_") + lib))[:70] + ".pdf"
        return H.pdf_reponse(pdf_resumes(rs, eleve, lib), nom)

    H.prep_cette_semaine = cette_semaine
    H.prep_pdf_fiches = pdf_fiches          # v1.21 : classeurs de fiches (m_evalprep)
    H.prep_doc_word = doc_word
    H.prep_classes = classes
    H.prep_plan_annuel = plan_annuel
    H.prep_ma_fiche = ma_fiche
