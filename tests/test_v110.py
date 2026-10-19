# -*- coding: utf-8 -*-
"""Tests de la version 1.10 : tableau de bord (programmation et bilan, CCS puis CP), module Effectifs
(apprenants, personnel, catégories, CAP / CEAP, courbes), tableaux globaux des fiches (recensement, rentrée, fin).
Lancer : python3 -m unittest tests.test_v110"""
import os
import subprocess
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import a_effectifs as E  # noqa: E402
import a_fiches as F  # noqa: E402

PREFIXE = "GESCOL" if os.path.exists(os.path.join(RACINE, "GESCOL_PUBLIC.md")) else "SCOLARIS"


def lancer(script, edition):
    env = dict(os.environ)
    for k in ("SCOLARIS_EDITION", "SCOLARIS_DATA", "GESCOL_EDITION", "GESCOL_DATA"):
        env.pop(k, None)
    env["EDITION_SCRIPT"] = edition
    env["PREFIXE_SCRIPT"] = PREFIXE
    return subprocess.run([sys.executable, "-c", script], cwd=RACINE, env=env, capture_output=True, text=True, timeout=900)


class TestRegles(unittest.TestCase):
    def test_categorie(self):
        self.assertEqual(E.categorie({"categorie": "FE"}), "FE")
        self.assertEqual(E.categorie({"categorie": "ACDPCTD"}), "ACDPCTD")
        self.assertEqual(E.categorie({"categorie": "AME"}), "ACDPCTD")
        self.assertEqual(E.categorie({"categorie": "", "fonction": "Éducatrice"}), "EDUCATEUR")
        self.assertEqual(E.categorie({"categorie": "EDUCATEUR"}), "EDUCATEUR")
        self.assertEqual(E.categorie({"categorie": "PRIVE"}), "PRIVE")
        self.assertEqual(E.categorie({"categorie": ""}), "AUTRE")

    def test_calcul(self):
        lignes = [{"id": 1, "nom": "EPP A", "type": "EP", "cs_id": 1, "cs_nom": "CS1", "zone_id": 10, "zone_nom": "Z1",
                   "eff": {"g": 30, "f": 25, "t": 55}},
                  {"id": 2, "nom": "EM B", "type": "EM", "cs_id": 1, "cs_nom": "CS1", "zone_id": 11, "zone_nom": "Z2",
                   "eff": {"g": 10, "f": 12, "t": 22}}]
        pers = [{"ecole_id": 1, "role": "directeur", "sexe": "M", "categorie": "FE", "cap": True, "type_cap": "EP", "ceap": True},
                {"ecole_id": 1, "role": "enseignant", "sexe": "F", "categorie": "ACDPE", "cap": False, "ceap": True},
                {"ecole_id": 2, "role": "enseignant", "sexe": "F", "categorie": "", "fonction": "Éducatrice", "cap": True},
                {"ecole_id": 2, "role": "soutien", "sexe": "M"}]
        grp, tot = E.calculer(lignes, pers, "zone")
        self.assertEqual([g["nom"] for g in grp], ["Z1", "Z2"])
        self.assertEqual(tot["app"]["ep"]["t"], 55)
        self.assertEqual(tot["app"]["em"]["f"], 12)
        self.assertEqual(tot["app"]["t"]["t"], 77)
        self.assertEqual((tot["dir"]["h"], tot["ens"]["f"], tot["tous"]["t"]), (1, 2, 3))
        self.assertEqual(tot["cat"]["EDUCATEUR"]["f"], 1)
        self.assertEqual(tot["dip"]["cap_ep"]["h"], 1)
        self.assertEqual(tot["dip"]["cap_em"]["f"], 1)     # CAP sans option : celle de l'école (EM)
        self.assertEqual(tot["dip"]["ceap_ep"]["t"], 2)
        grp, tot = E.calculer(lignes, pers, "cs")
        self.assertEqual(len(grp), 1)

    def test_diplomes_prive(self):
        self.assertEqual(E.diplome_academique("Licence en sociologie"), "licence")
        self.assertEqual(E.diplome_academique("BAC D"), "bac")
        self.assertEqual(E.diplome_academique("DEUG"), "bac2")
        self.assertEqual(E.diplome_academique("Maîtrise"), "maitrise")
        self.assertEqual(E.diplome_academique("DEA"), "master")
        self.assertEqual(E.diplome_academique(""), "nr")
        self.assertEqual(E.diplome_academique("Diplôme X"), "autre")
        lignes = [{"id": 1, "nom": "EPP", "type": "EP", "secteur": "public", "cs_id": 1, "cs_nom": "C", "zone_id": 1, "zone_nom": "Z",
                   "eff": {"g": 1, "f": 1, "t": 2}},
                  {"id": 2, "nom": "EPRIV", "type": "EM", "secteur": "prive", "cs_id": 1, "cs_nom": "C", "zone_id": 1, "zone_nom": "Z",
                   "eff": {"g": 1, "f": 1, "t": 2}}]
        pers = [{"ecole_id": 1, "role": "enseignant", "sexe": "F", "diplome_academique": "Licence"},
                {"ecole_id": 2, "role": "enseignant", "sexe": "M", "diplome_academique": "BAC"},
                {"ecole_id": 2, "role": "directeur", "sexe": "F"}]
        _g, tot = E.calculer(lignes, pers, "zone")
        # le privé est à part : rien de l'école privée dans les rubriques 1 à 5
        self.assertEqual((tot["ecoles"], tot["app"]["t"]["t"], tot["tous"]["t"]), (1, 2, 1))
        self.assertEqual((tot["aca"]["licence"]["f"], tot["aca"]["bac"]["h"], tot["aca"]["nr"]["t"]), (1, 0, 0))
        self.assertEqual((tot["prive"]["ecoles"], tot["prive"]["app"]["em"]["t"], tot["prive"]["ens"]["h"],
                          tot["prive"]["dir"]["f"], tot["prive"]["em"]["t"]), (1, 2, 1, 1, 2))

    def test_ages(self):
        self.assertEqual((E.cle_age(3), E.cle_age(5), E.cle_age(11), E.cle_age(19)), ("m5", "a5", "a11", "a16"))
        self.assertEqual(E.moyenne_ecart([(6, 1), (8, 1)]), (7.0, 1.0))
        self.assertEqual(E.moyenne_ecart([(6, 0)]), (None, None))
        sec = {"ages": {"CI": {"6": [3, 1], "4": [1, 0]}, "CM2": {"11": [0, 2], "17": [1, 0]}}}
        rec = {"primaire": {"valeurs": {"t73.a4.ci_g": 5, "t73.a7.cp_f": 2}}}
        lignes = [{"id": 1, "nom": "A", "type": "EP", "secteur": "public", "cs_id": 1, "cs_nom": "C", "zone_id": 1,
                   "zone_nom": "Z", "eff": {}, "_sec_eff": sec, "_rec": rec},
                  {"id": 2, "nom": "B", "type": "EP", "secteur": "public", "cs_id": 1, "cs_nom": "C", "zone_id": 2,
                   "zone_nom": "Z2", "eff": {}, "_sec_eff": {}, "_rec": rec},          # repli sur le 7.3 de la fiche
                  {"id": 3, "nom": "P", "type": "EP", "secteur": "prive", "cs_id": 1, "cs_nom": "C", "zone_id": 1,
                   "zone_nom": "Z", "eff": {}, "_sec_eff": {"ages": {"CE1": {"8": [2, 2]}}}, "_rec": {}}]
        grp, tot = E.calculer(lignes, [], "zone")
        t = E.tableau_ages(tot["ages"])
        lg = {x["cle"]: x for x in t["lignes"]}
        self.assertEqual(lg["m5"]["cells"]["CI"][0][0], 6)                   # 1 (âges) + 5 (fiche)
        self.assertEqual(lg["a16"]["cells"]["CM2"][2][0], 1)
        self.assertEqual(t["tot"]["ENS"], [10, 5, 15])
        self.assertEqual(lg["a6"]["cells"]["CI"][0][1], round(100 * 3 / 9, 1))  # 3 G de 6 ans sur 9 G au CI
        self.assertEqual(t["stats"]["CI"][1], (6.0, 0.0))                    # 1 F de 6 ans
        m, e = t["stats"]["ENS"][2]
        self.assertTrue(m and e and e > 0)
        p = E.tableau_ages(tot["prive"]["ages"])
        self.assertEqual((p["tot"]["CE1"], p["stats"]["CE1"][2]), ([2, 2, 4], (8.0, 0.0)))

    def test_courbes(self):
        s = str(E.svg_courbes(["A", "B"], [("X", "#000", [1, 3]), ("Y", "#111", [2, None])]))
        self.assertIn("<polyline", s)
        self.assertIn("A – X : 1", s)
        self.assertEqual(str(E.svg_courbes([], [])), "")

    def test_comparatif(self):
        vue = [{"titre": "1. IDENTIFICATION", "champs": [("1", "Nom", "X")], "tableaux": []},
               {"titre": "4. Infrastructures", "champs": [("4.1", "Salles", "3")],
                "tableaux": [{"titre": "t", "coin": "", "colonnes": ["Bon", "Mauvais"],
                              "lignes": [{"lib": "Classes", "cells": ["2", "1"]}]}]}]
        self.assertEqual(F.rubriques_chiffrees(vue), [1])
        lg = F.comparer([vue, None], vue, 1)
        self.assertEqual([(x["ligne"], x["colonne"], x["vals"], x["total"]) for x in lg],
                         [("4.1 Salles", "", [3.0, None], 3.0), ("Classes", "Bon", [2.0, None], 2.0),
                          ("Classes", "Mauvais", [1.0, None], 1.0)])


