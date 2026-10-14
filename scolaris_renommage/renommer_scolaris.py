# -*- coding: utf-8 -*-
"""
Renommage de GESCOL en SCOLARIS (nom, logo, icônes, fichiers, paquets Android, documents) — à lancer UNE FOIS à la racine du projet.

    python renommer_scolaris.py [dossier_projet] [--essai]

--essai : affiche ce qui serait modifié, sans rien écrire.

Ce que fait le script (idempotent : on peut le relancer sans risque) :
 1. sauvegarde les fichiers texte dans sauvegarde_avant_scolaris.zip (sauf s'il existe déjà) ;
 2. remplace GESCOL / Gescol / gescol par SCOLARIS / Scolaris / scolaris dans tous les fichiers texte
    (code, modèles HTML, JS, documentation, scripts, Android, Windows, Render, Docker, GitHub Actions…) ;
 3. renomme les fichiers et dossiers (gescol.js, gescol_serveur.py, GESCOL_PUBLIC.md, bj/gescol/…) ;
 4. met le logo : icône à la place de la lettre « G » du menu, logo sur la page de connexion, favicon SVG, icônes PNG / ICO
    (navigateur, application installable, Windows, Android) ;
 5. ajoute « SCOLARIS · » devant la mention « Conception : … » codée en dur (Excel, hors-ligne…) ;
 6. COMPATIBILITÉ avec les installations existantes (lignes marquées « LEGACY-GESCOL », jamais renommées) :
    variables d'environnement GESCOL_* encore lues, ancien dossier de données et ancienne base gescol.db réutilisés
    s'ils existent, anciens fichiers de transmission (.gescol) toujours acceptés.
"""
import io
import os
import re
import shutil
import sys
import zipfile

MARQUE = "LEGACY-GESCOL"
IGNORER_DOSSIERS = {".git", ".github_cache", "venv", ".venv", "node_modules", "__pycache__", "instance", "build", "dist", ".cache",
                    ".npm-global", ".gradle", "sauvegarde_avant_scolaris"}
EXT_TEXTE = {".py", ".html", ".htm", ".js", ".css", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".bat", ".sh",
             ".iss", ".spec", ".gradle", ".xml", ".java", ".kt", ".properties", ".svg", ".webmanifest", ".gitignore", ".dockerignore", ""}
NOMS_TEXTE = {"Dockerfile", "Procfile", ".gitignore", ".dockerignore", "LICENSE"}
REMPL = (("GESCOL", "SCOLARIS"), ("Gescol", "Scolaris"), ("gescol", "scolaris"))


def lister(racine):
    for dp, dn, fn in os.walk(racine):
        dn[:] = [d for d in dn if d not in IGNORER_DOSSIERS]
        for f in fn:
            yield os.path.join(dp, f)


def est_texte(chemin):
    nom = os.path.basename(chemin)
    if nom in NOMS_TEXTE or os.path.splitext(nom)[1].lower() in EXT_TEXTE:
        try:
            with open(chemin, "rb") as fh:
                return b"\x00" not in fh.read(4096)
        except OSError:
            return False
    return False


def transformer(texte):
    """Remplace le nom hors des lignes marquées LEGACY-GESCOL ; ajoute le nom devant les mentions « Conception » en dur."""
    sortie = []
    for ligne in texte.split("\n"):
        if MARQUE in ligne:
            sortie.append(ligne)
            continue
        for a, b in REMPL:
            ligne = ligne.replace(a, b)
        ligne = re.sub(r"([\"'>])Conception : Maître Aimé FACHE", r"\1SCOLARIS · Conception : Maître Aimé FACHE", ligne)
        sortie.append(ligne)
    return "\n".join(sortie)


def sauvegarder(racine, essai):
    cible = os.path.join(racine, "sauvegarde_avant_scolaris.zip")
    if os.path.exists(cible) or essai:
        return
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for ch in lister(racine):
            if est_texte(ch) and os.path.basename(ch) != "sauvegarde_avant_scolaris.zip":
                z.write(ch, os.path.relpath(ch, racine))
    print("Sauvegarde :", cible)


