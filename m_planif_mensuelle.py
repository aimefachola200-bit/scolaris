# -*- coding: utf-8 -*-
"""
Planification mensuelle des activités pédagogiques du CE1 au CM2 (modèle « CE-CM — planification du mois »).

Document de l'enseignant, rangé dans son espace (« Mon espace », une entrée par classe de CE1, CE2, CM1, CM2) :

* en-tête : circonscription scolaire, mois, école, cours (préremplis) ;
* 5 semaines (dates « du … au … » proposées d'après le calendrier scolaire : les semaines sans classe sont sautées) ;
* FRANÇAIS : 12 activités (libellés de la 1re et de la 2e semaine d'unité) × 5 semaines, saisie « U… SA… S… Étape… »
  ou « Texte n° … » ; dictée ; MATHÉMATIQUES (D… SA… séances n° …) ; ÉDUCATION SOCIALE (langue, morale, civisme,
  histoire, géographie) ; EST ; ÉDUCATION ARTISTIQUE (chant, poésie, dessin, contes, couture) ; EPS ;
* pied : titulaire, directeur, lieu et date.

Persistance : barre Sauvegarder / Charger / Réinitialiser (mécanisme `data-doc`, clé `planifmens:<classe>:<année>:<mois>`,
droits de classe vérifiés comme pour les relevés). Sorties : PDF (paysage, modèle officiel), Excel (export) et import
d'un fichier exporté. Un enseignant n'accède qu'aux classes qui lui sont affectées.

Routes : planif_mensuelle /planification-mensuelle (GET) ; planif_mensuelle_pdf (POST) ; planif_mensuelle_xlsx (POST) ;
planif_mensuelle_import (POST, JSON des champs lus).
"""
import io
import re
from datetime import date, timedelta

from flask import abort, g, jsonify, render_template, request

