# -*- coding: utf-8 -*-
"""v1.32 — « Guide d'utilisation » (LISEZ-MOI) de SCOLARIS : rubriques par rôle (administrateur, directeur, enseignant,
conseiller pédagogique, circonscription, DDEMP), premiers pas, chaque module en quelques étapes, sauvegarde, hors ligne,
impression, codes QR, questions fréquentes. Même plan que le guide des applications web (outils/lots/guide-contenus.mjs).

Trois sorties du même contenu : page de l'application (/aide/guide, avec recherche), PDF « LISEZ-MOI » (Times New Roman
14 pt) et fichier LISEZMOI.md (python3 guide_utilisation.py, depuis le dossier de l'application).
"""
import io
import os

ROLES = [("tous", "Tout le monde"), ("admin", "Administrateur / fondateur"), ("directeur", "Directeur / directrice"),
         ("enseignant", "Enseignant(e)"), ("cp", "Conseiller pédagogique"), ("cs", "Circonscription scolaire"), ("ddemp", "DDEMP")]
CONTACT = "Maître Aimé FACHOLA, +229 01 96 51 03 33 (appel ou WhatsApp)"

SECTIONS = [
    {"id": "premiers-pas", "titre": "Premiers pas", "roles": ["tous"],
     "intro": "{appli} gère l'école au quotidien : élèves, présences, notes et bulletins, préparation de classe, examens, "
              "personnel, sport scolaire (UASCEP), santé, cantine, patrimoine et documents officiels vérifiables.",
     "etapes": ["Ouvrez l'application et connectez-vous avec l'identifiant et le mot de passe reçus (au premier démarrage : admin / admin123, à changer aussitôt).",
                "Saisissez une fois le code d'accès personnel demandé (page « Code d'accès », demande par WhatsApp au concepteur).",
                "Remplissez la fiche de l'école : nom, circonscription, directeur, cachet, signature, devise et logo.",
                "Créez les classes (niveau CI à CM2, titulaire), puis les comptes des enseignants dans « Utilisateurs ».",
                "Inscrivez les élèves (un par un, ou par importation Excel / EducMaster)."],
     "conseils": ["Le menu à gauche (ou le bouton « Menu » sur téléphone) donne accès à tous les modules autorisés pour votre compte.",
                  "Les tableaux gardent leur ligne d'en-tête visible quand vous faites défiler la page."]},
    {"id": "ecole", "titre": "Fiche de l'école, logo et devise", "roles": ["admin", "directeur"],
     "etapes": ["Menu « Écoles » puis « Modifier » sur votre école.",
                "Écrivez la devise (ou choisissez-en une dans la liste : « Travail – Discipline – Réussite »…).",
                "Dans « Logo », choisissez « Créer le logo automatiquement », puis la forme (rond ou écusson), le symbole (livre, plume, soleil, épi, palmier, colombe, globe…), les initiales et les couleurs ; l'aperçu se met à jour.",
                "Ou importez votre propre logo (PNG ou JPG). « Pas de logo » le retire.",
                "Réglez le cachet et la griffe, ajoutez les signatures du directeur et de l'administrateur, puis « Enregistrer »."],
     "conseils": ["Le logo et la devise figurent en tête des documents de l'école (bulletins, certificats, listes, fiches).",
                  "Les liens « Télécharger le logo automatique (SVG / PNG) » donnent le logo en fichier pour d'autres usages."]},
    {"id": "eleves", "titre": "Élèves, classes et présences", "roles": ["admin", "directeur", "enseignant"],
     "etapes": ["« Élèves » : inscrire, modifier, transférer ; « Importer » pour une liste Excel ou EducMaster.",
                "« Faire l'appel » chaque demi-journée ; les absences alimentent le registre de présence et les alertes de décrochage.",
                "« Registre de présence » et « Relevés mensuels » s'impriment en PDF signé avec code QR."],
     "conseils": ["L'enseignant ne voit que ses classes ; le directeur voit toute l'école."]},
    {"id": "notes", "titre": "Évaluations, notes et bulletins", "roles": ["admin", "directeur", "enseignant"],
     "etapes": ["« Saisie des notes » : choisissez la classe, la période et la matière, saisissez puis enregistrez.",
                "« Statistiques » et « Analyse et rapport » : moyennes, taux de réussite, courbes, comparaison des classes.",
                "« Notes par période (bulletins) » : bulletins individuels et listes, signés avec code QR.",
                "« Bilan annuel et décision » : passage, redoublement, tableau d'honneur."]},
    {"id": "preparation", "titre": "Préparation de classe : fiches, résumés, épreuves", "roles": ["enseignant", "directeur", "cp", "admin"],
     "etapes": ["« Cette semaine » : pour chaque classe, les fiches de la semaine d'après la planification ; « Voir les fiches » ou « Fiches de la semaine (PDF) ».",
                "« Fiches de préparation (bibliothèque) » : filtrez par cours, matière, SA et séance ; ouvrez une fiche, puis PDF, Word ou « Adapter pour ma classe ».",
                "« Préparer une fiche » : partez d'une fiche du corpus ou d'une fiche vierge, complétez, enregistrez (« Mes fiches »).",
                "« Résumés » : l'essentiel de chaque séance, version enseignant ou version élève ; cahiers de résumés par cours et matière.",
                "« Évaluations et épreuves » : sujets et corrigés (mensuelles, trimestrielles, passage, CEP blancs), onglet « Modifier » pour adapter un sujet.",
                "« Planification et classeurs » : vues jour, semaine, mois ; classeur des fiches à imprimer."],
     "conseils": ["La fiche imprimée porte le nom du titulaire de la classe en filigrane oblique : renseignez le titulaire dans la fiche de la classe.",
                  "Les fiches longues sont prévues pour le recto verso : choisissez « recto verso » dans les réglages de l'imprimante ; chaque page est numérotée « Page x / y ».",
                  "Les contenus conçus selon l'APC portent la mention « à valider par le conseiller pédagogique »."]},
    {"id": "examens", "titre": "CEP, examen blanc et concours", "roles": ["admin", "directeur", "enseignant", "cs"],
     "etapes": ["« Session CEP » : candidats, centres, jurys, numéros de table.",
                "« Saisie des notes » puis « Délibération et résultats » : statistiques par école et par sexe, PV, listes, relevés.",
                "« Examen blanc du CEP » : neuf épreuves, seuil de six maîtrises sur neuf (six sur huit pour un dispensé d'EPS), classement et recommandations.",
                "« Révisions d'éveil » (CM1, CM2) : cahiers de révision et sujets type CEP avec corrigé et barème."]},
    {"id": "uascep", "titre": "Bureaux UASCEP et sport scolaire", "roles": ["tous"],
     "etapes": ["« Bureaux UASCEP », onglet « Ajouter un membre » : niveau (école, UP, zone, CS, DDEMP), entité, puis les renseignements du membre ; le bureau se crée avec le premier membre.",
                "Pour chaque responsable : signature (dessinée ou importée) et cachet (généré ou importé).",
                "Onglet « Documents » : composition du bureau, PV d'élection et d'installation, attestations, liste des bureaux, signés avec code QR.",
                "Onglet « Vie du bureau » : activités, réunions (rapporteur), caisse et budget (trésorier), matériel, rapport de fin de saison.",
                "« Sport scolaire » : licences, compétitions, feuilles de match, classements, palmarès, records et diplômes."]},
    {"id": "suivi", "titre": "Santé, cantine, communication, inspection, patrimoine", "roles": ["admin", "directeur", "cp", "cs", "ddemp"],
     "etapes": ["Santé : visites médicales (aptitude sportive), infirmerie, élèves à besoins spécifiques, scolarisation des filles, décrochage.",
                "Cantine : journal des repas et stocks (alerte de rupture).",
                "Communication : notes de service, circulaires et convocations avec accusé de lecture, échéances, messages aux parents, agenda.",
                "Inspection et formation : visites de classe (grille APC), suivi des recommandations, plans de formation, animations pédagogiques.",
                "Patrimoine : bâtiments, tables-bancs, manuels, matériel, besoins et dotations."]},
    {"id": "pilotage", "titre": "Tableau de bord du pilotage", "roles": ["admin", "directeur", "cp", "cs", "ddemp"],
     "etapes": ["Menu « Tableau de bord du pilotage » : effectifs, ratios élèves / maître et élèves / classe, réussite, CEP, abandons, personnel, sport.",
                "Choisissez le niveau et l'année ; comparez les entités et les années ; exportez en PDF ou Excel."]},
    {"id": "juridiction", "titre": "Circonscription (CS) et DDEMP", "roles": ["cs", "ddemp", "cp"],
     "etapes": ["Au premier démarrage, renseignez la structure (circonscription ou direction départementale), ses zones et UP, ses services.",
                "Ajoutez les écoles de la juridiction ou importez leurs données transmises (Excel, transmission).",
                "Les tableaux de synthèse, statistiques et documents se calculent à partir des écoles."]},
    {"id": "impression", "titre": "Imprimer et enregistrer en PDF", "roles": ["tous"],
     "etapes": ["Ouvrez le document puis « PDF » : le fichier s'ouvre ou se télécharge ; imprimez-le ou partagez-le.",
                "Pour les fiches longues, imprimez en recto verso.",
                "Une épreuve courte s'imprime deux fois par feuille A4 avec une ligne de coupe."]},
    {"id": "verification", "titre": "Code QR et vérification des documents", "roles": ["tous"],
     "etapes": ["Les documents officiels portent un code de vérification et un code QR.",
                "Scannez le code QR avec un téléphone, ou ouvrez « Vérifier un document » et saisissez le code.",
                "La page indique si le document est authentique et à quoi il correspond."]},
    {"id": "sauvegarde", "titre": "Sauvegarde, restauration et transmission", "roles": ["admin", "directeur"],
     "etapes": ["Menu « Données » : « Sauvegarder » télécharge une archive (base, photos, logo, cachet, signatures).",
                "Gardez la sauvegarde hors de l'appareil (clé USB, ordinateur, envoi à soi-même).",
                "« Restaurer » remet une sauvegarde en place (après confirmation).",
                "« Transmettre » envoie les données attendues à la circonscription."],
     "conseils": ["Sauvegardez au moins une fois par semaine et toujours avant une mise à jour ou un changement d'appareil."]},
    {"id": "hors-ligne", "titre": "Hors ligne, téléphone et tablette", "roles": ["tous"],
     "etapes": ["Les applications Android autonomes (SCOLARIS, Public, Enseignant…) fonctionnent sans internet ni ordinateur : installez-les avec le code QR de la fiche d'installation.",
                "Sur ordinateur, l'application Windows sert aussi les téléphones du même réseau Wi-Fi (adresse affichée au démarrage).",
                "Sur téléphone, les listes de choix s'ouvrent en plein écran avec une recherche."]},
]
FAQ = [
    ("Une page affiche « Une erreur est survenue ».", "Touchez « Envoyer le rapport par WhatsApp » : le concepteur reçoit le détail. Mettez l'application à jour (dernière version)."),
    ("La préparation de classe ne s'ouvre pas.", "Installez la version 1.31.1 ou plus récente, qui corrige l'ouverture des fiches depuis une classe."),
    ("Je ne retrouve pas mes données sur un autre appareil.", "Chaque appareil a ses données : faites une sauvegarde sur le premier, restaurez-la sur le second."),
    ("Le logo n'apparaît pas sur les documents.", "Fiche de l'école : choisissez « Créer le logo automatiquement » ou importez un logo, puis « Enregistrer »."),
    ("J'ai oublié mon mot de passe.", "Sur l'écran de connexion, « Mot de passe oublié » : l'administrateur ou le directeur reçoit la demande et vous donne un nouveau mot de passe."),
    ("Qui contacter ?", "Le concepteur : " + CONTACT + "."),
]