def remplacer_textes(racine, essai):
    n = 0
    for ch in lister(racine):
        if not est_texte(ch):
            continue
        try:
            with open(ch, "r", encoding="utf-8", newline="") as fh:
                ancien = fh.read()
        except UnicodeDecodeError:
            continue
        nouveau = transformer(ancien)
        if nouveau != ancien:
            n += 1
            if not essai:
                with open(ch, "w", encoding="utf-8", newline="") as fh:
                    fh.write(nouveau)
    print(f"Textes modifiés : {n} fichier(s).")


def renommer_chemins(racine, essai):
    n = 0
    chemins = []
    for dp, dn, fn in os.walk(racine, topdown=False):
        if any(p in IGNORER_DOSSIERS for p in os.path.relpath(dp, racine).split(os.sep)):
            continue
        for nom in fn + dn:
            if re.search(r"gescol", nom, re.I):
                chemins.append((dp, nom))
    for dp, nom in chemins:
        nouveau = nom
        for a, b in REMPL:
            nouveau = nouveau.replace(a, b)
        src, dst = os.path.join(dp, nom), os.path.join(dp, nouveau)
        if not os.path.exists(src):
            continue
        n += 1
        print("  renommé :", os.path.relpath(src, racine), "→", nouveau)
        if not essai:
            if os.path.exists(dst):
                if os.path.isdir(src):
                    for e in os.listdir(src):
                        shutil.move(os.path.join(src, e), os.path.join(dst, e))
                    os.rmdir(src)
                else:
                    os.remove(src)
            else:
                os.rename(src, dst)
    print(f"Fichiers / dossiers renommés : {n}.")


