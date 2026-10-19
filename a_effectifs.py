# -*- coding: utf-8 -*-
"""v1.10 — Module « Effectifs » des applications Circonscription scolaire et DDEMP.

Une seule page (/juridiction/effectifs) qui rassemble, par sexe, d'après les fiches et paquets transmis par les écoles
(effectifs de la fiche de recensement, personnel de l'état nominatif) :
  1. les apprenants : primaire (EP) et maternelle (EM, espaces enfance), garçons / filles ;
  2. le personnel enseignant : enseignants (adjoints compris) et directeurs, hommes / femmes ;
  3. les catégories : FE, ACDPE, ACDPCTD (AME), Éducateur, Privé, Autre ;
  4. les diplômes professionnels : CAP (EP, EM) et CEAP (EP, EM) ;
  5. les diplômes académiques et universitaires (CEP … Doctorat) ;
  6. les enseignants et directeurs du secteur privé (EP, EM).
Chaque tableau est ventilé par circonscription (DDEMP), par zone pédagogique (CS ou CS choisie à la DDEMP) ou par
école (au choix), avec une COURBE par tableau ; export Excel. La page est rattachée aux divisions chargées des
statistiques (CDOSP / DOSP, statistiques) et des ressources humaines (RH / SRH) — voir a_divisions.
"""
import unicodedata

from flask import abort, render_template, request
from markupsafe import Markup, escape

import config
import m_juridiction as J

CATS = [("FE", "FE"), ("ACDPE", "ACDPE"), ("ACDPCTD", "ACDPCTD (AME)"), ("EDUCATEUR", "Éducateur"),
        ("PRIVE", "Privé"), ("AUTRE", "Autre")]
DIPLOMES = [("cap_ep", "CAP – EP"), ("cap_em", "CAP – EM"), ("ceap_ep", "CEAP – EP"), ("ceap_em", "CEAP – EM")]
# diplômes académiques et universitaires (diplôme le plus élevé déclaré sur la fiche de l'agent)
ACADEMIQUES = [("cep", "CEP"), ("bepc", "BEPC"), ("bac", "BAC"), ("bac2", "BAC + 2 (DEUG, DUT, BTS)"),
               ("licence", "Licence"), ("maitrise", "Maîtrise"), ("master", "Master / DEA / DESS"),
               ("doctorat", "Doctorat"), ("autre", "Autre"), ("nr", "Non renseigné")]
PRIVE = [("ens", "Enseignants"), ("dir", "Directeurs"), ("ep", "dont EP"), ("em", "dont EM")]
PALETTE = ["#2a78d6", "#eb6834", "#1b7f3b", "#8e44ad", "#c99a06", "#d6336c", "#0f766e", "#64748b"]