def sections_pour(role=None):
    if not role or role == "tous":
        return SECTIONS
    return [s for s in SECTIONS if "tous" in s["roles"] or role in s["roles"]]


def texte(t, appli):
    return t.replace("{appli}", appli)


def markdown(appli="SCOLARIS", version=""):
    out = [f"# {appli} — Guide d'utilisation (LISEZ-MOI)", "",
           f"Version {version}. " if version else "",
           "Ce guide explique, en quelques étapes simples, comment utiliser chaque partie de l'application. "
           "Chaque rubrique indique pour qui elle est utile.", ""]
    lib = dict(ROLES)
    for s in SECTIONS:
        out += [f"## {s['titre']}", "", "*Pour : " + ", ".join(lib[r] for r in s["roles"]) + "*", ""]
        if s.get("intro"):
            out += [texte(s["intro"], appli), ""]
        out += [f"{i}. {texte(e, appli)}" for i, e in enumerate(s["etapes"], 1)] + [""]
        for c in s.get("conseils") or []:
            out.append(f"- Conseil : {texte(c, appli)}")
        if s.get("conseils"):
            out.append("")
    out += ["## Questions fréquentes et dépannage", ""]
    for qq, r in FAQ:
        out += [f"**{qq}**", "", r, ""]
    out += ["---", "", f"Conception : {CONTACT}", ""]
    return "\n".join(x for x in out if x is not None)


