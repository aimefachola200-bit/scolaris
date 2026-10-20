# -*- coding: utf-8 -*-
"""Application CP (MEMP — République du Bénin) pour Windows.

L'application web est embarquée (dossier « www ») et servie sur l'ordinateur lui-même (http://127.0.0.1:PORT) ;
elle s'ouvre dans une fenêtre d'application de Microsoft Edge (ou Chrome), avec un profil propre à MEMP CP :
les données restent sur le PC et fonctionnent sans Internet. Conception : Maître Aimé FACHE."""
import functools
import json
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WWW = os.path.join(BASE, "www")
try:
    with open(os.path.join(BASE, "variante.json"), encoding="utf-8") as f:
        VARIANTE = json.load(f)
except OSError:
    VARIANTE = {}
NOM = VARIANTE.get("nom", "MEMP CP")
PORT = int(VARIANTE.get("port", 8871))
DONNEES = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), NOM.replace(" ", "_"))


class Gestion(SimpleHTTPRequestHandler):
    extensions_map = dict(SimpleHTTPRequestHandler.extensions_map, **{
        ".js": "text/javascript", ".mjs": "text/javascript", ".webmanifest": "application/manifest+json",
        ".json": "application/json", ".svg": "image/svg+xml", ".wasm": "application/wasm"})

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, *args):
        pass


def port_libre(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def navigateur():
    """Edge ou Chrome (mode application) ; None si aucun n'est trouvé."""
    candidats = []
    for racine in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"), os.environ.get("LOCALAPPDATA")):
        if racine:
            candidats += [os.path.join(racine, "Microsoft", "Edge", "Application", "msedge.exe"),
                          os.path.join(racine, "Google", "Chrome", "Application", "chrome.exe")]
    return next((c for c in candidats if os.path.exists(c)), None)


def main():
    adresse = f"http://127.0.0.1:{PORT}/index.html"
    serveur = None
    if port_libre(PORT):
        serveur = ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Gestion, directory=WWW))
        threading.Thread(target=serveur.serve_forever, daemon=True).start()
    exe = navigateur()
    if not exe:
        webbrowser.open(adresse)
        if serveur:   # navigateur ordinaire : le serveur reste actif tant que le programme tourne
            while True:
                time.sleep(3600)
        return
    os.makedirs(DONNEES, exist_ok=True)
    p = subprocess.Popen([exe, f"--app={adresse}", f"--user-data-dir={os.path.join(DONNEES, 'navigateur')}",
                          "--no-first-run", "--no-default-browser-check", "--disable-features=Translate"])
    if serveur:
        p.wait()                 # fenêtre (profil MEMP CP) fermée : on arrête le serveur
        serveur.shutdown()


if __name__ == "__main__":
    main()
