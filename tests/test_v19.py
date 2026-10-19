# -*- coding: utf-8 -*-
"""Tests de la version 1.9 : groupes WhatsApp des directeurs et des enseignants (école, CS, DDEMP).
Lancer : python3 -m unittest tests.test_v19"""
import os
import subprocess
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import m_groupes_whatsapp as W  # noqa: E402


def lancer(script, edition):
    env = dict(os.environ)
    env.pop("SCOLARIS_EDITION", None)
    env.pop("SCOLARIS_DATA", None)
    env["SCOLARIS_EDITION_SCRIPT"] = edition
    return subprocess.run([sys.executable, "-c", script], cwd=RACINE, env=env, capture_output=True, text=True, timeout=900)


class TestRegles(unittest.TestCase):
    def test_role(self):
        self.assertEqual(W.role_de("Directeur"), "directeur")
        self.assertEqual(W.role_de("Directeur adjoint"), "adjoint")
        self.assertEqual(W.role_de("Instituteur"), "enseignant")
        self.assertEqual(W.role_de("Gardien"), "autre")

    def test_date_longue(self):
        self.assertEqual(W.date_longue("2026-10-23"), "vendredi 23 octobre 2026")
        self.assertEqual(W.date_longue("2026-11-01"), "dimanche 1er novembre 2026")
        self.assertEqual(W.date_longue(""), "")

    def test_texte_modele(self):
        m = {"type": "convocation", "objet": "la réunion de rentrée", "date": "2026-10-23", "heure": "09:00", "lieu": "la CS"}
        t = W.texte_modele(m, "CS Pobè", "Le Chef de la Circonscription Scolaire", W.PUBLIC["directeurs"])
        self.assertIn("CONVOCATION — CS Pobè", t)
        self.assertIn("Les directeurs et directrices sont convoqués à la réunion de rentrée le *vendredi 23 octobre 2026* à *09:00*", t)
        self.assertTrue(t.endswith("Le Chef de la Circonscription Scolaire"))
        t = W.texte_modele(m, "CS", "X", "Y", {"nom": "ADJOVI Paul", "ecole": "EPP Ahoyéyé"})
        self.assertIn("Bonjour ADJOVI Paul (EPP Ahoyéyé),", t)
        self.assertNotIn("\n\n\n", t)

    def test_vcard(self):
        v = W.vcard([{"nom": "ADJOVI Paul", "ecole": "EPP A, B", "num": "2290197000001", "role_lib": "Directeur"}], "Dir", "CS Pobè")
        self.assertIn("FN:Dir ADJOVI Paul (EPP A\\, B)", v)
        self.assertIn("TEL;TYPE=CELL:+2290197000001", v)
        self.assertTrue(v.startswith("BEGIN:VCARD\r\nVERSION:3.0"))


SCRIPT_ECOLE = r'''
import html, os, sys, tempfile, subprocess
ED = os.environ["SCOLARIS_EDITION_SCRIPT"]
os.environ["SCOLARIS_EDITION"] = ED; os.environ["SCOLARIS_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.getcwd())
subprocess.run([sys.executable, "demo.py"], check=True, env=dict(os.environ), stdout=subprocess.DEVNULL)
from app import app, q, ex
app.config["TESTING"] = True
def ok(r, code=200):
    assert r.status_code == code, (r.request.path, r.status_code, r.data[-800:]); return r
def txt(r): return html.unescape(r.data.decode())
with app.app_context():
    ex("UPDATE utilisateurs SET doit_changer_mdp=0")
    eco = q("SELECT id FROM ecoles ORDER BY id", un=True)["id"]
    ex("INSERT INTO personnel (matricule, nom, prenoms, fonction, telephone, ecole_id, actif) VALUES ('T1','HOUNSA','Marie','Institutrice','97 00 00 01',?,1)", (eco,))
    ex("INSERT INTO personnel (matricule, nom, prenoms, fonction, telephone, ecole_id, actif) VALUES ('T2','DOSSOU','Jean','Gardien','0196000002',?,1)", (eco,))
c = app.test_client(); ok(c.post("/login", data={"identifiant": "directeur", "mdp": "demo1234"}), 302)
t = txt(ok(c.get("/groupes-whatsapp")))
assert "Groupes WhatsApp" in t and "HOUNSA Marie" in t and "+229 01 97 00 00 01" in t, t[-3000:]
assert "DOSSOU" not in t.split("<table")[1]           # le gardien n'est pas dans le groupe des enseignants
t = txt(ok(c.get("/groupes-whatsapp?groupe=personnel")))
assert "DOSSOU Jean" in t and "contacts.vcf?groupe=personnel" in t and "avec tout le personnel" in t
ok(c.post("/groupes-whatsapp/reglages?groupe=enseignants", data={"nom": "Enseignants test", "lien": "https://chat.whatsapp.com/ABC", "message": "Rejoins {groupe} : {lien}"}), 302)
v = ok(c.get("/groupes-whatsapp/contacts.vcf?groupe=enseignants"))
assert "TEL;TYPE=CELL:+2290197000001" in v.data.decode() and v.mimetype == "text/vcard"
r = ok(c.get("/groupes-whatsapp/suivant?groupe=enseignants"), 302)
assert r.headers["Location"].startswith("https://wa.me/2290197000001?text=Rejoins%20Enseignants%20test"), r.headers["Location"]
t = txt(ok(c.get("/groupes-whatsapp")))
assert "envoyée le" in t
ok(c.post("/groupes-whatsapp/reglages?groupe=enseignants", data={"modele_type": "convocation", "objet": "la réunion", "date": "2026-10-23", "heure": "09:00", "lieu": "l'école"}), 302)
t = txt(ok(c.get("/groupes-whatsapp")))
assert "Les enseignants et enseignantes sont convoqués à la réunion le *vendredi 23 octobre 2026*" in t
r = ok(c.get("/groupes-whatsapp/suivant?groupe=enseignants&message=1"), 302)
assert "Bonjour%20HOUNSA%20Marie" in r.headers["Location"]
ok(c.post("/groupes-whatsapp/remise-a-zero?groupe=enseignants"), 302)
assert "envoyée le" not in txt(ok(c.get("/groupes-whatsapp")))
assert "Groupes WhatsApp" in txt(ok(c.get("/")))      # lien dans le menu
c2 = app.test_client(); ok(c2.post("/login", data={"identifiant": "enseignant", "mdp": "demo1234"}), 302)
assert c2.get("/groupes-whatsapp").status_code in (302, 403)
print("ECOLE-OK")
'''