def _sans_accent(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()


def categorie(p):
    """Catégorie du personnel : FE, ACDPE, ACDPCTD (AME), Éducateur, Privé, Autre."""
    c = str(p.get("categorie") or "").upper().replace("-", "").replace(" ", "")
    if c.startswith("ACDPCTD") or c == "AME":
        return "ACDPCTD"
    if c in ("FE", "ACDPE", "PRIVE"):
        return c
    if c.startswith("EDUC") or "educat" in _sans_accent(p.get("fonction")):
        return "EDUCATEUR"
    return "AUTRE"


def diplome_academique(v):
    """Libellé libre (« Licence en sociologie », « BAC D », « Maîtrise »…) → clé de ACADEMIQUES."""
    d = _sans_accent(v).replace(".", "").replace("-", " ")
    if not d.strip():
        return "nr"
    for cle, motifs in (("doctorat", ("doctorat", "phd", "doctor")), ("master", ("master", "dea", "dess", "mba")),
                        ("maitrise", ("maitrise",)), ("licence", ("licence", "license", "bachelor")),
                        ("bac2", ("deug", "dut", "bts", "duel", "bac + 2", "bac+2", "bac 2", "dues")),
                        ("bac", ("bac", "baccalaureat")), ("bepc", ("bepc", "brevet")), ("cep", ("cep",))):
        if any(m in d for m in motifs):
            return cle
    return "autre"


def oui(v):
    return v is True or str(v or "").strip().lower() in ("1", "oui", "true", "o", "x", "yes")


def sexe(p):
    s = str(p.get("sexe") or "").strip().upper()[:1]
    return "h" if s in ("M", "H", "G") else ("f" if s == "F" else None)


def vide_hf():
    return {"h": 0, "f": 0, "t": 0}


def ajouter(d, sx):
    d["t"] += 1
    if sx:
        d[sx] += 1


def nouveau_groupe(nom):
    return {"nom": nom, "ecoles": 0,
            "app": {"ep": {"g": 0, "f": 0, "t": 0}, "em": {"g": 0, "f": 0, "t": 0}, "t": {"g": 0, "f": 0, "t": 0}},
            "ens": vide_hf(), "dir": vide_hf(), "tous": vide_hf(),
            "cat": {k: vide_hf() for k, _ in CATS}, "dip": {k: vide_hf() for k, _ in DIPLOMES},
            "aca": {k: vide_hf() for k, _ in ACADEMIQUES},
            "prive": {"ecoles": 0, **{k: vide_hf() for k, _ in PRIVE}}}


def calculer(lignes, personnel, par):
    """lignes : écoles (a_tableau.donnees) ; personnel : J.personnel(...). Renvoie (groupes, total)."""
    def cle_nom(l):
        if par == "cs":
            return l["cs_id"], l["cs_nom"] or "Sans circonscription"
        if par == "ecole":
            return l["id"], l["nom"]
        return l["zone_id"], l["zone_nom"] or "Sans zone pédagogique"

    grp, de_ecole = {}, {}
    tot = nouveau_groupe("Total")
    for l in lignes:
        k, nom = cle_nom(l)
        g = grp.setdefault(k, nouveau_groupe(nom))
        de_ecole[l["id"]] = (g, l["type"], l.get("secteur"))
        em = l["type"] in ("EM", "EE")
        if l.get("secteur") == "prive":
            g["prive"]["ecoles"] += 1
            tot["prive"]["ecoles"] += 1
        e = l.get("eff") or {}
        for x in (g, tot):
            x["ecoles"] += 1
            for niv in ("em" if em else "ep", "t"):
                for s_ in ("g", "f", "t"):
                    x["app"][niv][s_] += int(e.get(s_) or 0)
    for p in personnel:
        if p.get("actif") is False:
            continue
        g_t = de_ecole.get(p.get("ecole_id"))
        if not g_t:
            continue
        g, typ, secteur = g_t
        role = p.get("role") or ""
        if role not in ("enseignant", "adjoint", "directeur"):
            continue
        sx = sexe(p)
        em = (p.get("ecole_type") or typ) in ("EM", "EE")
        for x in (g, tot):
            ajouter(x["dir" if role == "directeur" else "ens"], sx)
            ajouter(x["tous"], sx)
            ajouter(x["cat"][categorie(p)], sx)
            if oui(p.get("cap")):
                t_cap = str(p.get("type_cap") or "").upper()
                ajouter(x["dip"]["cap_em" if (t_cap == "EM" or (not t_cap and em)) else "cap_ep"], sx)
            if oui(p.get("ceap")):
                ajouter(x["dip"]["ceap_em" if em else "ceap_ep"], sx)
            ajouter(x["aca"][diplome_academique(p.get("diplome_academique"))], sx)
            if secteur == "prive" or categorie(p) == "PRIVE":
                ajouter(x["prive"]["dir" if role == "directeur" else "ens"], sx)
                ajouter(x["prive"]["em" if em else "ep"], sx)
    return list(grp.values()), tot


def _t(s):
    return str(escape(str(s)))


def svg_courbes(categories, series, aria="Courbes"):
    """Courbes (une par série) sur les groupes en abscisse ; points avec info-bulle et valeur."""
    if not categories or not series:
        return Markup("")
    n = len(categories)
    larg = max(640, 70 * n + 90)
    # légende sur plusieurs lignes si besoin
    leg, x, yl = [], 56, 15.5
    for nom, coul, _ in series:
        w = 28 + 6.6 * len(nom)
        if x + w > larg - 10 and x > 56:
            x, yl = 56, yl + 18
        leg.append((x, yl, nom, coul))
        x += w
    dy = yl - 15.5
    x0, x1, y0, y1 = 56, larg - 20, 34 + dy, 236 + dy
    vals = [v for _, _, vs in series for v in vs if v is not None]
    brut = max(vals + [1]) / 4
    puiss = 10 ** (len(str(int(brut))) - 1) if brut >= 1 else 1
    pas = next(k * puiss for k in (1, 2, 2.5, 5, 10) if k * puiss >= brut)
    m = pas * 4
    def X(i):
        return x0 + (x1 - x0) * (i + .5) / n
    def Y(v):
        return y1 - (y1 - y0) * v / m
    p = [f'<svg viewBox="0 0 {larg} {300 + dy:.0f}" width="100%" role="img" aria-label="{_t(aria)}" class="jsvg" '
         f'style="min-width:{min(larg, 900)}px">']
    for x, yl_, nom, coul in leg:
        p.append(f'<rect x="{x:.0f}" y="{yl_ - 9.5:.1f}" width="11" height="11" rx="2" fill="{coul}"/>'
                 f'<text x="{x + 15:.0f}" y="{yl_:.1f}" class="lg">{_t(nom)}</text>')
    for j in range(5):
        v = pas * j
        yy = Y(v)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" class="gr"/>'
                 f'<text x="{x0 - 6}" y="{yy + 4:.1f}" text-anchor="end" class="vl">{v:g}</text>')
    for i, c in enumerate(categories):
        lib = str(c)
        lib = lib if len(lib) <= 16 else lib[:15] + "…"
        p.append(f'<text x="{X(i):.1f}" y="{y1 + 16}" text-anchor="end" transform="rotate(-30 {X(i):.1f} {y1 + 16})" class="lb">{_t(lib)}</text>')
    for nom, coul, vs in series:
        pts = [(X(i), Y(v)) for i, v in enumerate(vs) if v is not None]
        if len(pts) > 1:
            p.append(f'<polyline fill="none" stroke="{coul}" stroke-width="2.4" stroke-linejoin="round" '
                     f'points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}"/>')
        for i, v in enumerate(vs):
            if v is None:
                continue
            p.append(f'<g><title>{_t(categories[i])} – {_t(nom)} : {v}</title><circle cx="{X(i):.1f}" cy="{Y(v):.1f}" r="3.6" '
                     f'fill="{coul}"/>' + (f'<text x="{X(i):.1f}" y="{Y(v) - 7:.1f}" text-anchor="middle" class="vl">{v}</text>'
                                           if n <= 14 else "") + "</g>")
    p.append("</svg>")
    return Markup("".join(p))


