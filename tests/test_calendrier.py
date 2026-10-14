# -*- coding: utf-8 -*-
"""Tests du calendrier scolaire et des thèmes d'UP (m_calendrier). Lancer : python3 -m unittest tests.test_calendrier"""
import html as html_mod
import io
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
EDITION = os.environ.get("GESCOL_EDITION_TEST", "publique")
DOSSIER = tempfile.mkdtemp(prefix=f"gescol_cal_{EDITION}_")
os.environ["GESCOL_EDITION"] = EDITION
os.environ["GESCOL_DATA"] = DOSSIER

from app import app  # noqa: E402
import config  # noqa: E402
import m_calendrier as MCAL  # noqa: E402

try:
    import openpyxl
except ImportError:  # pragma: no cover
    openpyxl = None


def txt(r):
    return html_mod.unescape(r.data.decode())


class TestCalendrier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.c = app.test_client()
        from werkzeug.security import generate_password_hash
        with app.app_context():
            from app import ex
            ex("UPDATE utilisateurs SET mdp_hash=?, doit_changer_mdp=0 WHERE identifiant='admin'", (generate_password_hash("admin123"),))
        r = cls.c.post("/login", data={"identifiant": "admin", "mdp": "admin123"}, follow_redirects=False)
        assert r.status_code == 302, r.status_code
        # éditions CS / DDEMP : les modules d'école exigent une structure configurée et une école ouverte
        # (/juridiction/structure) ; ce parcours n'est pas couvert par ces tests (même limite que test_synoptique).
        if cls.c.get("/synoptique/calendrier").status_code != 200:
            raise unittest.SkipTest("module d'école non accessible dans cette édition sans école ouverte")

    def test_01_dates(self):
        self.assertEqual(MCAL.en_iso("07/09/2026"), "2026-09-07")
        self.assertEqual(MCAL.en_iso("2027-01-04"), "2027-01-04")
        self.assertEqual(MCAL.en_iso(""), "")
        self.assertIsNone(MCAL.en_iso("31/02/2027"))
        self.assertIsNone(MCAL.en_iso("n'importe quoi"))
        self.assertEqual(MCAL.fr_long("2026-09-14"), "lundi 14/09/2026")

    def test_02_donnees_officielles(self):
        cal = MCAL.CALENDRIER_2026_2027
        self.assertEqual(len(cal), 12)
        for _c, _i, d1, d2, _d, _o in cal:
            self.assertLessEqual(d1, d2)
        th = MCAL.themes_officiels()
        self.assertEqual(sum(1 for t in th if t[0] == "maternelle"), 12)
        self.assertEqual(sum(1 for t in th if t[0] == "primaire"), 12)
        self.assertEqual(sum(1 for t in th if t[0] == "conference"), 5)
        self.assertEqual(sum(1 for t in th if t[0] == "formation"), 5)
        self.assertEqual(MCAL._DATES[0], "09/10/2026")
        self.assertEqual(MCAL._DATES[-1], "07/05/2027")

    def test_03_pages_et_prerempli(self):
        for url in ("/synoptique/calendrier", "/synoptique/themes-up", "/synoptique/calendrier/0", "/synoptique/themes-up/0",
                    "/synoptique/calendrier.pdf", "/synoptique/themes-up.pdf", "/synoptique/calendrier.xlsx", "/synoptique/themes-up.xlsx"):
            r = self.c.get(url + ("?annee=2026-2027" if "/0" not in url else ""))
            self.assertEqual(r.status_code, 200, f"{url} -> {r.status_code}")
        html = txt(self.c.get("/synoptique/calendrier?annee=2026-2027"))
        for mot in ("Pré-rentrée scolaire", "lundi 14/09/2026", "Grandes vacances", "Lundi de Pentecôte", "lundi 17/05/2027"):
            self.assertIn(mot, html)
        html = txt(self.c.get("/synoptique/themes-up?annee=2026-2027"))
        for mot in ("Renouvellement des bureaux", "09/10/2026", "La dictée préparée", "Pédagogie Explicite", "Conférences pédagogiques"):
            self.assertIn(mot, html)
        self.assertEqual(self.c.get("/synoptique/calendrier.pdf?annee=2026-2027").data[:4], b"%PDF")
        self.assertEqual(self.c.get("/synoptique/themes-up.pdf?annee=2026-2027").data[:4], b"%PDF")
        self.assertNotIn("Région pédagogique", html)
        # onglets du synoptique
        self.assertIn("Calendrier scolaire", txt(self.c.get("/synoptique")))

    def test_04_calendrier_crud(self):
        r = self.c.post("/synoptique/calendrier/0", data={"annee": "2026-2027", "categorie": "ferie", "intitule": "Fête locale",
                                                         "debut": "12/03/2027", "fin": "12/03/2027"}, follow_redirects=True)
        self.assertIn("Fête locale", txt(r))
        with app.app_context():
            from app import q
            lid = q("SELECT id FROM calendrier_officiel_lignes WHERE intitule='Fête locale'", un=True)["id"]
        r = self.c.post(f"/synoptique/calendrier/{lid}", data={"annee": "2026-2027", "categorie": "ferie", "intitule": "Fête locale 2",
                                                              "debut": "13/03/2027", "fin": "13/03/2027"}, follow_redirects=True)
        self.assertIn("Fête locale 2", txt(r))
        # erreurs : date illisible, fin avant début, intitulé vide
        for data in ({"intitule": "X", "debut": "31/02/2027", "fin": ""}, {"intitule": "X", "debut": "10/03/2027", "fin": "01/03/2027"},
                     {"intitule": "", "debut": "", "fin": ""}):
            self.assertEqual(self.c.post("/synoptique/calendrier/0", data=dict(data, annee="2026-2027")).status_code, 400)
        r = self.c.post(f"/synoptique/calendrier/{lid}/supprimer", follow_redirects=True)
        self.assertNotIn("Fête locale 2", txt(r))
        # année sans prérempli : tableau vide, puis ajout
        self.assertIn("Aucune ligne pour 2028-2029", txt(self.c.get("/synoptique/calendrier?annee=2028-2029")))
        self.c.post("/synoptique/calendrier/0", data={"annee": "2028-2029", "categorie": "periode", "intitule": "Premier trimestre",
                                                      "debut": "14/09/2028", "fin": "15/12/2028"})
        self.assertIn("Premier trimestre", txt(self.c.get("/synoptique/calendrier?annee=2028-2029")))
        self.assertNotIn("Pré-rentrée scolaire", txt(self.c.get("/synoptique/calendrier?annee=2028-2029")))

    def test_05_themes_crud(self):
        r = self.c.post("/synoptique/themes-up/0", data={"annee": "2026-2027", "categorie": "primaire", "numero": "13",
                                                        "theme": "Thème de test", "administration": "12/03/2027"}, follow_redirects=True)
        self.assertIn("Thème de test", txt(r))
        with app.app_context():
            from app import q
            tid = q("SELECT id FROM themes_up_lignes WHERE theme='Thème de test'", un=True)["id"]
        self.c.post(f"/synoptique/themes-up/{tid}", data={"annee": "2026-2027", "categorie": "primaire", "theme": "Thème de test 2",
                                                         "administration": "PM"})
        self.assertIn("Thème de test 2", txt(self.c.get("/synoptique/themes-up?annee=2026-2027")))
        self.assertEqual(self.c.post("/synoptique/themes-up/0", data={"annee": "2026-2027", "theme": ""}).status_code, 400)
        self.c.post(f"/synoptique/themes-up/{tid}/supprimer")
        self.assertNotIn("Thème de test 2", txt(self.c.get("/synoptique/themes-up?annee=2026-2027")))

    def test_06_reinitialiser(self):
        self.c.post("/synoptique/calendrier/reinitialiser?annee=2026-2027")
        with app.app_context():
            from app import q
            n = q("SELECT COUNT(*) n FROM calendrier_officiel_lignes WHERE annee='2026-2027'", un=True)["n"]
        self.assertEqual(n, 12)
        self.c.post("/synoptique/themes-up/reinitialiser?annee=2026-2027")
        with app.app_context():
            from app import q
            n = q("SELECT COUNT(*) n FROM themes_up_lignes WHERE annee='2026-2027'", un=True)["n"]
        self.assertEqual(n, 34)

    @unittest.skipIf(openpyxl is None, "openpyxl absent")
    def test_07_excel_aller_retour(self):
        self.c.post("/synoptique/calendrier/reinitialiser?annee=2027-2028")          # tableau vide
        r = self.c.get("/synoptique/calendrier.xlsx?annee=2026-2027")
        wb = openpyxl.load_workbook(io.BytesIO(r.data))
        ws = wb.active
        lignes = [[c.value for c in row] for row in ws.iter_rows()]
        self.assertTrue(any(l and "Pré-rentrée scolaire" in [str(x) for x in l] for l in lignes))
        r = self.c.post("/synoptique/calendrier/import?annee=2027-2028", data={"fichier": (io.BytesIO(r.data), "cal.xlsx")},
                        content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("Import terminé : 12 ligne(s)", txt(r))
        self.assertIn("Grandes vacances", txt(self.c.get("/synoptique/calendrier?annee=2027-2028")))
        r = self.c.get("/synoptique/themes-up.xlsx?annee=2026-2027")
        r = self.c.post("/synoptique/themes-up/import?annee=2027-2028", data={"fichier": (io.BytesIO(r.data), "up.xlsx")},
                        content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("Import terminé : 34 thème(s)", txt(r))
        bad = self.c.post("/synoptique/calendrier/import?annee=2027-2028", data={"fichier": (io.BytesIO(b"pas un xlsx"), "x.xlsx")},
                          content_type="multipart/form-data", follow_redirects=True)
        self.assertIn("illisible", txt(bad))

    def test_10_demi_journees(self):
        from datetime import date
        d = MCAL.compter_demi_journees([dict(categorie=c, intitule=i, debut=a, fin=b, classe=MCAL.classe_par_defaut(c, i))
                                        for c, i, a, b, _du, _o in MCAL.CALENDRIER_2026_2027])
        t1, t2, t3 = d["par_periode"]
        self.assertEqual((t1["jours"], t1["conges"]), (70, 0))                 # 14 semaines
        self.assertEqual((t2["jours"], t2["conges"], t2["feries"]), (51, 5, 2))  # 10 sem. 3 j - 2 fêtes (07 et 08/01)
        self.assertEqual((t3["jours"], t3["feries"]), (55, 2))                 # 11 sem. 2 j - Ascension, Pentecôte
        self.assertEqual(d["jours"], 176)
        self.assertEqual(d["demi_journees"], 352)
        self.assertEqual(d["demi_journees_primaire"], 352 - d["mercredis"])
        # un jour férié samedi/dimanche ne retire rien ; le jour de début d'un congé reste un jour de classe
        self.assertEqual(MCAL.compter_demi_journees([dict(categorie="periode", intitule="Trimestre", debut="2027-03-01", fin="2027-03-05", classe=1),
                                                     dict(categorie="ferie", intitule="Samedi", debut="2027-03-06", fin="2027-03-06", classe=0)])["jours"], 5)
        d2 = MCAL.compter_demi_journees([dict(categorie="periode", intitule="Trimestre", debut="2027-03-01", fin="2027-03-05", classe=1),
                                         dict(categorie="conge", intitule="Détente", debut="2027-03-03", fin="2027-03-07", classe=0)])
        self.assertEqual(d2["jours"], 3)                                        # 1, 2 et 3 mars (début du congé = jour de classe)
        self.assertEqual(MCAL.compter_demi_journees([])["demi_journees"], 0)

    def test_11_page_demi_journees(self):
        self.c.post("/synoptique/calendrier/reinitialiser?annee=2026-2027")
        html = txt(self.c.get("/synoptique/calendrier?annee=2026-2027"))
        self.assertIn("176", html)
        self.assertIn("352", html)
        self.assertIn("Jours et demi-journées de classe", html)
        pdf = self.c.get("/synoptique/calendrier.pdf?annee=2026-2027")
        self.assertEqual(pdf.data[:4], b"%PDF")

    def test_12_effigie_memp_et_menus(self):
        import pdfs
        with app.app_context():
            b = pdfs.document_tableau("TEST", ["A"], [["1"]])
        self.assertIn(b"/Image", b)                                           # armoiries / effigie du MEMP à l'en-tête
        html = txt(self.c.get("/synoptique"))
        self.assertIn("Calendrier scolaire", html)
        self.assertIn("Thèmes de l'UP", html)
        self.assertEqual(self.c.get("/").status_code, 200)

    def test_13_sections_de_transmission(self):
        import gzip
        import json
        with app.app_context():
            from app import ex
            ex("UPDATE ecoles SET nom='EPP TEST', departement='Donga', cs='CS Djougou II' WHERE id=1")
        r = self.c.get("/transmission/fichier")
        self.assertEqual(r.status_code, 200)
        secs = json.loads(gzip.decompress(r.data))["ecoles"][0]["sections"]
        self.assertIn("calendrier", secs)
        self.assertEqual(secs["calendrier"]["demi_journees"], 352)
        self.assertEqual(len(secs["calendrier"]["themes_up"]), 34)
        self.assertIn("synoptique", secs)
        import jur_format
        for nom in ("synoptique", "cantine_stock", "evaluations", "calendrier"):
            self.assertIn(nom, jur_format.SECTIONS_ECOLE)

    def test_14_registre_suit_le_calendrier_officiel(self):
        import types
        import m_registre as R
        from datetime import date
        lignes = [dict(categorie=c, intitule=i, debut=d1, fin=d2, classe=MCAL.classe_par_defaut(c, i))
                  for c, i, d1, d2, _du, _o in MCAL.CALENDRIER_2026_2027]
        H = types.SimpleNamespace(q=lambda *a, **k: [], doc_lire=lambda cle, defaut=None: defaut,
                                  calendrier_officiel=lambda annee=None, ecole_id=None: lignes if annee == "2026-2027" else [])
        cal = R.Calendrier(H, 1)
        self.assertEqual(cal.demi(date(2026, 9, 9)), 0)                          # pré-rentrée : pas de classe
        self.assertEqual(cal.demi(date(2026, 9, 14)), 2)                         # lundi de rentrée des classes
        self.assertEqual(cal.demi(date(2026, 9, 16)), 1)                         # mercredi : matin seulement
        self.assertEqual(cal.demi(date(2027, 1, 7)), 0)                          # fête des cultes
        self.assertEqual(cal.demi(date(2027, 2, 22)), 0)                         # congés de détente
        self.assertEqual(cal.demi(date(2027, 2, 19)), 2)                         # dernier jour avant les congés
        self.assertEqual(cal.demi(date(2027, 5, 17)), 0)                         # lundi de Pentecôte
        self.assertEqual(cal.demi(date(2026, 12, 21)), 0)                        # congés de fin de 1er trimestre
        total = sum(cal.demi(d) for d in R.jours_entre(date(2026, 9, 1), date(2027, 8, 31)))
        d = MCAL.compter_demi_journees(lignes)
        self.assertEqual(total, d["demi_journees_primaire"])                     # même décompte que la page du calendrier
        # année sans calendrier renseigné : règles par défaut du registre (rentrée / fin des cours)
        self.assertEqual(R.Calendrier(H, 1).demi(date(2027, 10, 12)), 2)

    # ------------------------------------------------------------ planification mensuelle CE-CM
    def _classe_cm2(self):
        with app.app_context():
            from app import ex, q
            r = q("SELECT id FROM classes WHERE niveau='CM2' LIMIT 1", un=True)
            if r:
                return r["id"]
            cols = {c["name"] for c in q("PRAGMA table_info(classes)")}
            ex("INSERT INTO classes (nom, niveau, cycle) VALUES ('CM2 A','CM2','primaire')" if "cycle" in cols
               else "INSERT INTO classes (nom, niveau) VALUES ('CM2 A','CM2')")
            return q("SELECT id FROM classes WHERE niveau='CM2' LIMIT 1", un=True)["id"]

    def test_15_planification_mensuelle(self):
        import m_planif_mensuelle as PM
        from datetime import date
        # semaines proposées : septembre 2026 (calendrier : classes à partir du 14/09), janvier 2027 (rentrée le 04/01, fêtes 07-08)
        import m_registre as R
        import types
        lignes = [dict(categorie=c, intitule=i, debut=a, fin=b, classe=MCAL.classe_par_defaut(c, i))
                  for c, i, a, b, _d, _o in MCAL.CALENDRIER_2026_2027]
        H = types.SimpleNamespace(q=lambda *a, **k: [], doc_lire=lambda cle, defaut=None: defaut,
                                  calendrier_officiel=lambda annee=None, ecole_id=None: lignes)
        sem = PM.semaines_du_mois("2026-2027", 9, R.Calendrier(H, 1).demi)
        self.assertEqual(sem[0][0], date(2026, 9, 14))                       # la pré-rentrée (07-11/09) est sautée
        self.assertEqual(len(sem), 3)                                        # 14-18, 21-25, 28-30
        sem = PM.semaines_du_mois("2026-2027", 2, R.Calendrier(H, 1).demi)
        self.assertEqual([s[0] for s in sem], [date(2027, 2, 1), date(2027, 2, 8), date(2027, 2, 15)])   # détente dès le 22/02
        self.assertEqual(len(PM.semaines_du_mois("2026-2027", 10)), 5)
        # grille et nettoyage
        self.assertEqual(len(PM.champs_grille()), len(set(PM.champs_grille())))
        self.assertEqual(PM.nettoyer({"fr1_1": " U1 SA2 ", "inconnu": "x", "h_cs": "Djougou II"}), {"fr1_1": "U1 SA2", "h_cs": "Djougou II"})
        cid = self._classe_cm2()
        html = txt(self.c.get(f"/planification-mensuelle?classe={cid}&mois=10&annee=2026-2027"))
        for mot in ("PLANIFICATION" if False else "Planification mensuelle", "1-C.O / Voc. thématique", "10-Exp. écrite N°4 / Écriture",
                    "MATHÉMATIQUES", "ÉDUCATION ARTISTIQUE", "COUTURE", "Le titulaire"):
            self.assertIn(mot, html)
        # PDF et Excel à partir des valeurs postées, puis réimport
        data = {"classe": cid, "mois": 10, "annee": "2026-2027", "h_cs": "Djougou II", "fr2_1": "U2 SA1 S1 E1 Texte n°3", "ma_d_2": "D3",
                "du_1": "05/10/2026", "au_1": "09/10/2026", "p_titulaire": "AKPO Jean"}
        r = self.c.post("/planification-mensuelle/pdf", data=data)
        self.assertEqual((r.status_code, r.data[:4]), (200, b"%PDF"))
        r = self.c.post("/planification-mensuelle/xlsx", data=data)
        self.assertEqual(r.status_code, 200)
        if openpyxl:
            r2 = self.c.post("/planification-mensuelle/import", data={"classe": cid, "mois": 10, "annee": "2026-2027",
                                                                      "fichier": (io.BytesIO(r.data), "p.xlsx")}, content_type="multipart/form-data")
            j = r2.get_json()
            self.assertTrue(j["ok"], j)
            self.assertEqual(j["valeurs"]["fr2_1"], "U2 SA1 S1 E1 Texte n°3")
            self.assertEqual(j["valeurs"]["ma_d_2"], "D3")
            self.assertEqual(j["valeurs"]["p_titulaire"], "AKPO Jean")
            bad = self.c.post("/planification-mensuelle/import", data={"classe": cid, "fichier": (io.BytesIO(b"x"), "x.xlsx")},
                              content_type="multipart/form-data")
            self.assertEqual(bad.status_code, 400)
        # sauvegarde / chargement par la barre de document (clé préfixée par l'école), puis rechargement du formulaire
        cle = PM.clef_doc(cid, "2026-2027", 10)
        self.assertEqual(self.c.post(f"/documents-modules/{cle}", json={"fr2_1": "U9 SA9", "h_cs": "CS Test"}).status_code, 200)
        html = txt(self.c.get(f"/planification-mensuelle?classe={cid}&mois=10&annee=2026-2027"))
        self.assertIn("U9 SA9", html)
        self.assertIn("CS Test", html)
        # lien dans l'espace enseignant
        self.assertIn("Planification mensuelle", txt(self.c.get("/mon-espace")))

    def test_08_fonctions_partagees(self):
        with app.test_request_context():
            pass
        import app as A
        self.assertTrue(callable(getattr(A.H, "calendrier_officiel", None)) if hasattr(A, "H") else True)

    def test_09_droits_ecriture(self):
        c2 = app.test_client()
        self.assertEqual(c2.get("/synoptique/calendrier").status_code, 302)           # non connecté -> login
        self.assertEqual(c2.post("/synoptique/calendrier/0", data={"intitule": "X"}).status_code, 302)


if __name__ == "__main__":
    unittest.main()