def lire(ch):
    with open(ch, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def ecrire(ch, txt):
    with open(ch, "w", encoding="utf-8", newline="") as fh:
        fh.write(txt)


def patch(racine, rel, fonction, essai):
    ch = os.path.join(racine, rel)
    if not os.path.exists(ch):
        print(f"  (absent, ignoré) {rel}")
        return
    ancien = lire(ch)
    nouveau = fonction(ancien)
    if nouveau != ancien:
        print("  adapté :", rel)
        if not essai:
            ecrire(ch, nouveau)


def logo_dans_modeles(racine, essai):
    img = ('<img class="logo-img" src="{{ url_for(\'static\', filename=\'icons/scolaris-icone.svg\') }}" alt="" '
           'width="34" height="34">')

    def base(t):
        t = t.replace('<span class="logo-g">G</span>', img)
        t = t.replace('<span class="logo-g">S</span>', img)
        if "scolaris-icone.svg" in t and "image/svg+xml" not in t:
            t = re.sub(r'(<link rel="icon" type="image/png"[^>]*>)',
                       lambda m: m.group(1) + '\n<link rel="icon" type="image/svg+xml" href="{{ url_for(\'static\', filename=\'icons/scolaris-icone.svg\') }}">',
                       t, count=1)
        return t

    def login(t):
        if "logo-img" in t or "<h1>SCOLARIS" not in t:
            return t
        grand = img.replace('width="34" height="34"', 'width="72" height="72" style="display:block;margin:0 auto 8px"')
        return t.replace("<h1>SCOLARIS", grand + "\n  <h1>SCOLARIS", 1)

    def css(t):
        return t if ".logo-img" in t else t.rstrip("\n") + "\n.logo-img{border-radius:9px;display:block;flex:none}\n"

    patch(racine, "templates/base.html", base, essai)
    patch(racine, "templates/login.html", login, essai)
    patch(racine, "static/style.css", css, essai)


def compat_ancien_nom(racine, essai):
    """Réutilise les installations GESCOL existantes (variables, dossier de données, base, fichiers .gescol)."""
    def config(t):
        if MARQUE in t:
            return t
        t = t.replace("import os\n", "import os\n\nfor _k, _v in list(os.environ.items()):  # " + MARQUE + " : anciennes variables GESCOL_* encore lues\n"
                      "    if _k.startswith(\"GESCOL_\") and \"SCOLARIS_\" + _k[7:] not in os.environ:  # " + MARQUE + "\n"
                      "        os.environ[\"SCOLARIS_\" + _k[7:]] = _v  # " + MARQUE + "\n", 1)
        t = re.sub(r"( +)return os\.path\.join\(racine, DOSSIERS\.get\(EDITION_IMPOSEE, \"SCOLARIS\"\)\)",
                   lambda m: (f"{m.group(1)}nouveau = os.path.join(racine, DOSSIERS.get(EDITION_IMPOSEE, \"SCOLARIS\"))\n"
                              f"{m.group(1)}ancien = os.path.join(racine, {{\"privee\": \"GESCOL\", \"publique\": \"GESCOL_Public\", \"cs\": \"GESCOL_CS\", \"ddemp\": \"GESCOL_DDEMP\"}}.get(EDITION_IMPOSEE, \"GESCOL\"))  # " + MARQUE + "\n"
                              f"{m.group(1)}return ancien if os.path.isdir(ancien) and not os.path.isdir(nouveau) else nouveau  # " + MARQUE), t, count=1)
        return t

    def db(t):
        if MARQUE in t:
            return t
        return re.sub(r"( +)return os\.path\.join\(current_app\.instance_path, \"scolaris\.db\"\)",
                      lambda m: (f"{m.group(1)}nouveau = os.path.join(current_app.instance_path, \"scolaris.db\")\n"
                                 f"{m.group(1)}ancien = os.path.join(current_app.instance_path, \"gescol.db\")  # " + MARQUE + "\n"
                                 f"{m.group(1)}return ancien if os.path.exists(ancien) and not os.path.exists(nouveau) else nouveau  # " + MARQUE), t, count=1)

    def fmt(t):
        if MARQUE in t:
            return t
        t = t.replace('FORMAT = "scolaris-transmission"', 'FORMAT = "scolaris-transmission"\nFORMATS_ACCEPTES = (FORMAT, "gescol-transmission")  # ' + MARQUE + " : anciens paquets .gescol", 1)
        return t.replace('paquet.get("format") != FORMAT', 'paquet.get("format") not in FORMATS_ACCEPTES', 1)

    def accept(t):
        return t.replace('accept=".scolaris"', 'accept=".scolaris,.gescol"')

    patch(racine, "config.py", config, essai)
    patch(racine, "db.py", db, essai)
    patch(racine, "jur_format.py", fmt, essai)
    for ch in lister(racine):
        if ch.endswith(".html"):
            patch(racine, os.path.relpath(ch, racine), accept, essai)


def icones(racine, essai):
    ici = os.path.dirname(os.path.abspath(__file__))
    for svg in ("scolaris-icone.svg", "scolaris-logo.svg"):
        src = os.path.join(ici, svg)
        if os.path.exists(src):
            print("  logo :", svg)
            if not essai:
                os.makedirs(os.path.join(racine, "static", "icons"), exist_ok=True)
                shutil.copy(src, os.path.join(racine, "static", "icons", svg))
                if svg == "scolaris-logo.svg":
                    os.makedirs(os.path.join(racine, "docs"), exist_ok=True)
                    shutil.copy(src, os.path.join(racine, "docs", svg))
    if not essai:
        sys.path.insert(0, ici)
        import generer_icones
        print(f"  icônes PNG / ICO : {generer_icones.ecrire(racine)} fichier(s)")
        ancienne = os.path.join(racine, "static", "icons", "gescol.ico")
        if os.path.exists(ancienne):
            os.remove(ancienne)


def reste(racine):
    r = []
    for ch in lister(racine):
        if est_texte(ch):
            for i, l in enumerate(lire(ch).split("\n"), 1):
                if re.search("gescol", l, re.I) and MARQUE not in l:
                    r.append(f"{os.path.relpath(ch, racine)}:{i}")
    return r


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    essai = "--essai" in sys.argv
    racine = os.path.abspath(args[0] if args else ".")
    if not os.path.exists(os.path.join(racine, "app.py")):
        sys.exit("app.py introuvable : lancez le script à la racine du projet (ou indiquez le dossier).")
    print(("ESSAI — rien n'est écrit. " if essai else "") + "Racine :", racine)
    sauvegarder(racine, essai)
    remplacer_textes(racine, essai)
    renommer_chemins(racine, essai)
    logo_dans_modeles(racine, essai)
    compat_ancien_nom(racine, essai)
    icones(racine, essai)
    if not essai:
        r = reste(racine)
        print("Occurrences « gescol » restantes (hors compatibilité) :", len(r), r[:10])


if __name__ == "__main__":
    main()
