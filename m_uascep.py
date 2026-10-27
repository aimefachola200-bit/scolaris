# -*- coding: utf-8 -*-
"""v1.22 — Bureaux de l'UASCEP (Union des associations scolaires et culturelles des écoles primaires) : membres et
responsables par école, unité pédagogique, zone pédagogique, circonscription scolaire et DDEMP.

Spécification commune à toutes les applications (outils/uascep/spec.md) : mêmes rubriques, même fichier Excel
(feuilles « Membres UASCEP » et « Bureaux »), pour qu'un bureau saisi dans une application s'importe dans une autre.

Périmètres
* éditions école (privée / publique) : le bureau de l'école (écriture : administrateur, fondateur, directeur) ;
  bureaux de son UP et de sa zone en lecture (importés) ;
* édition CS : bureaux des écoles, des UP, des zones et de la circonscription (responsable, chef de service, CP) ;
* édition DDEMP : tous les niveaux du département ;
* enseignant (portail /enseignant, application Enseignant) : lecture seule.

Routes
* /uascep                              uascep            onglets École · UP · Zone · CS · DDEMP · Synthèse · Anciens
* /uascep/bureau/<bid>                 uascep_bureau     GET/POST : bureau (0 = nouveau, ?niveau=&entite=)
* /uascep/membre/<mid>                 uascep_membre     GET/POST : membre (0 = ajouter, ?bureau=)
* /uascep/membre/<mid>/supprimer       POST
* /uascep/bureau/<bid>/reinitialiser   POST : vide le bureau (archive=1 : l'archive dans « Anciens bureaux »)
* /uascep/reinitialiser                POST : tous les bureaux d'un niveau
* /uascep/bureau/<bid>/renouveler      POST : copie du bureau sur un nouveau mandat (l'ancien est archivé)
* /uascep.pdf · /uascep.xlsx · /uascep/import (POST) · /uascep/modele.xlsx
"""
import io
import re
from datetime import date, datetime, timedelta

from flask import abort, flash, g, redirect, render_template, request, url_for

SCHEMA = """
CREATE TABLE IF NOT EXISTS uascep_bureaux (
    id INTEGER PRIMARY KEY, ecole_id INTEGER, niveau TEXT NOT NULL, entite TEXT NOT NULL, entite_lib TEXT,
    date_election TEXT, duree INTEGER DEFAULT 2, date_fin TEXT, date_installation TEXT, ag_date TEXT, ag_lieu TEXT,
    pv TEXT, observations TEXT, statut TEXT NOT NULL DEFAULT 'actif', archive_le TEXT, cree_le TEXT, maj TEXT
);
CREATE INDEX IF NOT EXISTS ix_uascep_b ON uascep_bureaux(ecole_id, niveau, entite, statut);
CREATE TABLE IF NOT EXISTS uascep_membres (
    id INTEGER PRIMARY KEY, bureau_id INTEGER NOT NULL REFERENCES uascep_bureaux(id) ON DELETE CASCADE,
    ordre INTEGER DEFAULT 1, nom TEXT NOT NULL, prenoms TEXT, sexe TEXT, ecole TEXT, up TEXT, zone TEXT, rup TEXT,
    fonction TEXT, qualite TEXT, contact TEXT, email TEXT, date_election TEXT, duree INTEGER, date_fin TEXT,
    date_installation TEXT, observations TEXT, maj TEXT
);
CREATE INDEX IF NOT EXISTS ix_uascep_m ON uascep_membres(bureau_id, ordre);
"""
NIVEAUX = [("ECOLE", "École"), ("UP", "Unité pédagogique"), ("ZONE", "Zone pédagogique"), ("CS", "Circonscription scolaire"),
           ("DDEMP", "Département (DDEMP)")]
NIV_LIB = dict(NIVEAUX)
FONCTIONS = ["Président", "Vice-président", "Secrétaire général", "Secrétaire général adjoint", "Trésorier général",
             "Trésorier général adjoint", "Commissaire aux comptes", "Responsable sport", "Responsable culture",
             "Responsable santé / hygiène", "Responsable genre", "Conseiller", "Membre"]
QUALITES = ["Directeur", "Directrice", "Enseignant", "Enseignante", "CP", "CCS", "Parent d'élève", "Élève", "Autre"]
ENT_MEMBRES = ["Niveau", "Entité", "N° d'ordre", "Nom", "Prénoms", "Sexe", "École", "UP", "Zone pédagogique", "Nom du RUP", "Fonction",
               "Qualité", "Contact", "E-mail", "Date d'élection", "Durée du mandat (ans)", "Date de fin de mandat", "Statut du mandat",
               "Date d'installation", "Observations"]
