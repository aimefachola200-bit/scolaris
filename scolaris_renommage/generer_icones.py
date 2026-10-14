# -*- coding: utf-8 -*-
"""Génère les icônes PNG / ICO de SCOLARIS à partir de la géométrie du logo (scolaris-icone.svg), sans dépendance autre que Pillow.
Usage : python generer_icones.py [dossier_projet]     (écrit static/icons/* et les icônes Android si le dossier packaging existe)"""
import os
import sys

from PIL import Image, ImageDraw

VERT_F, JAUNE, ROUGE, VERT = (15, 61, 46), (252, 209, 22), (232, 17, 45), (0, 135, 81)
BLANC, GRIS = (255, 255, 255), (233, 241, 236)


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def dessiner(taille=1024, maskable=False, fond_plein=False):
    """Icône carrée `taille` px (coordonnées du SVG : 512). maskable : motif réduit à 80 % (zone de sécurité Android)
    sur fond plein ; fond_plein : coins non arrondis."""
    S = taille * 2                                   # sur-échantillonnage pour lisser les bords
    k = S / 512
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if maskable or fond_plein:
        d.rectangle([0, 0, S, S], fill=VERT_F)
    else:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(104 * k), fill=VERT_F)
    # motif sur un calque (réduit et centré pour le format maskable)
    echelle, dec = (0.74, 66) if maskable else (1.0, 0)
    P = lambda x, y: ((x * echelle + dec) * k, (y * echelle + dec) * k)
    r = lambda v: v * echelle * k
    cx, cy = P(256, 150)
    d.ellipse([cx - r(58), cy - r(58), cx + r(58), cy + r(58)], fill=JAUNE)
    for (x1, y1, x2, y2) in ((256, 52, 256, 66), (186, 81, 196, 91), (326, 81, 316, 91), (157, 150, 171, 150), (341, 150, 355, 150)):
        a, b = P(x1, y1), P(x2, y2)
        d.line([a, b], fill=JAUNE, width=max(2, int(r(12))))
        for pt in (a, b):
            d.ellipse([pt[0] - r(6), pt[1] - r(6), pt[0] + r(6), pt[1] + r(6)], fill=JAUNE)
    g = bezier((256, 228), (212, 200), (150, 200), (96, 218))
    page_g = [P(*p) for p in g] + [P(96, 380)] + [P(*p) for p in bezier((96, 380), (150, 362), (212, 362), (256, 392))]
    dr = bezier((256, 228), (300, 200), (362, 200), (416, 218))
    page_d = [P(*p) for p in dr] + [P(416, 380)] + [P(*p) for p in bezier((416, 380), (362, 362), (300, 362), (256, 392))]
    d.polygon(page_g, fill=BLANC)
    d.polygon(page_d, fill=GRIS)
    d.line([P(256, 228), P(256, 392)], fill=VERT_F, width=max(2, int(r(8))))
    for sens, (x0, x1) in ((1, (130, 232)), (-1, (382, 280))):
        for dy in (0, 34, 68):
            pts = [P(*p) for p in bezier((x0, 250 + dy), ((170 if sens > 0 else 342), 242 + dy), ((208 if sens > 0 else 304), 246 + dy), (x1, 262 + dy), 24)]
            d.line(pts, fill=(158, 181, 170), width=max(2, int(r(7))))
    # bande tricolore (pleine largeur, en bas ; hors zone de sécurité pour le maskable : remplacée par un liseré)
    if maskable:
        y0, y1 = 430, 448
        for i, c in enumerate((VERT, JAUNE, ROUGE)):
            d.rectangle([P(110 + i * 97, y0)[0], P(0, y0)[1], P(110 + (i + 1) * 97, y1)[0], P(0, y1)[1]], fill=c)
    else:
        for i, c in enumerate((VERT, JAUNE, ROUGE)):
            d.rectangle([i * 171 * k, 424 * k, (i + 1) * 171 * k + 1, S], fill=c)
        if not fond_plein:                            # recoupe les angles arrondis du bas
            masque = Image.new("L", (S, S), 0)
            ImageDraw.Draw(masque).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(104 * k), fill=255)
            alpha = Image.new("L", (S, S), 0)
            alpha.paste(im.split()[3], (0, 0), masque)
            im.putalpha(alpha)
    return im.resize((taille, taille), Image.LANCZOS)


def ecrire(racine):
    ic = os.path.join(racine, "static", "icons")
    os.makedirs(ic, exist_ok=True)
    maitre = dessiner(1024)
    maitre.save(os.path.join(ic, "icon-1024.png"))
    for t in (512, 192):
        maitre.resize((t, t), Image.LANCZOS).save(os.path.join(ic, f"icon-{t}.png"))
    dessiner(512, maskable=True).save(os.path.join(ic, "maskable-512.png"))
    fond = Image.new("RGB", (180, 180), VERT_F)
    fond.paste(dessiner(180, fond_plein=True).convert("RGB"), (0, 0))
    fond.save(os.path.join(ic, "apple-touch-icon.png"))
    maitre.resize((256, 256), Image.LANCZOS).save(os.path.join(ic, "scolaris.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    maitre.resize((32, 32), Image.LANCZOS).save(os.path.join(ic, "favicon-32.png"))
    n = 5
    for dossier, taille in (("mipmap-mdpi", 48), ("mipmap-hdpi", 72), ("mipmap-xhdpi", 96), ("mipmap-xxhdpi", 144), ("mipmap-xxxhdpi", 192)):
        for proj in ("android", "android_autonome"):
            d = os.path.join(racine, "packaging", proj, "app", "src", "main", "res", dossier)
            if os.path.isdir(d):
                maitre.resize((taille, taille), Image.LANCZOS).save(os.path.join(d, "ic_launcher.png"))
                n += 1
    return n


if __name__ == "__main__":
    print(f"{ecrire(sys.argv[1] if len(sys.argv) > 1 else '.')} icône(s) écrite(s).")
