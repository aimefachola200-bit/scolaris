# -*- coding: utf-8 -*-
"""v1.21 — Préparation de classe : évaluations (banque d'épreuves APC + corrigés types + grilles), planification
journalière / hebdomadaire / mensuelle des classes et classeurs de fiches.

* /preparation/evaluations                        prep_evaluations          banque : cours × type × période × discipline
* /preparation/evaluations/organigramme           prep_organigramme         organigramme des épreuves (INFRE) par cours
* /preparation/evaluations/e/<cle>                prep_epreuve              sujet, corrigé type, grille ; actions
* /preparation/evaluations/e/<cle>/modifier       prep_epreuve_modifier     GET/POST : modification (enregistrée pour l'école)
* /preparation/evaluations/e/<cle>/regenerer      prep_epreuve_regenerer    POST : régénérée d'après la planification actuelle
* /preparation/evaluations/e/<cle>.pdf|.doc       prep_epreuve_pdf / _doc   ?partie=sujet|corrige|grille
* /preparation/evaluations/jeu.pdf                prep_jeu_pdf              toutes les épreuves d'un cours et d'une période
* /preparation/evaluations/creer                  prep_eval_creer           POST : crée l'évaluation (saisie des notes)
* /preparation/planification                      prep_planif               vue jour / semaine / mois d'une classe
* /preparation/planification/case                 prep_planif_case          POST : modifie une case (matière, fiche, note)
* /preparation/planification.pdf | .xlsx          prep_planif_pdf / _xlsx
* /preparation/classeur                           prep_classeur             PDF (sommaire + fiches), Word ou zip

Épreuves : générées par banque_epreuves d'après l'organigramme INFRE et la progression (planification annuelle de
l'école, sinon planification officielle) ; une épreuve modifiée ou régénérée est enregistrée pour l'école et l'année
(table prep_epreuves). Planification : emploi du temps du cours (tableau synoptique) × planification mensuelle de la
classe (modifiable dans le tableau synoptique) × progression ; chaque case peut être modifiée (table prep_planif).
Droits : comme la préparation de classe ; l'enseignant ne voit que les cours et classes qui lui sont affectés.
"""
import io
import json
import re
import zipfile
from datetime import date, datetime, timedelta

from flask import Response, abort, flash, g, redirect, render_template, request, url_for

import banque_epreuves as B
import m_preparation as MP

SCHEMA = """
CREATE TABLE IF NOT EXISTS prep_epreuves (
    id INTEGER PRIMARY KEY, ecole_id INTEGER NOT NULL, annee TEXT NOT NULL, cle TEXT NOT NULL,
    donnees TEXT NOT NULL, origine TEXT, maj TEXT, maj_par INTEGER,
    UNIQUE(ecole_id, annee, cle)
);
CREATE TABLE IF NOT EXISTS prep_planif (
    id INTEGER PRIMARY KEY, ecole_id INTEGER NOT NULL, annee TEXT NOT NULL, classe_id INTEGER NOT NULL,
    jour TEXT NOT NULL, creneau INTEGER NOT NULL, donnees TEXT NOT NULL, maj TEXT, maj_par INTEGER,
    UNIQUE(ecole_id, annee, classe_id, jour, creneau)
);
"""
COURS_NIV = {"CI": "ci", "CP": "cp", "CE1": "ce1", "CE2": "ce2", "CM1": "cm1", "CM2": "cm2"}
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi"]
JOURS_LIB = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
LIB_MATIERE = [(r"dict", "francais", "Dictée"), (r"fran", "francais", ""), (r"math", "maths", ""), (r"\bes\b|morale|civisme|histoire|g[ée]o", "es", ""),
               (r"\best\b", "est", ""), (r"\beps\b", "eps", ""), (r"\bea\b|po[ée]sie|chant|dessin|conte|couture|\btm\b", "ea", ""),
               (r"c[ée]r[ée]monial", "dg", "Cérémonial des couleurs")]
PLAN_COLS = {"francais": ["francais"], "maths": ["maths"], "es": ["es_morale", "es_civisme", "es_histoire", "es_geographie"], "est": ["est"],
             "eps": ["eps"], "ea": ["ea_chant", "ea_poesie", "ea_conte", "ea_dessin", "ea_couture"]}


def annee_civile(annee, mois):
    a = int(str(annee)[:4])
    return a if mois >= 9 else a + 1


def mois_jusqua(per):
    """Mois scolaires couverts par une période (progression « jusqu'à la date »)."""
    _c, _l, typ, m = B.PER[per]
    i = B.MOIS_SCO.index(m)
    if typ == "mensuelle":
        return [m]
    if typ == "trimestrielle":
        debut = {12: 0, 3: 4, 6: 7}[m]
        return B.MOIS_SCO[debut:i + 1]
    return B.MOIS_SCO[:i + 1]


def creneaux(texte):
    """« Français 45 min\\nES/Morale 30 min » -> [(libellé, matière, sous-matière, durée)]."""
    out = []
    for l in str(texte or "").split("\n"):
        l = l.strip()
        if not l or l.upper() in ("RÉCRÉATION", "INTERCLASSE"):
            continue
        m = re.search(r"(\d+)\s*min", l)
        lib = re.sub(r"\s*\d+\s*min.*$", "", l).strip()
        ls = MP._sans_accent(lib)
        mat, sm = next(((mm, s) for rx, mm, s in LIB_MATIERE if re.search(rx, ls)), ("dg", ""))
        if mat == "ea" and not sm:
            sm = lib.replace("EA/", "").replace("EA ", "").strip()
        if mat == "es" and "/" in lib:
            sm = lib.split("/", 1)[1].strip()
        out.append({"libelle": lib, "matiere": mat, "sous_matiere": sm, "duree": f"{m.group(1)} min" if m else ""})
    return out