ENT_BUREAUX = ["Niveau", "Entité", "Date d'élection", "Durée du mandat (ans)", "Date de fin de mandat", "Date d'installation",
               "Date de l'assemblée générale", "Lieu de l'assemblée générale", "PV", "Observations", "Statut"]
CHAMPS_M = ["ordre", "nom", "prenoms", "sexe", "ecole", "up", "zone", "rup", "fonction", "qualite", "contact", "email",
            "date_election", "duree", "date_fin", "date_installation", "observations"]
CHAMPS_B = ["entite_lib", "date_election", "duree", "date_fin", "date_installation", "ag_date", "ag_lieu", "pv", "observations"]


def fin_mandat(election, duree):
    try:
        d = datetime.strptime(election, "%Y-%m-%d").date()
        return d.replace(year=d.year + int(duree or 2)).isoformat()
    except (ValueError, TypeError):
        return ""


def statut_mandat(fin, auj=None):
    auj = auj or date.today()
    if not fin:
        return "Date de fin non renseignée"
    try:
        f = datetime.strptime(fin, "%Y-%m-%d").date()
    except ValueError:
        return "Date de fin non renseignée"
    if f < auj:
        return "Expiré"
    if f <= auj + timedelta(days=90):
        return "À renouveler"
    return "En cours"