SCRIPT_JUR = r'''
import html, json, os, sys, tempfile
os.environ["SCOLARIS_EDITION"] = os.environ["SCOLARIS_EDITION_SCRIPT"]; os.environ["SCOLARIS_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.getcwd())
import config, demo_juridiction
from app import app, q, ex
app.config["TESTING"] = True
demo_juridiction.main()
def ok(r, code=200):
    assert r.status_code == code, (r.request.path, r.status_code, r.data[-800:]); return r
def txt(r): return html.unescape(r.data.decode())
with app.app_context():
    e = q("SELECT * FROM jur_ecoles ORDER BY id", un=True)
    ex("UPDATE jur_ecoles SET directeur_nom='ADJOVI Paul', directeur_tel='97000001' WHERE id=?", (e["id"],))
    ex("INSERT OR REPLACE INTO jur_sections (ecole_id, annee, section, donnees, source, maj) VALUES (?,?,?,?,?,datetime('now'))",
       (e["id"], config.ANNEE_ACTIVE, "personnel", json.dumps([{"nom": "HOUNSA", "prenoms": "Marie", "fonction": "Institutrice", "role": "enseignant", "telephone": "0196000002", "nip": "N1"}]), "test"))
    z = q("SELECT id FROM jur_zones ORDER BY id", un=True)
    ex("UPDATE jur_zones SET cp_nom='AGBO Rose', cp_telephone='0195000003' WHERE id=?", (z["id"],))
c = app.test_client(); ok(c.post("/login", data={"identifiant": "responsable", "mdp": "demo1234"}), 302)
t = txt(ok(c.get("/groupes-whatsapp")))
assert "Partager les informations avec directeurs des écoles" in t and "contacts.vcf?groupe=directeurs" in t
assert "ADJOVI Paul" in t and "+229 01 97 00 00 01" in t, t[-3000:]
t = txt(ok(c.get("/groupes-whatsapp?groupe=enseignants")))
assert "HOUNSA Marie" in t, t[-3000:]
t = txt(ok(c.get("/groupes-whatsapp?groupe=cp")))
assert "AGBO Rose" in t
if config.EDITION == "ddemp":
    assert "Chefs de circonscription" in t
v = ok(c.get("/groupes-whatsapp/contacts.vcf?groupe=directeurs")).data.decode()
assert "TEL;TYPE=CELL:+2290197000001" in v
r = ok(c.get("/groupes-whatsapp/inviter/E%d?groupe=directeurs" % e["id"]), 302)
assert r.headers["Location"].startswith("https://wa.me/2290197000001")
assert "Groupes WhatsApp" in txt(ok(c.get("/juridiction/tableau-de-bord")))
print("JUR-OK")
'''


class TestParcours(unittest.TestCase):
    def test_publique(self):
        r = lancer(SCRIPT_ECOLE, "publique")
        self.assertIn("ECOLE-OK", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])

    def test_privee(self):
        r = lancer(SCRIPT_ECOLE, "privee")
        self.assertIn("ECOLE-OK", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])

    def test_cs(self):
        r = lancer(SCRIPT_JUR, "cs")
        self.assertIn("JUR-OK", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])

    def test_ddemp(self):
        r = lancer(SCRIPT_JUR, "ddemp")
        self.assertIn("JUR-OK", r.stdout, r.stdout[-3000:] + r.stderr[-6000:])


if __name__ == "__main__":
    unittest.main()