def enregistrer(app, H):
    q, ex, config = H.q, H.ex, H.config
    H.schema(SCHEMA)

    # ------------------------------------------------------------------ périmètre
    def mes_classes():
        return [c for c in H.prep_classes() if c["niveau"] in COURS_NIV]

    def mes_cours():
        if g.user["role"] == "enseignant":
            return [c for c in B.COURS if any(cl["niveau"] == c for cl in mes_classes())]
        return list(B.COURS)

    def exiger_cours(cours):
        if cours not in mes_cours():
            abort(403 if cours in B.COURS else 404)

    def peut_modifier():
        return g.user["role"] in ("enseignant", "directeur", "admin", "fondateur")

    # ------------------------------------------------------------------ progression (planification annuelle)
    def progression(cours, per):
        lignes_plan = {}
        r = q("SELECT contenu FROM synoptique_planification WHERE ecole_id=? AND niveau=?", (H.eco(), COURS_NIV[cours]), un=True)
        import m_synoptique as S
        lignes = json.loads(r["contenu"]) if r else S.planification_defaut(COURS_NIV[cours])
        for l in lignes:
            m = next((k for k, v in B.MOIS_LIB.items() if MP._sans_accent(v) == MP._sans_accent(l.get("mois", ""))), None)
            if m:
                lignes_plan[m] = l
        mois = mois_jusqua(per)
        out = {}
        C = MP.corpus()
        for mat, cols in PLAN_COLS.items():
            textes = [str(lignes_plan.get(m, {}).get(c) or "") for m in mois for c in cols]
            texte = " ; ".join(t for t in textes if t.strip())
            refs = MP.references(texte)
            fiches = MP.correspondances(cours, mat, refs) if (refs["sa"] or refs["u"] or refs["d"]) else []
            par_sa = {}
            for f in fiches:
                if f.get("sa"):
                    par_sa.setdefault(f["sa"], []).append(f)
            titres = {}
            for p in C["programmes"]:
                if p["cours"] == cours and p["matiere"] == mat and p.get("type") == "sa" and p.get("num"):
                    titres.setdefault(p["num"], p["titre"])
            for n, fs in par_sa.items():
                titres.setdefault(n, fs[0].get("intitule") or fs[0].get("titre"))
            sas = [(n, titres.get(n, f"SA {n}")) for n in sorted(set(refs["sa"]) | set(par_sa))]
            out[mat] = {"refs": texte[:300], "sas": sas, "fiches": par_sa}
        return out

    # ------------------------------------------------------------------ épreuves (générées / enregistrées)
    def cle_valide(cle):
        m = re.fullmatch(r"(CI|CP|CE1|CE2|CM1|CM2)-([A-Z]\d|FA)-(comp|expr|math|est|es|ea|eps|dictee)", cle or "")
        if not m or m.group(2) not in B.PER:
            abort(404)
        cours, per, code = m.groups()
        if per not in [p[0] for p in B.periodes_du_cours(cours)] or code not in [e["code"] for e in B.organigramme(cours, B.PER[per][2])]:
            abort(404)
        return cours, per, code

    def epreuve(cle):
        cours, per, code = cle_valide(cle)
        r = q("SELECT * FROM prep_epreuves WHERE ecole_id=? AND annee=? AND cle=?", (H.eco(), config.ANNEE_ACTIVE, cle), un=True)
        if r:
            d = json.loads(r["donnees"])
            d["_origine"], d["_maj"] = r["origine"], r["maj"]
            return d
        e = next(x for x in B.organigramme(cours, B.PER[per][2]) if x["code"] == code)
        d = B.generer(cours, per, e, progression(cours, per))
        d["_origine"] = "banque"
        return d

    def sauver(cle, d, origine):
        d = {k: v for k, v in d.items() if not k.startswith("_")}
        ex("INSERT INTO prep_epreuves (ecole_id, annee, cle, donnees, origine, maj, maj_par) VALUES (?,?,?,?,?,?,?) "
           "ON CONFLICT(ecole_id, annee, cle) DO UPDATE SET donnees=excluded.donnees, origine=excluded.origine, maj=excluded.maj, maj_par=excluded.maj_par",
           (H.eco(), config.ANNEE_ACTIVE, cle, json.dumps(d, ensure_ascii=False), origine, H.maintenant(), g.user["id"]))

    # ------------------------------------------------------------------ PDF / Word des épreuves
    def pdf_epreuves(liste, partie):
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        W, Hh = A4
        marge = 15 * mm
        utile = W - 2 * marge
        t = MP.txt_pdf
        st = ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=13.5, spaceAfter=3)
        stb = ParagraphStyle("b", parent=st, fontName="Helvetica-Bold")
        sti = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, leading=16, alignment=1, textColor=pdfs.BLEU, spaceAfter=4)
        stc = ParagraphStyle("c", parent=st, fontName="Helvetica-Oblique", leftIndent=8, rightIndent=8)
        stm = ParagraphStyle("m", parent=st, fontSize=8, fontName="Helvetica-Oblique", textColor=colors.HexColor("#B54708"))
        sts = ParagraphStyle("s", parent=st, fontSize=7.5, textColor=colors.grey)
        std = ParagraphStyle("d", parent=st, fontSize=8.5, leading=10.5)
        h = []
        for n, d in enumerate(liste):
            if n:
                h.append(PageBreak())
            titre = {"sujet": "", "corrige": "CORRIGÉ TYPE — ", "grille": "GRILLE DE CORRECTION — "}[partie]
            h.append(Paragraph(f"{titre}ÉPREUVE DE {t(d['discipline'].upper())}", sti))
            ent = Table([[Paragraph(f"<b>COURS :</b> {d['cours']}", st), Paragraph(f"<b>PÉRIODE :</b> {t(d['periode_lib'])}", st),
                          Paragraph(f"<b>DURÉE :</b> {t(d['duree'])}", st), Paragraph(f"<b>Barème :</b> {d.get('bareme', 20)} points", st)]],
                        colWidths=[utile * 0.16, utile * 0.44, utile * 0.2, utile * 0.2])
            ent.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, pdfs.BLEU), ("BACKGROUND", (0, 0), (-1, -1), pdfs.GRIS)]))
            h += [ent, Spacer(1, 6)]
            if partie == "sujet":
                h.append(Paragraph("<b>Nom et prénoms :</b> ……………………………………………………   <b>Classe :</b> ………………", st))
                h.append(Spacer(1, 4))
                if d.get("contexte"):
                    h.append(Paragraph(t(d["contexte"]), stc))
                if d.get("support") and d["code"] != "dictee":
                    h += [Spacer(1, 3), Paragraph(f"<b>{'Support' if d['code'] in ('ea', 'eps') else 'Texte'} :</b> {t(d.get('support_titre') or '')}", stb),
                          Paragraph(t(d["support"]), st)]
                h += [Spacer(1, 3), Paragraph(f"<b>Tâche :</b> {t(d.get('tache') or '')}", st), Paragraph("<b>Consigne :</b>", stb)]
                for it in d.get("consignes") or []:
                    if it["titre"] not in ("Consigne", "Présentation"):
                        h.append(Paragraph(f"<b>{t(it['titre'])}</b>", st))
                    if it["titre"] == "Présentation":
                        continue
                    for i, x in enumerate(it["questions"]):
                        lettre = "" if it["titre"] == "Consigne" else f"{'abcdefgh'[i]}- "
                        h.append(Paragraph(f"{lettre}{t(x['q'])}" + (f" <font size=8 color='#667085'>({B.nb(x['pts'])} pt{'s' if (x['pts'] or 0) > 1 else ''})</font>" if x.get("pts") else ""), ParagraphStyle("q", parent=st, leftIndent=10)))
            elif partie == "corrige":
                if d["code"] == "dictee":
                    h += [Paragraph(f"<b>Texte de la dictée :</b> {t(d.get('support_titre'))}", stb), Paragraph(t(d["support"]), st)]
                for it in d.get("consignes") or []:
                    if not any(x.get("r") for x in it["questions"]):
                        continue
                    h.append(Paragraph(f"<b>{t(it['titre'])}</b>", st))
                    data = [[Paragraph("<b>Question</b>", std), Paragraph("<b>Réponse attendue</b>", std), Paragraph("<b>Pts</b>", std)]]
                    for x in it["questions"]:
                        data.append([Paragraph(t(x["q"]), std), Paragraph(t(x.get("r") or ""), std), Paragraph(B.nb(x["pts"]) if x.get("pts") else "", std)])
                    tb = Table(data, colWidths=[utile * 0.42, utile * 0.5, utile * 0.08], repeatRows=1)
                    tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")),
                                            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                    h += [tb, Spacer(1, 4)]
                if d.get("corrige_note"):
                    h.append(Paragraph(t(d["corrige_note"]), st))
                h.append(Paragraph("<i>RP : réponse personnelle, à accepter si elle respecte l'indicateur.</i>", sts))
            if partie in ("corrige", "grille"):
                h += [Spacer(1, 4), Paragraph("<b>Grille de correction (critères, indicateurs, barème)</b>", stb)]
                data = [[Paragraph("<b>Critère</b>", std), Paragraph("<b>Indicateurs</b>", std), Paragraph("<b>Points</b>", std)]]
                for gr in d.get("grille") or []:
                    data.append([Paragraph(t(gr["critere"]), std), Paragraph("<br/>".join("• " + t(i) for i in gr.get("indicateurs") or []), std),
                                 Paragraph(B.nb(gr["points"]), std)])
                data.append([Paragraph("<b>Total</b>", std), "", Paragraph(f"<b>{B.nb(sum(gr['points'] for gr in d.get('grille') or []))}</b>", std)])
                tb = Table(data, colWidths=[utile * 0.3, utile * 0.58, utile * 0.12], repeatRows=1)
                tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")),
                                        ("VALIGN", (0, 0), (-1, -1), "TOP")]))
                h.append(tb)
            h += [Spacer(1, 6), Paragraph(t(d.get("mention") or B.MENTION), stm), Paragraph(t(d.get("source") or ""), sts)]

        def deco(c, doc):
            pdfs._entete_primaire(c, W, Hh, marge, None, None)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(colors.grey)
            c.drawString(marge, 7 * mm, f"SCOLARIS · {config.ECOLE.get('nom', '')} · {config.ANNEE_ACTIVE}")
            c.drawRightString(W - marge, 7 * mm, f"Page {doc.page}")
        buf = io.BytesIO()
        SimpleDocTemplate(buf, pagesize=A4, leftMargin=marge, rightMargin=marge, topMargin=marge + 30 * mm, bottomMargin=13 * mm,
                          title="Épreuves", author="SCOLARIS").build(h, onFirstPage=deco, onLaterPages=deco, canvasmaker=pdfs.GCanvas)
        return buf.getvalue()

    def doc_epreuves(liste, partie):
        import html as _h
        e = _h.escape
        parts = []
        for d in liste:
            s = [f"<h1>{'CORRIGÉ TYPE — ' if partie == 'corrige' else 'GRILLE — ' if partie == 'grille' else ''}ÉPREUVE DE {e(d['discipline'].upper())}</h1>",
                 f"<p><b>COURS :</b> {e(d['cours'])} &nbsp; <b>PÉRIODE :</b> {e(d['periode_lib'])} &nbsp; <b>DURÉE :</b> {e(d['duree'])} &nbsp; <b>Barème :</b> {d.get('bareme', 20)} points</p>"]
            if partie == "sujet":
                s.append(f"<p><i>{e(d.get('contexte') or '')}</i></p>")
                if d.get("support") and d["code"] != "dictee":
                    s.append(f"<p><b>Texte : {e(d.get('support_titre') or '')}</b><br>{e(d['support'])}</p>")
                s.append(f"<p><b>Tâche :</b> {e(d.get('tache') or '')}</p><p><b>Consigne :</b></p>")
                for it in d.get("consignes") or []:
                    if it["titre"] == "Présentation":
                        continue
                    s.append(f"<p><b>{e(it['titre'])}</b></p><ul>" + "".join(f"<li>{e(x['q'])}</li>" for x in it["questions"]) + "</ul>")
            if partie == "corrige":
                for it in d.get("consignes") or []:
                    s.append(f"<p><b>{e(it['titre'])}</b></p><table><tr><th>Question</th><th>Réponse attendue</th><th>Pts</th></tr>" +
                             "".join(f"<tr><td>{e(x['q'])}</td><td>{e(x.get('r') or '')}</td><td>{B.nb(x['pts']) if x.get('pts') else ''}</td></tr>" for x in it["questions"]) + "</table>")
            if partie in ("corrige", "grille"):
                s.append("<p><b>Grille de correction</b></p><table><tr><th>Critère</th><th>Indicateurs</th><th>Points</th></tr>" +
                         "".join(f"<tr><td>{e(gr['critere'])}</td><td>{'<br>'.join(e(i) for i in gr.get('indicateurs') or [])}</td><td>{B.nb(gr['points'])}</td></tr>" for gr in d.get("grille") or []) + "</table>")
            s.append(f"<p><i>{e(d.get('mention') or B.MENTION)}</i><br><small>{e(d.get('source') or '')}</small></p>")
            parts.append("".join(s))
        corps = "<br style='page-break-before:always'>".join(parts)
        return ("<html><head><meta charset='utf-8'><style>body{font-family:Calibri,Arial;font-size:11pt}table{border-collapse:collapse;width:100%}"
                "td,th{border:1px solid #666;padding:4px;vertical-align:top}th{background:#E4ECF5}h1{text-align:center;color:#1F4E79;font-size:15pt}</style></head>"
                f"<body>{corps}</body></html>")

    def nom(base, ext):
        return re.sub(r"[^A-Za-z0-9]+", "_", MP._sans_accent(base))[:80].strip("_") + "." + ext

    # ------------------------------------------------------------------ pages : évaluations
    @app.route("/preparation/evaluations")
    @H.connexion_requise("preparation")
    def prep_evaluations():
        a = request.args
        cours_dispo = mes_cours()
        cours = a.get("cours") if a.get("cours") in cours_dispo else (cours_dispo[0] if cours_dispo else "")
        typ = a.get("type") if a.get("type") in B.TYPES else ""
        per = a.get("periode") or ""
        lignes = []
        if cours:
            for p in B.periodes_du_cours(cours):
                if (typ and p[2] != typ) or (per and p[0] != per):
                    continue
                eps = B.organigramme(cours, p[2])
                lignes.append({"periode": p, "epreuves": [{"cle": f"{cours}-{p[0]}-{e['code']}", **e} for e in eps]})
        modifiees = {r["cle"]: r["origine"] for r in q("SELECT cle, origine FROM prep_epreuves WHERE ecole_id=? AND annee=?", (H.eco(), config.ANNEE_ACTIVE))}
        classes = [c for c in mes_classes() if c["niveau"] == cours]
        nb_tot = sum(len(B.organigramme(c, p[2])) for c in B.COURS for p in B.periodes_du_cours(c))
        return render_template("prep_evaluations.html", cours=cours, typ=typ, per=per, lignes=lignes, COURS=cours_dispo, TYPES=B.TYPES,
                               PERIODES=B.periodes_du_cours(cours) if cours else [], modifiees=modifiees, classes=classes, nb_tot=nb_tot,
                               MENTION=B.MENTION)

    @app.route("/preparation/evaluations/organigramme")
    @H.connexion_requise("preparation")
    def prep_organigramme():
        return render_template("prep_organigramme.html", org=B.organigramme_tableau(), TYPES=B.TYPES, PERIODES=B.PERIODES)

    @app.route("/preparation/evaluations/e/<cle>")
    @H.connexion_requise("preparation")
    def prep_epreuve(cle):
        cours, per, code = cle_valide(cle)
        exiger_cours(cours)
        d = epreuve(cle)
        classes = [c for c in mes_classes() if c["niveau"] == cours]
        return render_template("prep_epreuve.html", d=d, cle=cle, classes=classes, peut_mod=peut_modifier(), fnb=B.nb)

    @app.route("/preparation/evaluations/e/<cle>/modifier", methods=["GET", "POST"])
    @H.connexion_requise("preparation")
    def prep_epreuve_modifier(cle):
        cours, per, code = cle_valide(cle)
        exiger_cours(cours)
        if not peut_modifier():
            abort(403)
        d = epreuve(cle)
        if request.method == "POST":
            f = request.form
            for k in ("contexte", "tache", "support_titre", "support", "duree", "corrige_note"):
                if k in f:
                    d[k] = (f.get(k) or "").strip()[:6000]
            for i, it in enumerate(d.get("consignes") or []):
                for j, x in enumerate(it["questions"]):
                    if f"q_{i}_{j}" in f:
                        x["q"] = (f.get(f"q_{i}_{j}") or "").strip()[:1500]
                        x["r"] = (f.get(f"r_{i}_{j}") or "").strip()[:2500]
                        p = (f.get(f"p_{i}_{j}") or "").replace(",", ".").strip()
                        try:
                            x["pts"] = float(p) if p else None
                            if x["pts"] is not None and (x["pts"] < 0 or x["pts"] > 20):
                                raise ValueError
                        except ValueError:
                            flash("Points invalides : un nombre entre 0 et 20 est attendu.", "danger")
                            return render_template("prep_epreuve_form.html", d=d, cle=cle), 400
            for i, gr in enumerate(d.get("grille") or []):
                if f"gc_{i}" in f:
                    gr["critere"] = (f.get(f"gc_{i}") or "").strip()[:300]
                    gr["indicateurs"] = [x.strip() for x in (f.get(f"gi_{i}") or "").split("\n") if x.strip()][:12]
                    try:
                        gr["points"] = float((f.get(f"gp_{i}") or "0").replace(",", "."))
                    except ValueError:
                        gr["points"] = 0
            sauver(cle, d, "modifiee")
            H.journal("prep_epreuve_modifiee", cle)
            flash("Épreuve enregistrée pour l'école (elle remplace la version de la banque).", "success")
            return redirect(url_for("prep_epreuve", cle=cle))
        return render_template("prep_epreuve_form.html", d=d, cle=cle)

    @app.route("/preparation/evaluations/e/<cle>/regenerer", methods=["POST"])
    @H.connexion_requise("preparation")
    def prep_epreuve_regenerer(cle):
        cours, per, code = cle_valide(cle)
        exiger_cours(cours)
        if not peut_modifier():
            abort(403)
        e = next(x for x in B.organigramme(cours, B.PER[per][2]) if x["code"] == code)
        if request.form.get("banque"):
            ex("DELETE FROM prep_epreuves WHERE ecole_id=? AND annee=? AND cle=?", (H.eco(), config.ANNEE_ACTIVE, cle))
            flash("Version de la banque rétablie.", "success")
        else:
            d = B.generer(cours, per, e, progression(cours, per))
            sauver(cle, d, "regeneree")
            flash("Épreuve régénérée d'après la planification actuelle de l'école.", "success")
        H.journal("prep_epreuve_regeneree", cle)
        return redirect(url_for("prep_epreuve", cle=cle))

    def partie():
        p = request.args.get("partie") or "sujet"
        if p not in ("sujet", "corrige", "grille"):
            abort(404)
        return p

    @app.route("/preparation/evaluations/e/<cle>.pdf")
    @H.connexion_requise("preparation")
    def prep_epreuve_pdf(cle):
        cours, per, code = cle_valide(cle)
        exiger_cours(cours)
        p = partie()
        d = epreuve(cle)
        return H.pdf_reponse(pdf_epreuves([d], p), nom(f"epreuve_{cle}_{p}", "pdf"))

    @app.route("/preparation/evaluations/e/<cle>.doc")
    @H.connexion_requise("preparation")
    def prep_epreuve_doc(cle):
        cours, per, code = cle_valide(cle)
        exiger_cours(cours)
        p = partie()
        return Response("﻿" + doc_epreuves([epreuve(cle)], p), mimetype="application/msword",
                        headers={"Content-Disposition": f"attachment; filename={nom(f'epreuve_{cle}_{p}', 'doc')}"})

    @app.route("/preparation/evaluations/jeu.pdf")
    @H.connexion_requise("preparation")
    def prep_jeu_pdf():
        cours, per = request.args.get("cours") or "", request.args.get("periode") or ""
        exiger_cours(cours)
        if per not in [p[0] for p in B.periodes_du_cours(cours)]:
            abort(404)
        p = partie()
        liste = [epreuve(f"{cours}-{per}-{e['code']}") for e in B.organigramme(cours, B.PER[per][2])]
        return H.pdf_reponse(pdf_epreuves(liste, p), nom(f"epreuves_{cours}_{per}_{p}", "pdf"))

    @app.route("/preparation/evaluations/creer", methods=["POST"])
    @H.connexion_requise("preparation")
    def prep_eval_creer():
        import evaluations_core as EC
        cid = request.form.get("classe", type=int)
        per = request.form.get("periode") or ""
        cl = next((c for c in mes_classes() if c["id"] == cid), None)
        if not cl or per not in B.PER:
            abort(404)
        cours = cl["niveau"]
        if per not in [p[0] for p in B.periodes_du_cours(cours)]:
            abort(404)
        if not peut_modifier():
            abort(403)
        typ = B.TYPE_EVAL[B.PER[per][2]]
        existantes = EC.evaluations_classe(cid)
        nums = [x["numero"] for x in existantes if x["type"] == typ]
        numero = (max(nums) + 1) if nums else 1
        lib = EC.libelle(typ, numero)
        codes = {e["matiere_code"] for e in B.organigramme(cours, B.PER[per][2])}
        if "ART.P" in codes:
            codes.add("ART.V")
        from calcul import cycle_du_niveau
        cyc = cycle_du_niveau(cours)
        mats = [m["id"] for m in EC.matieres_cycle(cyc) if m["code"] in codes]
        m = B.PER[per][3]
        jour = date(annee_civile(config.ANNEE_ACTIVE, m), m, 20 if m != 6 else 10).isoformat()
        nid = ex("INSERT INTO evaluations (classe_id, annee, type, numero, libelle, date, matieres, seuil, cree_le) VALUES (?,?,?,?,?,?,?,?,?)",
                 (cid, config.ANNEE_ACTIVE, typ, numero, lib, jour, json.dumps(mats), None, H.maintenant()))
        H.journal("evaluation_creee", f"{cl['nom']} {lib} ({B.PER[per][1]})")
        flash(f"Évaluation « {lib} » créée pour {cl['nom']} ({B.PER[per][1]}) : vous pouvez saisir les notes.", "success")
        return redirect(url_for("eval_saisie", ev_id=nid))

    # ------------------------------------------------------------------ planification journalière / hebdomadaire / mensuelle
    def edt_cours(niveau):
        import m_synoptique as S
        r = q("SELECT contenu FROM synoptique_edt WHERE ecole_id=? AND niveau=?", (H.eco(), niveau), un=True)
        return json.loads(r["contenu"]) if r else S.edt_defaut(niveau)

    def lundi_de(d):
        return d - timedelta(days=d.weekday())

    def journee(cl, jour, suggestions=None):
        """Créneaux d'une journée : emploi du temps × planification × fiches ; cases modifiées prises en compte."""
        if jour.weekday() > 4:
            return []
        niv = COURS_NIV[cl["niveau"]]
        edt = edt_cours(niv)
        if suggestions is None:
            suggestions = semaine_fiches(cl, jour)
        rang = {}
        out = []
        k = 0
        modifs = {r["creneau"]: json.loads(r["donnees"]) for r in q("SELECT creneau, donnees FROM prep_planif WHERE ecole_id=? AND annee=? AND classe_id=? AND jour=?",
                                                                     (H.eco(), config.ANNEE_ACTIVE, cl["id"], jour.isoformat()))}
        for ligne in edt.get("lignes") or []:
            for c in creneaux(ligne.get(JOURS[jour.weekday()])):
                c = dict(c, horaire=ligne.get("horaire", ""), creneau=k)
                liste = suggestions.get(c["matiere"]) or []
                if liste:
                    i = rang.get(c["matiere"], 0)
                    f = liste[i % len(liste)]
                    rang[c["matiere"]] = i + 1
                    c.update(fiche_id=f["id"], fiche_titre=f["titre"])
                if k in modifs:
                    c.update(modifs[k])
                    c["modifie"] = True
                out.append(c)
                k += 1
        return out

    def semaine_fiches(cl, jour):
        s = H.prep_cette_semaine(cl, jour)
        C = MP.corpus()
        out = {}
        for m in s["matieres"]:
            ids = m.get("ids") or [f["id"] for f in m["fiches"]]
            out[m["matiere"]] = [C["fiche_par_id"][i] for i in ids if i in C["fiche_par_id"]]
        # répartition sur la semaine : chaque jour reprend la suite (rang = nombre de créneaux déjà passés dans la semaine)
        return out

    def semaine(cl, jour):
        l = lundi_de(jour)
        sug = semaine_fiches(cl, l)
        jours = []
        decal = {}
        for i in range(5):
            dj = l + timedelta(days=i)
            js = journee(cl, dj, {m: (fs[decal.get(m, 0):] + fs[:decal.get(m, 0)]) for m, fs in sug.items()})
            for c in js:
                if not c.get("modifie") and c["matiere"] in sug:
                    decal[c["matiere"]] = decal.get(c["matiere"], 0) + 1
            jours.append((dj, js))
        return jours

    def mois_classe(cl, an, mo):
        try:
            liste = H.planification_mensuelle(H.eco(), config.ANNEE_ACTIVE, cl["id"])
        except Exception:  # noqa: BLE001
            liste = []
        pm = next((p for p in liste if p.get("mois") == f"{an}-{mo:02d}"), None)
        lignes = H.prep_plan_annuel(COURS_NIV[cl["niveau"]], MP.MOIS_FR[mo - 1])
        d1 = date(an, mo, 1)
        sem = []
        d = lundi_de(d1)
        while d.month == mo or d < d1:
            if d.month == mo or (d + timedelta(days=4)).month == mo:
                sem.append(d)
            d += timedelta(days=7)
            if len(sem) > 5:
                break
        return pm, lignes, sem

    def classe_choisie():
        cls = mes_classes()
        cid = request.values.get("classe", type=int)
        cl = next((c for c in cls if c["id"] == cid), None) or (cls[0] if cls else None)
        return cls, cl

    def date_choisie():
        try:
            return datetime.strptime(request.values.get("date") or "", "%Y-%m-%d").date()
        except ValueError:
            return date.today()

    @app.route("/preparation/planification")
    @H.connexion_requise("preparation")
    def prep_planif():
        cls, cl = classe_choisie()
        vue = request.args.get("vue") if request.args.get("vue") in ("jour", "semaine", "mois") else "semaine"
        d = date_choisie()
        ctx = {"classes": cls, "cl": cl, "vue": vue, "d": d, "JOURS_LIB": JOURS_LIB, "timedelta": timedelta}
        if cl:
            if vue == "jour":
                ctx["jour"] = journee(cl, d)
                C = MP.corpus()
                fj = {}
                for c in ctx["jour"]:
                    f = C["fiche_par_id"].get(c.get("fiche_id") or "")
                    if f:
                        fj.setdefault(c["matiere"], []).append(f)
                ctx["resumes_jour"] = MP.resumes_semaine(cl["niveau"], fj)   # v1.25 : résumés des séances du jour
            elif vue == "semaine":
                ctx["semaine"] = semaine(cl, d)
                ctx["resumes_sem"] = MP.resumes_semaine(cl["niveau"], semaine_fiches(cl, lundi_de(d)))
            else:
                ctx["pm"], ctx["ligne"], ctx["semaines"] = mois_classe(cl, d.year, d.month)
                ctx["cols"] = [(k, v) for k, v in [("francais", "Français"), ("maths", "Mathématiques"), ("es_morale", "ES — morale"), ("es_civisme", "ES — civisme"),
                                                   ("es_histoire", "ES — histoire"), ("es_geographie", "ES — géographie"), ("est", "EST"), ("eps", "EPS"),
                                                   ("ea_chant", "EA — chant"), ("ea_poesie", "EA — poésie"), ("ea_conte", "EA — conte"), ("ea_dessin", "EA — dessin"), ("ea_couture", "EA — couture")]]
                ctx["semaine_resume"] = [(s, semaine_fiches(cl, s)) for s in ctx["semaines"]]
                ctx["resumes_mois"] = MP.resumes_mois(cl["niveau"], MP.MOIS_FR[d.month - 1])   # v1.25 : progression du mois
        return render_template("prep_planif.html", **ctx)

    @app.route("/preparation/planification/case", methods=["POST"])
    @H.connexion_requise("preparation")
    def prep_planif_case():
        cls, cl = classe_choisie()
        if not cl or not peut_modifier():
            abort(403)
        d = date_choisie()
        k = request.form.get("creneau", type=int)
        if k is None or k < 0 or k > 40:
            abort(400)
        if request.form.get("retablir"):
            ex("DELETE FROM prep_planif WHERE ecole_id=? AND annee=? AND classe_id=? AND jour=? AND creneau=?", (H.eco(), config.ANNEE_ACTIVE, cl["id"], d.isoformat(), k))
        else:
            fid = (request.form.get("fiche_id") or "").strip()
            C = MP.corpus()
            v = {"matiere": request.form.get("matiere") if request.form.get("matiere") in C["matieres"] else "dg",
                 "sous_matiere": (request.form.get("sous_matiere") or "").strip()[:120], "note": (request.form.get("note") or "").strip()[:500]}
            if fid in C["fiche_par_id"]:
                v.update(fiche_id=fid, fiche_titre=C["fiche_par_id"][fid]["titre"])
            elif fid.startswith("mes-") and fid[4:].isdigit():
                mf = H.prep_ma_fiche(int(fid[4:]))
                v.update(fiche_id=fid, fiche_titre=mf["titre"])
            else:
                v.update(fiche_id="", fiche_titre=(request.form.get("fiche_titre") or "").strip()[:200])
            ex("INSERT INTO prep_planif (ecole_id, annee, classe_id, jour, creneau, donnees, maj, maj_par) VALUES (?,?,?,?,?,?,?,?) "
               "ON CONFLICT(ecole_id, annee, classe_id, jour, creneau) DO UPDATE SET donnees=excluded.donnees, maj=excluded.maj, maj_par=excluded.maj_par",
               (H.eco(), config.ANNEE_ACTIVE, cl["id"], d.isoformat(), k, json.dumps(v, ensure_ascii=False), H.maintenant(), g.user["id"]))
        flash("Planification mise à jour.", "success")
        return redirect(url_for("prep_planif", classe=cl["id"], vue=request.form.get("vue") or "jour", date=d.isoformat()))

    def lignes_export(cl, vue, d):
        rows = []
        if vue == "jour":
            for c in journee(cl, d):
                rows.append([d.strftime("%d/%m/%Y"), c["horaire"], ("Vie de la classe" if c["matiere"] == "dg" else MP.nom_matiere(c["matiere"])), c.get("sous_matiere", "") or c.get("libelle", ""), c.get("duree", ""), c.get("fiche_titre", ""), c.get("note", "")])
        elif vue == "semaine":
            for dj, js in semaine(cl, d):
                for c in js:
                    rows.append([f"{JOURS_LIB[dj.weekday()]} {dj.strftime('%d/%m')}", c["horaire"], ("Vie de la classe" if c["matiere"] == "dg" else MP.nom_matiere(c["matiere"])), c.get("sous_matiere", "") or c.get("libelle", ""), c.get("duree", ""), c.get("fiche_titre", ""), c.get("note", "")])
        else:
            pm, ligne, sems = mois_classe(cl, d.year, d.month)
            for s in sems:
                for m, fs in semaine_fiches(cl, s).items():
                    rows.append([f"Semaine du {s.strftime('%d/%m')}", "", MP.nom_matiere(m), "", "", " ; ".join(f["titre"] for f in fs[:6]), ""])
        return rows

    ENT = ["Jour / semaine", "Horaire", "Matière", "Sous-matière / activité", "Durée", "Fiche à utiliser", "Note"]

    @app.route("/preparation/planification.xlsx")
    @H.connexion_requise("preparation")
    def prep_planif_xlsx():
        cls, cl = classe_choisie()
        if not cl:
            abort(404)
        vue = request.args.get("vue") if request.args.get("vue") in ("jour", "semaine", "mois") else "semaine"
        d = date_choisie()
        return H.xlsx.reponse_xlsx(nom(f"planification_{vue}_{cl['nom']}_{d.isoformat()}", "xlsx"), ENT, lignes_export(cl, vue, d),
                                   titre=f"Planification {vue}", titre_haut=[f"{config.ECOLE.get('nom', '')} — {cl['nom']} — planification {vue} ({d.strftime('%d/%m/%Y')})"])

    @app.route("/preparation/planification.pdf")
    @H.connexion_requise("preparation")
    def prep_planif_pdf():
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        cls, cl = classe_choisie()
        if not cl:
            abort(404)
        vue = request.args.get("vue") if request.args.get("vue") in ("jour", "semaine", "mois") else "semaine"
        d = date_choisie()
        W, Hh = landscape(A4)
        marge = 12 * mm
        st = ParagraphStyle("p", fontName="Helvetica", fontSize=8, leading=10)
        rows = [[Paragraph(f"<b>{x}</b>", st) for x in ENT]] + [[Paragraph(MP.txt_pdf(x), st) for x in r] for r in lignes_export(cl, vue, d)]
        larg = [32, 26, 30, 38, 14, 95, 38]
        tb = Table(rows, colWidths=[x * mm for x in larg], repeatRows=1)
        tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")),
                                ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        titre = {"jour": "PLANIFICATION JOURNALIÈRE", "semaine": "PLANIFICATION HEBDOMADAIRE", "mois": "PLANIFICATION MENSUELLE"}[vue]
        h = [Paragraph(titre, ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, alignment=1, textColor=pdfs.BLEU, leading=16)),
             Paragraph(f"{MP.txt_pdf(config.ECOLE.get('nom', ''))} — Classe : {MP.txt_pdf(cl['nom'])} — {d.strftime('%d/%m/%Y')}", ParagraphStyle("s", parent=st, alignment=1, fontSize=9.5)),
             Spacer(1, 6), tb]
        buf = io.BytesIO()
        SimpleDocTemplate(buf, pagesize=(W, Hh), leftMargin=marge, rightMargin=marge, topMargin=marge, bottomMargin=marge, title=titre,
                          author="SCOLARIS").build(h, canvasmaker=pdfs.GCanvas)
        return H.pdf_reponse(buf.getvalue(), nom(f"planification_{vue}_{cl['nom']}", "pdf"))

    # ------------------------------------------------------------------ classeurs de fiches
    def fiches_portee(cl, portee, d):
        if portee == "jour":
            jours = [d]
        elif portee == "semaine":
            l = lundi_de(d)
            jours = [l + timedelta(days=i) for i in range(5)]
        else:
            d1 = date(d.year, d.month, 1)
            jours = [d1 + timedelta(days=i) for i in range(31) if (d1 + timedelta(days=i)).month == d.month and (d1 + timedelta(days=i)).weekday() < 5]
        C = MP.corpus()
        vus, out, sommaire = set(), [], []
        if portee == "jour":
            cases = [(d, journee(cl, d))]
        else:
            cases = []
            faits = set()
            for j in jours:
                l = lundi_de(j)
                if l in faits:
                    continue
                faits.add(l)
                cases += [x for x in semaine(cl, l) if x[0] in jours]
        for j, js in cases:
            for c in js:
                fid = c.get("fiche_id")
                if not fid or fid in vus:
                    continue
                vus.add(fid)
                if fid.startswith("mes-"):
                    try:
                        f = H.prep_ma_fiche(int(fid[4:]))
                    except Exception:  # noqa: BLE001
                        continue
                else:
                    f = C["fiche_par_id"].get(fid)
                    if not f:
                        continue
                    f = dict(f, classe_id=cl["id"], source_id=fid, date_seance=j.isoformat())
                out.append(f)
                sommaire.append((j, c.get("horaire", ""), MP.nom_matiere(c["matiere"]), f.get("titre", "")))
        mes = q("SELECT id FROM prep_fiches WHERE ecole_id=? AND user_id=? AND classe_id=? AND date_seance BETWEEN ? AND ? ORDER BY date_seance",
                (H.eco(), g.user["id"], cl["id"], jours[0].isoformat(), jours[-1].isoformat())) if jours else []
        for r in mes:
            mf = H.prep_ma_fiche(r["id"])
            if f"mes-{r['id']}" not in vus:
                out.append(mf)
                sommaire.append((datetime.strptime(mf["date_seance"], "%Y-%m-%d").date() if mf.get("date_seance") else jours[0], "", MP.nom_matiere(mf.get("matiere")), mf.get("titre", "") + " (ma fiche)"))
        return out, sommaire, jours

    def pdf_sommaire(cl, portee, jours, sommaire):
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        st = ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=11.5)
        lib = {"jour": "du jour", "semaine": "de la semaine", "mois": "du mois"}[portee]
        h = [Paragraph(f"CLASSEUR DES FICHES {lib.upper()}", ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=15, alignment=1, textColor=pdfs.BLEU, leading=19)),
             Paragraph(f"{MP.txt_pdf(config.ECOLE.get('nom', ''))} — Classe : {MP.txt_pdf(cl['nom'])} — du {jours[0].strftime('%d/%m/%Y')} au {jours[-1].strftime('%d/%m/%Y')}",
                       ParagraphStyle("s", parent=st, alignment=1)), Spacer(1, 8), Paragraph("<b>SOMMAIRE</b>", st), Spacer(1, 3)]
        rows = [[Paragraph("<b>N°</b>", st), Paragraph("<b>Jour</b>", st), Paragraph("<b>Horaire</b>", st), Paragraph("<b>Matière</b>", st), Paragraph("<b>Fiche</b>", st), Paragraph("<b>Page</b>", st)]]
        for i, (j, hor, mat, titre, page) in enumerate(sommaire, 1):
            rows.append([Paragraph(str(i), st), Paragraph(f"{JOURS_LIB[j.weekday()] if j.weekday() < 5 else ''} {j.strftime('%d/%m')}", st), Paragraph(MP.txt_pdf(hor), st),
                         Paragraph(MP.txt_pdf(mat), st), Paragraph(MP.txt_pdf(titre), st), Paragraph(str(page), st)])
        tb = Table(rows, colWidths=[10 * mm, 24 * mm, 26 * mm, 32 * mm, 80 * mm, 12 * mm], repeatRows=1)
        tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        h.append(tb)
        buf = io.BytesIO()
        SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm, title="Classeur", author="SCOLARIS").build(h, canvasmaker=pdfs.GCanvas)
        return buf.getvalue()

    @app.route("/preparation/classeur")
    @H.connexion_requise("preparation")
    def prep_classeur():
        cls, cl = classe_choisie()
        if not cl:
            flash("Aucune classe : le classeur se prépare pour une de vos classes.", "warning")
            return redirect(url_for("prep_planif"))
        portee = request.args.get("portee") if request.args.get("portee") in ("jour", "semaine", "mois") else "semaine"
        fmt = request.args.get("format") if request.args.get("format") in ("pdf", "doc", "zip") else "pdf"
        d = date_choisie()
        fiches, sommaire, jours = fiches_portee(cl, portee, d)
        if not fiches:
            flash("Aucune fiche à classer pour cette période : la planification de la classe ne cite pas encore de SA, d'unité ou de dossier.", "warning")
            return redirect(url_for("prep_planif", classe=cl["id"], vue=portee, date=d.isoformat()))
        base = f"classeur_{portee}_{cl['nom']}_{d.isoformat()}"
        H.journal("prep_classeur", f"{cl['nom']} {portee} : {len(fiches)} fiche(s)")
        if fmt == "doc":
            return Response("﻿" + H.prep_doc_word(fiches), mimetype="application/msword", headers={"Content-Disposition": f"attachment; filename={nom(base, 'doc')}"})
        from pypdf import PdfReader, PdfWriter
        pages, pdfs_f = [], []
        for f in fiches:
            b = H.prep_pdf_fiches([f])
            pdfs_f.append(b)
            pages.append(len(PdfReader(io.BytesIO(b)).pages))
        brouillon = pdf_sommaire(cl, portee, jours, [s + (0,) for s in sommaire])
        n0 = len(PdfReader(io.BytesIO(brouillon)).pages)
        num, debut = [], n0 + 1
        for p in pages:
            num.append(debut)
            debut += p
        som = pdf_sommaire(cl, portee, jours, [s + (n,) for s, n in zip(sommaire, num)])
        w = PdfWriter()
        for b in [som] + pdfs_f:
            for pg in PdfReader(io.BytesIO(b)).pages:
                w.add_page(pg)
        out = io.BytesIO()
        w.write(out)
        if fmt == "zip":
            z = io.BytesIO()
            with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(nom(base, "pdf"), out.getvalue())
                zf.writestr(nom(base, "doc"), "﻿" + H.prep_doc_word(fiches))
                for i, (f, b) in enumerate(zip(fiches, pdfs_f), 1):
                    zf.writestr(f"fiches/{i:02d}_" + nom(f.get("titre", "fiche"), "pdf"), b)
            return Response(z.getvalue(), mimetype="application/zip", headers={"Content-Disposition": f"attachment; filename={nom(base, 'zip')}"})
        return H.pdf_reponse(out.getvalue(), nom(base, "pdf"))