def pdf(appli="SCOLARIS", version="", role=None):
    """PDF « LISEZ-MOI » (Times New Roman 14 pt, titres en couleur)."""
    import pdfs
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape
    S = pdfs.police_serif()
    bleu = colors.HexColor("#1F4E79")
    st = {"t": ParagraphStyle("t", fontName=S["gras"], fontSize=20, leading=24, textColor=bleu, alignment=1, spaceAfter=6),
          "s": ParagraphStyle("s", fontName=S["normal"], fontSize=13, leading=17, alignment=1, spaceAfter=10),
          "h": ParagraphStyle("h", fontName=S["gras"], fontSize=16, leading=20, textColor=bleu, spaceBefore=10, spaceAfter=4),
          "r": ParagraphStyle("r", fontName=S["italique"], fontSize=11, leading=14, textColor=colors.HexColor("#475467"), spaceAfter=4),
          "p": ParagraphStyle("p", fontName=S["normal"], fontSize=14, leading=18, spaceAfter=4),
          "e": ParagraphStyle("e", fontName=S["normal"], fontSize=14, leading=18, leftIndent=16, bulletIndent=2, spaceAfter=3),
          "c": ParagraphStyle("c", fontName=S["italique"], fontSize=13, leading=17, leftIndent=16, textColor=colors.HexColor("#067647"), spaceAfter=3)}
    lib = dict(ROLES)
    h = [Paragraph(escape(f"{appli} — Guide d'utilisation"), st["t"]),
         Paragraph(escape(("Version " + version + " · ") if version else "") + "LISEZ-MOI" + (f" · {lib.get(role, '')}" if role and role != "tous" else ""), st["s"])]
    for s in sections_pour(role):
        bloc = [Paragraph(escape(s["titre"]), st["h"]), Paragraph(escape("Pour : " + ", ".join(lib[r] for r in s["roles"])), st["r"])]
        if s.get("intro"):
            bloc.append(Paragraph(escape(texte(s["intro"], appli)), st["p"]))
        h.append(KeepTogether(bloc + [Paragraph(escape(texte(s["etapes"][0], appli)), st["e"], bulletText="1.")]))
        h += [Paragraph(escape(texte(e, appli)), st["e"], bulletText=f"{i}.") for i, e in enumerate(s["etapes"][1:], 2)]
        h += [Paragraph(escape("Conseil : " + texte(c, appli)), st["c"]) for c in s.get("conseils") or []]
    h.append(Paragraph("Questions fréquentes et dépannage", st["h"]))
    for qq, r in FAQ:
        h.append(KeepTogether([Paragraph("<b>" + escape(qq) + "</b>", st["p"]), Paragraph(escape(r), st["e"])]))
    h += [Spacer(1, 8), Paragraph(escape("Conception : " + CONTACT), st["r"])]
    buf = io.BytesIO()

    def pied(c, doc):
        c.saveState()
        c.setFont(S["normal"], 9)
        c.setFillColor(colors.HexColor("#667085"))
        c.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {doc.page}")
        c.restoreState()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                      title=f"{appli} — Guide d'utilisation", author="SCOLARIS").build(h, onFirstPage=pied, onLaterPages=pied,
                                                                                       canvasmaker=pdfs.GCanvasPeda)
    return buf.getvalue()


def enregistrer(app, H):
    from flask import render_template, request

    @app.route("/aide/guide")
    @H.connexion_requise()
    def guide_utilisation():
        role = request.args.get("role") or ""
        return render_template("guide_utilisation.html", sections=sections_pour(role), faq=FAQ, roles=ROLES, role=role,
                               lib=dict(ROLES), texte=texte)

    @app.route("/aide/lisez-moi.pdf")
    @H.connexion_requise()
    def guide_pdf():
        import config
        return H.pdf_reponse(pdf(config.NOMS_APPLI.get(config.EDITION, "SCOLARIS") if hasattr(config, "NOMS_APPLI") else "SCOLARIS",
                                 config.VERSION, request.args.get("role")), "LISEZ-MOI.pdf")


if __name__ == "__main__":
    import config
    ici = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(ici, "LISEZMOI.md"), "w", encoding="utf-8") as f:
        f.write(markdown(config.NOMS_APPLI.get("privee", "SCOLARIS") if hasattr(config, "NOMS_APPLI") else "SCOLARIS", config.VERSION))
    print("LISEZMOI.md écrit")