SCRIPT = r'''
import html, json, os, sys, tempfile
P = os.environ["PREFIXE_SCRIPT"]
os.environ[P + "_EDITION"] = os.environ["EDITION_SCRIPT"]; os.environ[P + "_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.getcwd())
import config, demo_juridiction
from app import app, q, ex
app.config["TESTING"] = True
demo_juridiction.main()
import m_juridiction as J
def ok(r, code=200):
    assert r.status_code == code, (r.request.path, r.status_code, r.data[-1500:]); return r
def txt(r): return html.unescape(r.data.decode())
with app.app_context():
    a = J.annee()
    c1 = J.cs_liste()[0]
    ex("INSERT OR REPLACE INTO jur_cp_programmes (cs_id, annee, periode, acteur, indicateur, valeur, maj) VALUES (?,?,?,?,?,?,datetime('now'))",
       (c1["id"], a, "T1", "ccs", "su_t", 10))
    ex("INSERT INTO jur_cp_activites (cs_id, zone_id, annee, categorie, date_debut, designation, nb, statut, cree_le) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
       (c1["id"], None, a, "suivi", a[:4] + "-10-05", "Suivi", 1, "realisee"))
    e = q("SELECT * FROM jur_ecoles WHERE type='EP' AND cs_id=? ORDER BY id", (c1["id"],), un=True)
    ex("INSERT OR REPLACE INTO jur_sections (ecole_id, annee, section, donnees, source, maj) VALUES (?,?,?,?,?,datetime('now'))",
       (e["id"], a, "rapports", json.dumps({"rentree-ep": {"annee": a, "valeurs": {"nom_ecole": e["nom"]}}}), "test"))
c = app.test_client(); ok(c.post("/login", data={"identifiant": "responsable", "mdp": "demo1234"}), 302)
t = txt(ok(c.get("/juridiction/tableau-de-bord?periode=T1")))
assert "Programmation et bilan des activités pédagogiques" in t and "Conseillers pédagogiques (CP)" in t
i_ccs, i_cp = t.find("Chef"), t.find("Conseillers pédagogiques (CP)")
assert 0 < i_ccs < i_cp, (i_ccs, i_cp)                      # les CCS avant les CP
assert "1 / 10" in t.replace("<span class=\"gris\"> / ", " / ").replace("</span>", ""), "suivi du CCS : 1 réalisé / 10 programmés"
t = txt(ok(c.get("/juridiction/effectifs")))
for k in ("1. Apprenants", "2. Personnel enseignant", "ACDPCTD (AME)", "Éducateur", "CAP – EP", "CEAP – EM", "<polyline",
          "5. Diplômes académiques", "Licence", "Doctorat", "6. Secteur privé (à part)", "Écoles privées (à part)", "7. Catégories d'âge", "Moins de 5 ans",
          "16 ans et plus", "Écart type", "Âge moyen"):
    assert k in t, k
assert ok(c.get("/juridiction/effectifs?par=ecole")).status_code == 200
x = ok(c.get("/juridiction/effectifs?export=xlsx")); assert x.data[:2] == b"PK"
for fiche in ("recensement-primaire", "recensement-maternelle", "rentree-ep", "fin-ep", "rentree-em", "fin-em"):
    t = txt(ok(c.get("/juridiction/fiches/tableaux?fiche=" + fiche)))
    assert "Tableaux globaux des fiches" in t and "Rubrique" in t, fiche
x = ok(c.get("/juridiction/fiches/tableaux?fiche=rentree-ep&format=xlsx")); assert x.data[:2] == b"PK"
t = txt(ok(c.get("/juridiction/tableau-de-bord")))
assert "Tableaux globaux" in t and "/juridiction/effectifs" in t       # menu
# division DOSP / statistiques : accès au module Effectifs et aux tableaux globaux
d = app.test_client(); ok(d.post("/login", data={"identifiant": "chef", "mdp": "demo1234"}), 302)
ok(d.get("/juridiction/effectifs"))
print("OK-" + config.EDITION)
'''


class TestParcours(unittest.TestCase):
    def test_cs(self):
        r = lancer(SCRIPT, "cs")
        self.assertIn("OK-cs", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])

    def test_ddemp(self):
        r = lancer(SCRIPT, "ddemp")
        self.assertIn("OK-ddemp", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])


if __name__ == "__main__":
    unittest.main()