NIVEAUX = ("CE1", "CE2", "CM1", "CM2")
MOIS = ["Septembre", "Octobre", "Novembre", "Décembre", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin"]
NUM_MOIS = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
SEMAINES = (1, 2, 3, 4, 5)

# (code, libellé de la 1re semaine d'unité, libellé de la 2e semaine d'unité, lecture ?)
FRANCAIS = [
    ("fr1", "1-C.O / Voc. thématique", "1-Communication orale", False),
    ("fr2", "2-Lecture", "2-Lecture", True),
    ("fr3", "3-Exp. écrite imprégnation", "3-Vocab. systématique", False),
    ("fr4", "4-Exp. écrite 1er jet", "4-Grammaire", False),
    ("fr5", "5-Vocab. fonctionnel", "5-Conjugaison", False),
    ("fr6", "6-Grammaire", "6-Orthographe (Dictée)", False),
    ("fr7", "7-Conjugaison", "7-Exp. écrite amélioration", False),
    ("fr8", "8-Orthographe", "8-Écriture", False),
    ("fr9", "9-Écriture", "9-Lecture", True),
    ("fr10", "10-Lecture", "10-Exp. écrite N°4 / Écriture", True),
    ("fr11", "11-Écriture", "11-Lecture renforcement", True),
    ("fr12", "12-Exp. écrite compte rendu", "", False),
]
# (champ de formation, [(code, libellé, modèle de saisie)])
AUTRES = [
    ("ÉDUCATION SOCIALE", [("langue", "LANGUE", "SA… Séq…"), ("morale", "MORALE", "SA… Séq…"), ("civisme", "CIVISME", "SA… Séq…"),
                           ("histoire", "HISTOIRE", "SA… Séq…"), ("geo", "GÉOGRAPHIE", "SA… Séq…")]),
    ("ÉDUCATION SCIENTIFIQUE ET TECHNOLOGIQUE", [("est", "EST", "SA… Séq…")]),
    ("ÉDUCATION ARTISTIQUE", [("chant", "CHANT", "SA… Titre…"), ("poesie", "POÉSIE", "SA… Séq…"), ("dessin", "DESSIN", "SA… Séq…"),
                              ("contes", "CONTES", "SA… Séq…"), ("couture", "COUTURE", "SA… Séq…")]),
    ("ÉDUCATION PHYSIQUE ET SPORTIVE", [("eps", "EPS", "SA… Séq…")]),
]
MATHS = [("ma_d", "D…"), ("ma_sa", "SA…"), ("ma_s", "Séances N°…")]
ENTETE = ("h_cs", "h_ecole", "h_cours", "h_mois")
PIED = ("p_titulaire", "p_directeur", "p_fait")


def codes_lignes():
    """Tous les codes de lignes de la grille (chaque champ de saisie = f"{code}_{semaine}")."""
    c = ["du", "au"] + [x[0] for x in FRANCAIS] + ["dictee"] + [x[0] for x in MATHS]
    for _chp, lignes in AUTRES:
        c += [x[0] for x in lignes]
    return c


def champs_grille():
    return [f"{c}_{w}" for c in codes_lignes() for w in SEMAINES]


def clef_doc(cid, annee, mois_num):
    return f"planifmens:{cid}:{annee}:{mois_num:02d}"


def mois_defaut(auj=None):
    auj = auj or date.today()
    return auj.month if auj.month in NUM_MOIS else 9


def annee_du_mois(annee_scolaire, mois_num):
    """« 2026-2027 », 9 -> 2026 ; « 2026-2027 », 2 -> 2027."""
    a = int(annee_scolaire[:4])
    return a if mois_num >= 9 else a + 1


def semaines_du_mois(annee_scolaire, mois_num, demi=None):
    """Jusqu'à 5 plages (lundi, vendredi) de semaines qui touchent le mois ; `demi(date)` -> nombre de demi-journées de classe
    (calendrier scolaire) : les semaines sans aucune classe (congés, fêtes) sont sautées."""
    an = annee_du_mois(annee_scolaire, mois_num)
    premier = date(an, mois_num, 1)
    d = premier - timedelta(days=premier.weekday())                    # lundi de la semaine du 1er
    out = []
    for _ in range(6):
        jours = [d + timedelta(days=i) for i in range(5) if (d + timedelta(days=i)).month == mois_num]
        if jours and (demi is None or any(demi(j) for j in jours)) and len(out) < 5:
            out.append((jours[0], jours[-1]))
        d += timedelta(days=7)
    return out


def valeurs_defaut(cs, ecole, cours, mois_txt, titulaire, directeur, semaines):
    v = {"h_cs": cs or "", "h_ecole": ecole or "", "h_cours": cours or "", "h_mois": mois_txt or "",
         "p_titulaire": titulaire or "", "p_directeur": directeur or "", "p_fait": ""}
    for i, (a, b) in enumerate(semaines, 1):
        v[f"du_{i}"], v[f"au_{i}"] = a.strftime("%d/%m/%Y"), b.strftime("%d/%m/%Y")
    return v


def lignes_export(v):
    """Lignes d'un tableau plat : [(code, rubrique, libellé, [S1..S5])] — sert à l'Excel et au PDF."""
    out = [("du", "", "Du", [v.get(f"du_{w}", "") for w in SEMAINES]), ("au", "", "Au", [v.get(f"au_{w}", "") for w in SEMAINES])]
    for code, la, lb, _lec in FRANCAIS:
        lib = la if not lb or la == lb else f"{la}  /  {lb}"
        out.append((code, "FRANÇAIS", lib, [v.get(f"{code}_{w}", "") for w in SEMAINES]))
    out.append(("dictee", "FRANÇAIS", "Dictée", [v.get(f"dictee_{w}", "") for w in SEMAINES]))
    for code, lib in MATHS:
        out.append((code, "MATHÉMATIQUES", lib, [v.get(f"{code}_{w}", "") for w in SEMAINES]))
    for chp, lignes in AUTRES:
        for code, lib, _m in lignes:
            out.append((code, chp, lib, [v.get(f"{code}_{w}", "") for w in SEMAINES]))
    return out


def nettoyer(brut):
    """Ne garde que les champs connus, en texte court (protection des saisies importées ou postées)."""
    ok = set(champs_grille()) | set(ENTETE) | set(PIED)
    return {k: (str(brut.get(k) or "").strip()[:80] if k in champs_grille() else str(brut.get(k) or "").strip()[:120])
            for k in ok if k in brut}


def lire_import(fichier_octets, openpyxl):
    """Relit un classeur produit par l'export : retourne {champ: valeur}. Lève ValueError si le fichier n'est pas reconnu."""
    try:
        wb = openpyxl.load_workbook(io.BytesIO(fichier_octets), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001
        raise ValueError("Fichier Excel illisible : enregistrez-le au format .xlsx.") from e
    ws = wb.worksheets[0]
    lignes = [list(r) for r in ws.iter_rows(values_only=True)]
    idx = next((i for i, r in enumerate(lignes[:20]) if r and str(r[0] or "").strip().lower() == "code"), None)
    if idx is None:
        raise ValueError("Fichier non reconnu : utilisez un export de cette planification (colonne « Code »).")
    codes = set(codes_lignes())
    out = {}
    for r in lignes[idx + 1:]:
        code = str(r[0] or "").strip()
        if code in codes:
            for w in SEMAINES:
                val = r[2 + w] if len(r) > 2 + w else None
                if val not in (None, ""):
                    out[f"{code}_{w}"] = str(val).strip()
        elif code in ENTETE + PIED and len(r) > 3 and r[3] not in (None, ""):
            out[code] = str(r[3]).strip()
    if not out:
        raise ValueError("Aucune donnée lue dans ce fichier.")
    return out


def enregistrer(app, H):
    q = H.q

    def classes_ce_cm():
        return [c for c in H.classes_autorisees() if c["niveau"] in NIVEAUX]

    def choix():
        """(classe, mois, année scolaire) demandés ; None si aucune classe de CE-CM accessible."""
        cls = classes_ce_cm()
        cid = request.values.get("classe", type=int)
        if cid is None and cls:
            cid = cls[0]["id"]
        cl = None
        if cid is not None:
            H.verifier_classe(cid)
            cl = H.classe_ou_404(cid)
            if cl["niveau"] not in NIVEAUX:
                abort(404)
        annee = (request.values.get("annee") or H.config.ANNEE_ACTIVE or "").strip()
        if not re.fullmatch(r"\d{4}-\d{4}", annee):
            annee = H.config.ANNEE_ACTIVE
        mois = request.values.get("mois", type=int)
        if mois not in NUM_MOIS:
            mois = mois_defaut()
        return cls, cl, mois, annee

    def calendrier_demi():
        import m_registre as R
        cal = R.Calendrier(H, H.eco())
        return cal.demi

    def defauts(cl, mois, annee):
        ident = H.identification(cl) if hasattr(H, "identification") else {}
        try:
            demi = calendrier_demi()
        except Exception:  # noqa: BLE001
            demi = None
        sem = semaines_du_mois(annee, mois, demi)
        return valeurs_defaut(ident.get("cs"), ident.get("ecole"), cl["nom"], MOIS[NUM_MOIS.index(mois)].upper(),
                              ident.get("titulaire") or (cl["titulaire_nom"] if "titulaire_nom" in cl.keys() else ""),
                              ident.get("directeur"), sem), ident

    @app.route("/planification-mensuelle")
    @H.connexion_requise()
    def planif_mensuelle():
        cls, cl, mois, annee = choix()
        if not cl:
            return render_template("planif_mensuelle.html", cls=cls, cl=None, MOIS=list(zip(NUM_MOIS, MOIS)), mois=mois,
                                   annee=annee), 200
        d, _ident = defauts(cl, mois, annee)
        enreg = H.doc_lire(f"e{H.eco()}:{clef_doc(cl['id'], annee, mois)}", None)
        v = dict(d)
        if enreg:
            v.update(nettoyer(enreg))
        return render_template("planif_mensuelle.html", cls=cls, cl=cl, mois=mois, annee=annee, v=v, FR=FRANCAIS, MATHS=MATHS,
                               AUTRES=AUTRES, SEM=SEMAINES, MOIS=list(zip(NUM_MOIS, MOIS)), cle=clef_doc(cl["id"], annee, mois),
                               defauts=d, enregistre=bool(enreg), mois_nom=MOIS[NUM_MOIS.index(mois)])

    def valeurs_postees():
        cls, cl, mois, annee = choix()
        if not cl:
            abort(404)
        d, _ = defauts(cl, mois, annee)
        v = dict(d)
        v.update(nettoyer(request.form))
        return cl, mois, annee, v

    @app.route("/planification-mensuelle/pdf", methods=["POST"])
    @H.connexion_requise()
    def planif_mensuelle_pdf():
        cl, mois, annee, v = valeurs_postees()
        octets = construire_pdf(v, cl, MOIS[NUM_MOIS.index(mois)], annee)
        H.journal("planif_mensuelle_pdf", f"{cl['nom']} {MOIS[NUM_MOIS.index(mois)]} {annee}")
        return H.pdf_reponse(octets, f"planification_{cl['nom']}_{MOIS[NUM_MOIS.index(mois)]}_{annee}.pdf".replace(" ", "_"))

    @app.route("/planification-mensuelle/xlsx", methods=["POST"])
    @H.connexion_requise()
    def planif_mensuelle_xlsx():
        cl, mois, annee, v = valeurs_postees()
        lignes = [[c, r, lib] + s for c, r, lib, s in lignes_export(v)]
        lignes += [[c, "EN-TÊTE" if c in ENTETE else "PIED", c, v.get(c, "")] for c in ENTETE + PIED]
        return H.xlsx.reponse_xlsx(f"planification_{cl['nom']}_{MOIS[NUM_MOIS.index(mois)]}_{annee}.xlsx".replace(" ", "_"),
                                   ["Code", "Champ de formation", "Libellé", "Semaine 1", "Semaine 2", "Semaine 3", "Semaine 4",
                                    "Semaine 5"], lignes, titre="Planification",
                                   titre_haut=[f"Planification mensuelle {cl['nom']} — {MOIS[NUM_MOIS.index(mois)]} {annee}"])

    @app.route("/planification-mensuelle/import", methods=["POST"])
    @H.connexion_requise()
    def planif_mensuelle_import():
        cls, cl, mois, annee = choix()
        if not cl:
            return jsonify({"ok": False, "erreur": "Aucune classe."}), 404
        f = request.files.get("fichier")
        if not f or not f.filename:
            return jsonify({"ok": False, "erreur": "Choisissez un fichier Excel (.xlsx)."}), 400
        try:
            donnees = lire_import(f.read(), H.xlsx._openpyxl())
        except (ValueError, H.xlsx.ExcelIndisponible) as e:
            return jsonify({"ok": False, "erreur": str(e)}), 400
        return jsonify({"ok": True, "valeurs": nettoyer(donnees)})

    # ------------------------------------------------------------ PDF
    def construire_pdf(v, cl, mois_nom, annee):
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        import pdfs
        bleu = colors.HexColor("#1f4e79")
        st = ParagraphStyle("c", fontName="Helvetica", fontSize=7, leading=8.4)
        st_b = ParagraphStyle("b", parent=st, fontName="Helvetica-Bold")
        st_h = ParagraphStyle("h", parent=st_b, textColor=colors.white, alignment=1)
        st_t = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=bleu)
        st_s = ParagraphStyle("s", fontName="Helvetica", fontSize=8.5, leading=11)

        def esc(x):
            return ("" if x is None else str(x)).replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br/>")

        def p(x, s=st):
            return Paragraph(esc(x), s)

        ent = [p("Champs de formation", st_h), p("1re semaine d'unité", st_h), p("2e semaine d'unité", st_h)]
        for w in SEMAINES:
            du, au = v.get(f"du_{w}", ""), v.get(f"au_{w}", "")
            ent.append(p(f"{w}{'re' if w == 1 else 'e'} semaine" + (f"\nDu {du}\nau {au}" if du or au else ""), st_h))
        data = [ent]
        spans, fonds = [], []
        r0 = 1
        for i, (code, la, lb, _lec) in enumerate(FRANCAIS):
            data.append([p("FRANÇAIS", st_b) if i == 0 else "", p(la), p(lb)] + [p(v.get(f"{code}_{w}", "")) for w in SEMAINES])
        data.append(["", p("Dictée", st_b), ""] + [p(v.get(f"dictee_{w}", "")) for w in SEMAINES])
        spans.append(("SPAN", (0, r0), (0, len(data) - 1)))
        spans.append(("SPAN", (1, len(data) - 1), (2, len(data) - 1)))
        r1 = len(data)
        for j, (code, lib) in enumerate(MATHS):
            data.append([p("MATHÉMATIQUES", st_b) if j == 0 else "", p(lib), ""] + [p(v.get(f"{code}_{w}", "")) for w in SEMAINES])
            spans.append(("SPAN", (1, len(data) - 1), (2, len(data) - 1)))
        spans.append(("SPAN", (0, r1), (0, len(data) - 1)))
        for chp, lignes in AUTRES:
            r2 = len(data)
            for j, (code, lib, _m) in enumerate(lignes):
                data.append([p(chp, st_b) if j == 0 else "", p(lib), ""] + [p(v.get(f"{code}_{w}", "")) for w in SEMAINES])
                spans.append(("SPAN", (1, len(data) - 1), (2, len(data) - 1)))
            spans.append(("SPAN", (0, r2), (0, len(data) - 1)))
        utile = landscape(A4)[0] - 20 * mm
        cw = [utile * 0.12, utile * 0.145, utile * 0.145] + [utile * 0.118] * 5
        t = Table(data, colWidths=cw, repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), bleu), ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#eef3f8")),
                               ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.4)] + spans))
        buf = io.BytesIO()

        def entete_page(c, doc):
            c.saveState()
            w, h = landscape(A4)
            pdfs.bloc_memp(c, 10 * mm, h - 7 * mm, 14 * mm)
            c.setFont("Helvetica", 7)
            c.setFillColor(colors.grey)
            c.drawRightString(w - 10 * mm, 6 * mm, f"Page {doc.page} · GESCOL")
            c.restoreState()

        corps = [Spacer(1, 9 * mm),
                 p(f"PLANIFICATION (CE-CM) DU MOIS DE {(v.get('h_mois') or mois_nom).upper()} — ANNÉE SCOLAIRE {annee}", st_t),
                 p(f"CIRCONSCRIPTION SCOLAIRE DE {(v.get('h_cs') or '').upper() or '………………………'}  |  "
                   f"ÉCOLE PRIMAIRE {v.get('h_ecole') or '…………………………'}  |  COURS : {v.get('h_cours') or cl['nom']}", st_s),
                 Spacer(1, 2 * mm), t, Spacer(1, 3 * mm),
                 p(f"Le titulaire : {v.get('p_titulaire') or '…………………'}          Le directeur : {v.get('p_directeur') or '…………………'}"
                   f"          Fait le : {v.get('p_fait') or '…………………'}", st_s)]
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=8 * mm,
                                bottomMargin=10 * mm, title=f"Planification {mois_nom} {cl['nom']}", author="GESCOL")
        doc.build(corps, onFirstPage=entete_page, onLaterPages=entete_page)
        return buf.getvalue()