def jjmmaaaa(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


def iso(v):
    import outils_xlsx as X
    return X.date_iso(v)


def niveau_de(v):
    t = re.sub(r"[^a-z]", "", __import__("unicodedata").normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode().lower())
    for code, lib in NIVEAUX:
        l = re.sub(r"[^a-z]", "", __import__("unicodedata").normalize("NFKD", lib).encode("ascii", "ignore").decode().lower())
        if t in (code.lower(), l) or (t and l.startswith(t)):
            return code
    return {"circonscription": "CS", "departement": "DDEMP", "unitepedagogique": "UP", "zone": "ZONE", "ecole": "ECOLE"}.get(t)


def enregistrer(app, H):
    q, ex, config = H.q, H.ex, H.config
    H.schema(SCHEMA)

    # ------------------------------------------------------------------ périmètre
    def juridiction():
        return config.EDITION in ("cs", "ddemp")

    def niveaux_visibles():
        if config.EDITION == "ddemp":
            return [c for c, _ in NIVEAUX]
        if config.EDITION == "cs":
            return ["ECOLE", "UP", "ZONE", "CS"]
        return ["ECOLE", "UP", "ZONE"]

    def niveaux_ecriture():
        role = g.user["role"]
        if config.EDITION == "enseignant" or role == "enseignant":
            return []
        if juridiction():
            if role in ("admin", "fondateur", "responsable", "chef_service"):
                return niveaux_visibles()
            if role == "cp":
                return ["ECOLE", "UP", "ZONE"]
            return []
        return ["ECOLE"] if role in ("admin", "fondateur", "directeur") else []

    def cle_ecole():
        return None if juridiction() else H.eco()

    def ident():
        try:
            return {x["cle"]: x["valeur"] for x in H.synoptique_identite(H.eco())}
        except Exception:  # noqa: BLE001
            return {}

    def entites(niveau):
        """[(clé, libellé, {zone, up, rup})] des entités du niveau dans le périmètre."""
        if not juridiction():
            i = ident()
            nom_e = config.ECOLE.get("nom") or i.get("epp") or "École"
            if niveau == "ECOLE":
                return [(str(H.eco()), nom_e, {"ecole": nom_e, "up": i.get("up", ""), "zone": i.get("zone_numero", ""), "rup": i.get("rup_nom", "")})]
            if niveau == "UP":
                return [(i["up"], i["up"], {"up": i["up"], "zone": i.get("zone_numero", ""), "rup": i.get("rup_nom", "")})] if i.get("up") else []
            if niveau == "ZONE":
                return [(i["zone_numero"], f"Zone {i['zone_numero']}", {"zone": i["zone_numero"]})] if i.get("zone_numero") else []
            return []
        try:
            if niveau == "ECOLE":
                return [(str(r["id"]), r["nom"], {"ecole": r["nom"], "zone": r["zone"] or "", "up": "", "rup": ""})
                        for r in q("SELECT e.id, e.nom, z.nom zone FROM jur_ecoles e LEFT JOIN jur_zones z ON z.id=e.zone_id WHERE COALESCE(e.actif,1)=1 ORDER BY z.ordre, e.nom")]
            if niveau == "UP":
                return [(r["nom"], r["nom"], {"up": r["nom"], "zone": r["zone"] or "", "rup": r["rup_nom"] or ""})
                        for r in q("SELECT u.nom, u.rup_nom, z.nom zone FROM jur_up u LEFT JOIN jur_zones z ON z.id=u.zone_id WHERE COALESCE(u.actif,1)=1 ORDER BY z.ordre, u.nom")]
            if niveau == "ZONE":
                return [(r["nom"], r["nom"], {"zone": r["nom"]}) for r in q("SELECT nom FROM jur_zones ORDER BY cs_id, ordre, nom")]
            if niveau == "CS":
                s = q("SELECT * FROM jur_structure WHERE id=1", un=True)
                if config.EDITION == "cs":
                    nom_cs = (s["cs"] or s["nom"]) if s else "Circonscription scolaire"
                    return [(nom_cs, nom_cs, {})]
                return [(r["nom"], r["nom"], {}) for r in q("SELECT nom FROM jur_cs WHERE COALESCE(actif,1)=1 ORDER BY nom")]
            if niveau == "DDEMP":
                s = q("SELECT * FROM jur_structure WHERE id=1", un=True)
                dep = (s["departement"] or s["nom"]) if s else "Département"
                return [(dep, f"DDEMP — {dep}", {})]
        except Exception:  # noqa: BLE001
            return []
        return []

    def bureau(bid):
        r = q("SELECT * FROM uascep_bureaux WHERE id=?", (bid,), un=True)
        if not r or r["niveau"] not in niveaux_visibles() or (r["ecole_id"] or None) != cle_ecole():
            abort(404)
        return r

    def exiger_ecriture(niveau):
        if niveau not in niveaux_ecriture():
            abort(403)

    def bureau_actif(niveau, entite, creer=False, lib=""):
        r = q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND entite=? AND statut='actif' ORDER BY id DESC",
              (cle_ecole(), niveau, entite), un=True)
        if r or not creer:
            return r
        bid = ex("INSERT INTO uascep_bureaux (ecole_id, niveau, entite, entite_lib, duree, statut, cree_le, maj) VALUES (?,?,?,?,2,'actif',?,?)",
                 (cle_ecole(), niveau, entite, lib, H.maintenant(), H.maintenant()))
        return q("SELECT * FROM uascep_bureaux WHERE id=?", (bid,), un=True)

    def membres(bid):
        return [dict(m, statut=statut_mandat(m["date_fin"])) for m in q("SELECT * FROM uascep_membres WHERE bureau_id=? ORDER BY ordre, id", (bid,))]

    def lignes_niveau(niveau, filtres=None, statut="actif"):
        f = filtres or {}
        out = []
        for b in q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND statut=? ORDER BY entite_lib, entite, id",
                   (cle_ecole(), niveau, statut)):
            for m in membres(b["id"]):
                if any(v and (str(m.get(k) or "") != v) for k, v in f.items()):
                    continue
                out.append((b, m))
        return out

    # ------------------------------------------------------------------ pages
    @app.route("/uascep")
    @H.connexion_requise("uascep")
    def uascep():
        vis = niveaux_visibles()
        onglet = request.args.get("onglet") or vis[0]
        if onglet not in vis + ["SYNTHESE", "ANCIENS"]:
            abort(404)
        ctx = {"NIVEAUX": [(c, l) for c, l in NIVEAUX if c in vis], "onglet": onglet, "ecrire": niveaux_ecriture(), "FONCTIONS": FONCTIONS,
               "jjmmaaaa": jjmmaaaa, "statut_mandat": statut_mandat}
        if onglet in vis:
            ents = entites(onglet)
            f = {k: (request.args.get(k) or "").strip() for k in ("zone", "up", "ecole") if request.args.get(k)}
            entite = request.args.get("entite") or ""
            if not juridiction() and ents:
                entite = entite or ents[0][0]
            b = bureau_actif(onglet, entite) if entite else None
            ctx.update(entites=ents, entite=entite, bureau=b, membres=membres(b["id"]) if b else [], filtres=f,
                       toutes=lignes_niveau(onglet, f) if not entite else [],
                       zones=sorted({e[2].get("zone", "") for e in entites("ECOLE") + entites("UP") if e[2].get("zone")}),
                       ups=sorted({e[2].get("up", "") for e in entites("UP") if e[2].get("up")}))
        elif onglet == "SYNTHESE":
            syn = []
            par_fonction, par_sexe = {}, {"M": 0, "F": 0, "": 0}
            alertes = []
            for c in vis:
                bs = q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND statut='actif'", (cle_ecole(), c))
                nm = 0
                for b in bs:
                    ms = membres(b["id"])
                    nm += len(ms)
                    for m in ms:
                        par_fonction[m["fonction"] or "—"] = par_fonction.get(m["fonction"] or "—", 0) + 1
                        par_sexe[m["sexe"] if m["sexe"] in ("M", "F") else ""] += 1
                    st = statut_mandat(b["date_fin"])
                    if st in ("Expiré", "À renouveler"):
                        alertes.append((NIV_LIB[c], b["entite_lib"] or b["entite"], st, jjmmaaaa(b["date_fin"])))
                syn.append((NIV_LIB[c], len(bs), nm))
            ctx.update(syn=syn, par_fonction=sorted(par_fonction.items(), key=lambda x: FONCTIONS.index(x[0]) if x[0] in FONCTIONS else 99),
                       par_sexe=par_sexe, alertes=alertes)
        else:
            ctx["anciens"] = [(b, membres(b["id"])) for b in q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND statut='archive' AND niveau IN ({}) ORDER BY archive_le DESC, id DESC".format(",".join("?" * len(vis))), (cle_ecole(), *vis))]
        return render_template("uascep.html", **ctx)

    def lire_bureau(f, b=None):
        d = {k: (f.get(k) or "").strip()[:300] for k in CHAMPS_B}
        for k in ("date_election", "date_fin", "date_installation", "ag_date"):
            d[k] = iso(d[k]) if d[k] else ""
        try:
            d["duree"] = max(1, min(10, int(d["duree"] or 2)))
        except ValueError:
            d["duree"] = 2
        if d["date_election"] and not d["date_fin"]:
            d["date_fin"] = fin_mandat(d["date_election"], d["duree"])
        return d

    @app.route("/uascep/bureau/<int:bid>", methods=["GET", "POST"])
    @H.connexion_requise("uascep")
    def uascep_bureau(bid):
        if bid:
            b = dict(bureau(bid))
            niveau, entite = b["niveau"], b["entite"]
        else:
            niveau, entite = request.values.get("niveau") or "", request.values.get("entite") or ""
            if niveau not in niveaux_visibles():
                abort(404)
            lib = next((e[1] for e in entites(niveau) if e[0] == entite), entite)
            if not entite:
                abort(400)
            b = {"id": 0, "niveau": niveau, "entite": entite, "entite_lib": lib, "duree": 2}
        exiger_ecriture(niveau)
        if request.method == "POST":
            d = lire_bureau(request.form)
            if not bid:
                bb = bureau_actif(niveau, entite, creer=True, lib=d["entite_lib"] or b["entite_lib"])
                bid = bb["id"]
            ex("UPDATE uascep_bureaux SET " + ", ".join(f"{k}=?" for k in CHAMPS_B) + ", maj=? WHERE id=?",
               tuple(d[k] for k in CHAMPS_B) + (H.maintenant(), bid))
            H.journal("uascep_bureau", f"{NIV_LIB[niveau]} {entite}")
            flash("Bureau enregistré.", "success")
            return redirect(url_for("uascep", onglet=niveau, entite=entite))
        return render_template("uascep_bureau.html", b=b, NIV_LIB=NIV_LIB)

    @app.route("/uascep/membre/<int:mid>", methods=["GET", "POST"])
    @H.connexion_requise("uascep")
    def uascep_membre(mid):
        if mid:
            m = q("SELECT * FROM uascep_membres WHERE id=?", (mid,), un=True)
            if not m:
                abort(404)
            b = bureau(m["bureau_id"])
            m = dict(m)
        else:
            bid = request.values.get("bureau", type=int)
            if bid:
                b = bureau(bid)
            else:
                niveau, entite = request.values.get("niveau") or "", request.values.get("entite") or ""
                if niveau not in niveaux_visibles() or not entite:
                    abort(404)
                exiger_ecriture(niveau)
                b = bureau_actif(niveau, entite, creer=True, lib=next((e[1] for e in entites(niveau) if e[0] == entite), entite))
            info = next((e[2] for e in entites(b["niveau"]) if e[0] == b["entite"]), {})
            n = q("SELECT COALESCE(MAX(ordre),0)+1 n FROM uascep_membres WHERE bureau_id=?", (b["id"],), un=True)["n"]
            m = {"id": 0, "ordre": n, "ecole": info.get("ecole", ""), "up": info.get("up", ""), "zone": info.get("zone", ""), "rup": info.get("rup", ""),
                 "date_election": b["date_election"] or "", "duree": b["duree"] or 2, "date_fin": b["date_fin"] or "", "date_installation": b["date_installation"] or ""}
        exiger_ecriture(b["niveau"])
        if request.method == "POST":
            f = request.form
            d = {k: (f.get(k) or "").strip()[:300] for k in CHAMPS_M}
            err = []
            if not d["nom"]:
                err.append("Le nom est obligatoire.")
            d["sexe"] = d["sexe"] if d["sexe"] in ("M", "F") else ""
            for k in ("date_election", "date_fin", "date_installation"):
                d[k] = iso(d[k]) if d[k] else ""
            try:
                d["ordre"] = int(d["ordre"] or 1)
                d["duree"] = int(d["duree"] or (b["duree"] or 2))
            except ValueError:
                err.append("N° d'ordre et durée du mandat : nombres entiers.")
            if d["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", d["email"]):
                err.append("Adresse e-mail invalide.")
            if d["date_election"] and not d["date_fin"]:
                d["date_fin"] = fin_mandat(d["date_election"], d["duree"])
            if err:
                for e in err:
                    flash(e, "danger")
                return render_template("uascep_membre.html", m=dict(m, **d), b=b, FONCTIONS=FONCTIONS, QUALITES=QUALITES, NIV_LIB=NIV_LIB), 400
            if mid:
                ex("UPDATE uascep_membres SET " + ", ".join(f"{k}=?" for k in CHAMPS_M) + ", maj=? WHERE id=?", tuple(d[k] for k in CHAMPS_M) + (H.maintenant(), mid))
            else:
                ex("INSERT INTO uascep_membres (bureau_id, " + ", ".join(CHAMPS_M) + ", maj) VALUES (?," + ",".join("?" * len(CHAMPS_M)) + ",?)",
                   (b["id"],) + tuple(d[k] for k in CHAMPS_M) + (H.maintenant(),))
            H.journal("uascep_membre", f"{NIV_LIB[b['niveau']]} {b['entite']} : {d['nom']} {d['prenoms']}")
            flash("Membre enregistré.", "success")
            return redirect(url_for("uascep", onglet=b["niveau"], entite=b["entite"]))
        return render_template("uascep_membre.html", m=m, b=b, FONCTIONS=FONCTIONS, QUALITES=QUALITES, NIV_LIB=NIV_LIB)

    @app.route("/uascep/membre/<int:mid>/supprimer", methods=["POST"])
    @H.connexion_requise("uascep")
    def uascep_membre_supprimer(mid):
        m = q("SELECT * FROM uascep_membres WHERE id=?", (mid,), un=True)
        if not m:
            abort(404)
        b = bureau(m["bureau_id"])
        exiger_ecriture(b["niveau"])
        ex("DELETE FROM uascep_membres WHERE id=?", (mid,))
        H.journal("uascep_membre_supprime", f"{m['nom']} {m['prenoms'] or ''}")
        flash("Membre supprimé.", "success")
        return redirect(url_for("uascep", onglet=b["niveau"], entite=b["entite"]))

    def archiver(b):
        ex("UPDATE uascep_bureaux SET statut='archive', archive_le=?, maj=? WHERE id=?", (H.maintenant(), H.maintenant(), b["id"]))

    def reinitialiser(b, archive):
        if archive and q("SELECT 1 FROM uascep_membres WHERE bureau_id=? LIMIT 1", (b["id"],), un=True):
            archiver(b)
        else:
            ex("DELETE FROM uascep_membres WHERE bureau_id=?", (b["id"],))
            ex("DELETE FROM uascep_bureaux WHERE id=?", (b["id"],))

    @app.route("/uascep/bureau/<int:bid>/reinitialiser", methods=["POST"])
    @H.connexion_requise("uascep")
    def uascep_reinitialiser(bid):
        b = bureau(bid)
        exiger_ecriture(b["niveau"])
        reinitialiser(b, bool(request.form.get("archive")))
        H.journal("uascep_reinitialise", f"{NIV_LIB[b['niveau']]} {b['entite']}")
        flash("Bureau réinitialisé" + (" (ancien bureau archivé)." if request.form.get("archive") else "."), "success")
        return redirect(url_for("uascep", onglet=b["niveau"], entite=b["entite"]))

    @app.route("/uascep/reinitialiser", methods=["POST"])
    @H.connexion_requise("uascep")
    def uascep_reinitialiser_tous():
        niveau = request.form.get("niveau") or ""
        if niveau not in niveaux_visibles():
            abort(404)
        exiger_ecriture(niveau)
        bs = q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND statut='actif'", (cle_ecole(), niveau))
        for b in bs:
            reinitialiser(b, bool(request.form.get("archive")))
        H.journal("uascep_reinitialise_tous", f"{NIV_LIB[niveau]} : {len(bs)} bureau(x)")
        flash(f"{len(bs)} bureau(x) réinitialisé(s).", "success")
        return redirect(url_for("uascep", onglet=niveau))

    @app.route("/uascep/bureau/<int:bid>/renouveler", methods=["POST"])
    @H.connexion_requise("uascep")
    def uascep_renouveler(bid):
        b = bureau(bid)
        exiger_ecriture(b["niveau"])
        el = iso(request.form.get("date_election") or "") or date.today().isoformat()
        duree = b["duree"] or 2
        fin = fin_mandat(el, duree)
        archiver(b)
        nid = ex("INSERT INTO uascep_bureaux (ecole_id, niveau, entite, entite_lib, date_election, duree, date_fin, statut, observations, cree_le, maj) "
                 "VALUES (?,?,?,?,?,?,?,'actif',?,?,?)", (b["ecole_id"], b["niveau"], b["entite"], b["entite_lib"], el, duree, fin,
                                                         "Renouvellement du bureau", H.maintenant(), H.maintenant()))
        for m in membres(bid):
            ex("INSERT INTO uascep_membres (bureau_id, " + ", ".join(CHAMPS_M) + ", maj) VALUES (?," + ",".join("?" * len(CHAMPS_M)) + ",?)",
               (nid,) + tuple({**m, "date_election": el, "duree": duree, "date_fin": fin, "date_installation": ""}[k] for k in CHAMPS_M) + (H.maintenant(),))
        H.journal("uascep_renouvele", f"{NIV_LIB[b['niveau']]} {b['entite']}")
        flash("Bureau renouvelé sur un nouveau mandat (l'ancien est dans « Anciens bureaux »).", "success")
        return redirect(url_for("uascep", onglet=b["niveau"], entite=b["entite"]))

    # ------------------------------------------------------------------ Excel (spécification commune) et PDF
    def lignes_export(niveaux):
        lm, lb = [], []
        for c in niveaux:
            for b in q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND statut='actif' ORDER BY entite", (cle_ecole(), c)):
                lb.append([c, b["entite_lib"] or b["entite"], jjmmaaaa(b["date_election"]), b["duree"] or "", jjmmaaaa(b["date_fin"]), jjmmaaaa(b["date_installation"]),
                           jjmmaaaa(b["ag_date"]), b["ag_lieu"] or "", b["pv"] or "", b["observations"] or "", b["statut"]])
                for m in membres(b["id"]):
                    lm.append([c, b["entite_lib"] or b["entite"], m["ordre"], m["nom"], m["prenoms"] or "", m["sexe"] or "", m["ecole"] or "", m["up"] or "",
                               m["zone"] or "", m["rup"] or "", m["fonction"] or "", m["qualite"] or "", m["contact"] or "", m["email"] or "",
                               jjmmaaaa(m["date_election"]), m["duree"] or "", jjmmaaaa(m["date_fin"]), m["statut"], jjmmaaaa(m["date_installation"]), m["observations"] or ""])
        return lm, lb

    @app.route("/uascep.xlsx")
    @H.connexion_requise("uascep")
    def uascep_xlsx():
        vis = niveaux_visibles()
        niv = [request.args["niveau"]] if request.args.get("niveau") in vis else vis
        lm, lb = lignes_export(niv)
        return H.xlsx.reponse_classeur("bureaux_uascep.xlsx", [("Membres UASCEP", ENT_MEMBRES, lm, {}), ("Bureaux", ENT_BUREAUX, lb, {})])

    @app.route("/uascep/modele.xlsx")
    @H.connexion_requise("uascep")
    def uascep_modele():
        ex_ = ["École", "EPP Exemple", 1, "NOM", "Prénoms", "F", "EPP Exemple", "UP 1", "Zone 1", "", "Présidente", "Enseignante", "", "",
               "15/10/2026", 2, "15/10/2028", "", "", ""]
        return H.xlsx.reponse_classeur("modele_uascep.xlsx", [("Membres UASCEP", ENT_MEMBRES, [ex_], {}), ("Bureaux", ENT_BUREAUX, [], {})])

    @app.route("/uascep/import", methods=["POST"])
    @H.connexion_requise("uascep")
    def uascep_import():
        import outils_xlsx as X
        fichier = request.files.get("fichier")
        if not fichier or not fichier.filename:
            flash("Choisissez un fichier Excel.", "danger")
            return redirect(url_for("uascep"))
        try:
            wb = X._openpyxl().load_workbook(io.BytesIO(fichier.read()), read_only=True, data_only=True)
        except Exception:  # noqa: BLE001
            flash("Fichier Excel illisible : enregistrez-le au format .xlsx.", "danger")
            return redirect(url_for("uascep"))
        feuilles = {X.normaliser(ws.title): ws for ws in wb.worksheets}
        ws_m = feuilles.get(X.normaliser("Membres UASCEP")) or wb.worksheets[0]
        ws_b = feuilles.get(X.normaliser("Bureaux"))
        refus, nb_m, nb_b = [], 0, 0
        ecrire = niveaux_ecriture()
        lib_ent = {}
        for c in niveaux_visibles():
            for k, lib, _i in entites(c):
                lib_ent[(c, X.normaliser(lib))] = k
                lib_ent[(c, X.normaliser(k))] = k

        def cle_entite(niv, v):
            if not juridiction() and niv == "ECOLE":
                return str(H.eco())
            return lib_ent.get((niv, X.normaliser(v)), str(v).strip())

        def lignes(ws):
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            i = next((k for k, r in enumerate(rows[:20]) if r and X.normaliser(r[0]) == "niveau"), 0)
            return [str(v or "").strip() for v in rows[i]], [r for r in rows[i + 1:] if any(v not in (None, "") for v in r)], i

        if ws_b is not None:
            ent, rows, i0 = lignes(ws_b)
            ci = {h: X.colonne(ent, h) for h in ENT_BUREAUX}
            for n, r in enumerate(rows, i0 + 2):
                v = {h: X.valeur(r, ci[h]) for h in ENT_BUREAUX}
                niv = niveau_de(v["Niveau"])
                if niv not in ecrire:
                    refus.append(f"Bureaux, ligne {n} : niveau « {v['Niveau']} » hors de votre périmètre.")
                    continue
                k = cle_entite(niv, v["Entité"])
                b = bureau_actif(niv, k, creer=True, lib=v["Entité"])
                el = iso(v["Date d'élection"])
                du = int(v["Durée du mandat (ans)"]) if str(v["Durée du mandat (ans)"]).isdigit() else 2
                ex("UPDATE uascep_bureaux SET date_election=?, duree=?, date_fin=?, date_installation=?, ag_date=?, ag_lieu=?, pv=?, observations=?, maj=? WHERE id=?",
                   (el, du, iso(v["Date de fin de mandat"]) or fin_mandat(el, du), iso(v["Date d'installation"]), iso(v["Date de l'assemblée générale"]),
                    v["Lieu de l'assemblée générale"], v["PV"], v["Observations"], H.maintenant(), b["id"]))
                nb_b += 1
        ent, rows, i0 = lignes(ws_m)
        ci = {h: X.colonne(ent, h) for h in ENT_MEMBRES}
        if ci["Nom"] is None or ci["Niveau"] is None:
            flash("En-têtes introuvables : utilisez le modèle (feuille « Membres UASCEP »).", "danger")
            return redirect(url_for("uascep"))
        for n, r in enumerate(rows, i0 + 2):
            v = {h: X.valeur(r, ci[h]) for h in ENT_MEMBRES}
            niv = niveau_de(v["Niveau"])
            if niv not in ecrire:
                refus.append(f"Membres, ligne {n} : niveau « {v['Niveau']} » hors de votre périmètre.")
                continue
            if not v["Nom"]:
                refus.append(f"Membres, ligne {n} : nom manquant.")
                continue
            k = cle_entite(niv, v["Entité"])
            b = bureau_actif(niv, k, creer=True, lib=v["Entité"])
            el = iso(v["Date d'élection"])
            du = int(v["Durée du mandat (ans)"]) if str(v["Durée du mandat (ans)"]).isdigit() else (b["duree"] or 2)
            d = {"ordre": int(v["N° d'ordre"]) if str(v["N° d'ordre"]).isdigit() else 1, "nom": v["Nom"], "prenoms": v["Prénoms"], "sexe": X.sexe(v["Sexe"]),
                 "ecole": v["École"], "up": v["UP"], "zone": v["Zone pédagogique"], "rup": v["Nom du RUP"], "fonction": v["Fonction"], "qualite": v["Qualité"],
                 "contact": v["Contact"], "email": v["E-mail"], "date_election": el, "duree": du, "date_fin": iso(v["Date de fin de mandat"]) or fin_mandat(el, du),
                 "date_installation": iso(v["Date d'installation"]), "observations": v["Observations"]}
            ex_m = q("SELECT id FROM uascep_membres WHERE bureau_id=? AND lower(nom)=lower(?) AND lower(COALESCE(prenoms,''))=lower(?)", (b["id"], d["nom"], d["prenoms"] or ""), un=True)
            if ex_m:
                ex("UPDATE uascep_membres SET " + ", ".join(f"{c}=?" for c in CHAMPS_M) + ", maj=? WHERE id=?", tuple(d[c] for c in CHAMPS_M) + (H.maintenant(), ex_m["id"]))
            else:
                ex("INSERT INTO uascep_membres (bureau_id, " + ", ".join(CHAMPS_M) + ", maj) VALUES (?," + ",".join("?" * len(CHAMPS_M)) + ",?)",
                   (b["id"],) + tuple(d[c] for c in CHAMPS_M) + (H.maintenant(),))
            nb_m += 1
        H.journal("uascep_import", f"{nb_m} membre(s), {nb_b} bureau(x), {len(refus)} refus")
        flash(f"Import : {nb_m} membre(s) et {nb_b} bureau(x) enregistrés ; {len(refus)} ligne(s) refusée(s).", "success" if not refus else "warning")
        for x in refus[:15]:
            flash(x, "warning")
        return redirect(url_for("uascep"))

    @app.route("/uascep.pdf")
    @H.connexion_requise("uascep")
    def uascep_pdf():
        import pdfs
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        vis = niveaux_visibles()
        niv = [request.args["niveau"]] if request.args.get("niveau") in vis else vis
        entite = request.args.get("entite") or ""
        W, Hh = landscape(A4)
        marge = 12 * mm
        utile = W - 2 * marge
        st = ParagraphStyle("p", fontName="Helvetica", fontSize=7.6, leading=9.4)
        stt = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, alignment=1, textColor=pdfs.BLEU, leading=16)
        h, n = [], 0
        for c in niv:
            for b in q("SELECT * FROM uascep_bureaux WHERE COALESCE(ecole_id,0)=COALESCE(?,0) AND niveau=? AND statut='actif'" + (" AND entite=?" if entite else "") + " ORDER BY entite",
                       (cle_ecole(), c) + ((entite,) if entite else ())):
                ms = membres(b["id"])
                if n:
                    h.append(PageBreak())
                n += 1
                h += [Paragraph(f"BUREAU DE L'UASCEP — {NIV_LIB[c].upper()}", stt),
                      Paragraph(f"{MPtxt(b['entite_lib'] or b['entite'])} · élu le {jjmmaaaa(b['date_election']) or '……'} · fin de mandat {jjmmaaaa(b['date_fin']) or '……'} · {statut_mandat(b['date_fin'])}",
                                ParagraphStyle("s", parent=st, alignment=1, fontSize=9)), Spacer(1, 5)]
                ent = ["N°", "Nom et prénoms", "Sexe", "École", "UP", "Zone", "Nom du RUP", "Fonction", "Qualité", "Contact", "Élection", "Fin de mandat", "Statut"]
                data = [[Paragraph(f"<b>{x}</b>", st) for x in ent]]
                for m in ms:
                    data.append([Paragraph(MPtxt(x), st) for x in [m["ordre"], f"{m['nom']} {m['prenoms'] or ''}", m["sexe"] or "", m["ecole"] or "", m["up"] or "", m["zone"] or "",
                                                                   m["rup"] or "", m["fonction"] or "", m["qualite"] or "", m["contact"] or "", jjmmaaaa(m["date_election"]),
                                                                   jjmmaaaa(m["date_fin"]), m["statut"]]])
                larg = [9, 40, 10, 32, 20, 18, 28, 30, 22, 24, 18, 20, 0]
                larg[-1] = utile / mm - sum(larg[:-1])
                tb = Table(data, colWidths=[x * mm for x in larg], repeatRows=1)
                tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#98A2B3")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4ECF5")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
                pres = next((m for m in ms if (m["fonction"] or "").startswith("Président")), None)
                sigs = [("Le / La Président(e) du bureau", f"{pres['nom']} {pres['prenoms'] or ''}" if pres else "", None, False),
                        ({"ECOLE": "Le Directeur / La Directrice", "UP": "Le RUP", "ZONE": "Le CP de zone", "CS": "Le Chef de la circonscription scolaire", "DDEMP": "Le Directeur départemental"}[c], "", None, True)]
                h += [tb, Spacer(1, 8), KeepTogether([pdfs._BlocSignatures(sigs, utile)])]
        if not h:
            flash("Aucun bureau à imprimer.", "warning")
            return redirect(url_for("uascep"))

        def deco(cv, doc):
            pdfs._entete_primaire(cv, W, Hh, marge, None, None)
        buf = io.BytesIO()
        SimpleDocTemplate(buf, pagesize=(W, Hh), leftMargin=marge, rightMargin=marge, topMargin=marge + 30 * mm, bottomMargin=12 * mm, title="Bureaux UASCEP",
                          author="SCOLARIS").build(h, onFirstPage=deco, onLaterPages=deco, canvasmaker=pdfs.GCanvas)
        return H.pdf_reponse(buf.getvalue(), "bureaux_uascep.pdf")

    def MPtxt(t):
        return str(t if t is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