def enregistrer(app, H):
    import a_tableau as T

    def garde():
        if not config.juridiction():
            abort(404)

    @app.route("/juridiction/effectifs")
    @H.connexion_requise()
    def jur_effectifs():
        garde()
        flt = T.lire_filtres()
        par = request.args.get("par") if request.args.get("par") in ("cs", "zone", "ecole") else flt["par"]
        if par == "cs" and config.EDITION == "cs":
            par = "zone"
        lignes = T.donnees(flt["annee"], flt["cs_id"], flt["zone_id"], flt["type"], flt["secteur"], flt["q"])
        pers = J.personnel(flt["annee"], cs_id=flt["cs_id"], zone_id=flt["zone_id"], inclure_agents=False)
        grp, tot = calculer(lignes, pers, par)
        lib = {"cs": "Circonscription", "zone": "Zone pédagogique", "ecole": "École"}[par]
        noms = [g["nom"] for g in grp]
        courbes = {
            "app": svg_courbes(noms, [("Garçons", PALETTE[0], [g["app"]["t"]["g"] for g in grp]),
                                      ("Filles", PALETTE[1], [g["app"]["t"]["f"] for g in grp]),
                                      ("Total", PALETTE[2], [g["app"]["t"]["t"] for g in grp])], "Apprenants"),
            "pers": svg_courbes(noms, [("Enseignants – H", PALETTE[0], [g["ens"]["h"] for g in grp]),
                                       ("Enseignants – F", PALETTE[1], [g["ens"]["f"] for g in grp]),
                                       ("Directeurs – H", PALETTE[3], [g["dir"]["h"] for g in grp]),
                                       ("Directeurs – F", PALETTE[4], [g["dir"]["f"] for g in grp])], "Personnel enseignant"),
            "cat": svg_courbes(noms, [(l, PALETTE[i], [g["cat"][k]["t"] for g in grp]) for i, (k, l) in enumerate(CATS)],
                               "Catégories"),
            "dip": svg_courbes(noms, [(l, PALETTE[i], [g["dip"][k]["t"] for g in grp]) for i, (k, l) in enumerate(DIPLOMES)],
                               "CAP et CEAP"),
            "aca": svg_courbes(noms, [(l, PALETTE[i % len(PALETTE)], [g["aca"][k]["t"] for g in grp])
                                      for i, (k, l) in enumerate(ACADEMIQUES[:8])], "Diplômes académiques"),
            "prive": svg_courbes(noms, [("Enseignants – H", PALETTE[0], [g["prive"]["ens"]["h"] for g in grp]),
                                        ("Enseignants – F", PALETTE[1], [g["prive"]["ens"]["f"] for g in grp]),
                                        ("Directeurs", PALETTE[3], [g["prive"]["dir"]["t"] for g in grp])],
                                 "Secteur privé"),
        }
        if request.args.get("export") == "xlsx":
            haut = [config.ECOLE.get("nom", ""), f"Effectifs – année {flt['annee']} – par {lib.lower()}"]
            lst = grp + [tot]

            def feuille(nom, colonnes, valeurs):
                return (nom, [lib, "Écoles"] + colonnes, [[g["nom"], g["ecoles"]] + valeurs(g) for g in lst], {"titre_haut": haut})
            feuilles = [
                feuille("Apprenants", ["EP – G", "EP – F", "EP – T", "EM – G", "EM – F", "EM – T", "Total – G", "Total – F", "Total"],
                        lambda g: [g["app"][n][s] for n in ("ep", "em", "t") for s in ("g", "f", "t")]),
                feuille("Personnel", ["Enseignants – H", "Enseignants – F", "Enseignants", "Directeurs – H", "Directeurs – F",
                                      "Directeurs", "Ensemble – H", "Ensemble – F", "Ensemble"],
                        lambda g: [g[n][s] for n in ("ens", "dir", "tous") for s in ("h", "f", "t")]),
                feuille("Catégories", [f"{l} – {s.upper()}" if s != "t" else l for _k, l in CATS for s in ("h", "f", "t")],
                        lambda g: [g["cat"][k][s] for k, _l in CATS for s in ("h", "f", "t")]),
                feuille("CAP et CEAP", [f"{l} – {s.upper()}" if s != "t" else l for _k, l in DIPLOMES for s in ("h", "f", "t")],
                        lambda g: [g["dip"][k][s] for k, _l in DIPLOMES for s in ("h", "f", "t")]),
                feuille("Diplômes académiques", [f"{l} – {s.upper()}" if s != "t" else l for _k, l in ACADEMIQUES for s in ("h", "f", "t")],
                        lambda g: [g["aca"][k][s] for k, _l in ACADEMIQUES for s in ("h", "f", "t")]),
                feuille("Secteur privé", ["Écoles privées"] + [f"{l} – {s.upper()}" if s != "t" else l for _k, l in PRIVE for s in ("h", "f", "t")],
                        lambda g: [g["prive"]["ecoles"]] + [g["prive"][k][s] for k, _l in PRIVE for s in ("h", "f", "t")]),
            ]
            H.journal("jur_effectifs", f"{flt['annee']} xlsx")
            return H.xlsx.reponse_classeur(f"effectifs_{flt['annee']}_par_{par}.xlsx", feuilles)
        return render_template("jur_effectifs.html", flt=flt, par=par, lib=lib, grp=grp, tot=tot, CATS=CATS,
                               DIPLOMES=DIPLOMES, ACADEMIQUES=ACADEMIQUES, PRIVE=PRIVE, courbes=courbes, args=T.args_filtres(flt, par=par),
                               args0=T.args_filtres(flt))
