![SCOLARIS](docs/scolaris-banniere-github.png)

# SCOLARIS – Gestion d'établissement scolaire (CPFA)

> **Installer sur PC, Android ou tablette : voir [INSTALLATION.md](INSTALLATION.md).**
> **Mettre en ligne (accessible partout par Internet) : voir [EN_LIGNE.md](EN_LIGNE.md).**
> Ce README décrit le fonctionnement et le lancement en mode développement.

Application web Python (Flask + SQLite) utilisable sur le réseau de l'école.
Modules : élèves et inscriptions, classes, saisie des notes et bulletins,
paiements et reçus, documents officiels avec QR code de vérification.

## Nouveautés de la version 1.10 (1.10.1)

- **Tableau de bord CS / DDEMP — programmation et bilan des activités pédagogiques** : pour le trimestre choisi
  (ou le bilan annuel), les **chefs de circonscription (CCS) en premier**, puis les **conseillers pédagogiques** en
  second plan : réalisé / programmé et taux de réalisation (visites de classes et d'écoles, suivis de directeurs,
  séances d'UP, formations, concertations). À la DDEMP : bilan transmis par chaque CS, sinon calcul sur les données reçues.
- **Module « Effectifs »** (Statistiques) : apprenants EP / EM (fiche de recensement), enseignants et directeurs,
  catégories FE, ACDPE, ACDPCTD (AME), Éducateur, Privé, titulaires du CAP (EP, EM) et du CEAP (EP, EM), par sexe ;
  **diplômes académiques et universitaires** (CEP, BEPC, BAC, BAC + 2, Licence, Maîtrise, Master / DEA / DESS,
  Doctorat) ; le **secteur privé à part** (v1.10.2) : les rubriques 1 à 5 ne comptent que le public, et une
  rubrique propre au privé donne écoles, apprenants, enseignants, directeurs, CAP / CEAP des écoles privées ;
  les **catégories d'âge** des apprenants du primaire (v1.10.3), de « moins de 5 ans » à « 16 ans et plus »,
  par sexe et par cours (CI … CM2), avec pourcentages, âge moyen et écart type (public, et privé à part) ;
  les **écoles maternelles par section** (v1.10.4), section des petits (SP) et des grands (SG), par sexe : tableau 3
  de la fiche de recensement (catégories d'âge, pourcentages, âge moyen, écart type), rapport de rentrée EM et fiche
  de fin d'année EM (début, fin, besoin spécifique, abandons), public et privé à part ;
  par circonscription (DDEMP), par zone pédagogique (CS) ou par école ; une **courbe** par tableau ; Excel.
  Rattaché aux divisions des statistiques / de l'organisation scolaire et des ressources humaines.
- **Évaluations, planification et classeurs** (v1.21.0) : dans « Préparation de classe », banque de 359 épreuves APC 2026-2027 (sujet, corrigé type et grille de correction) suivant l'organigramme des épreuves de l'INFRE — évaluations mensuelles (octobre, novembre, janvier, février, avril, mai : 30 par cours), sommatives trimestrielles (21 par cours), de fin d'année / passage (CI → CM1) et 3 examens blancs du CEP (CM2) ; 32 épreuves reformulées d'après les épreuves standardisées INFRE (CE1 → CM2), les autres créées d'après la progression de la planification annuelle ; modification et régénération d'après la planification de l'école, PDF et Word (sujet, corrigé, grille), « créer l'évaluation » pour la saisie des notes ; planification journalière, hebdomadaire et mensuelle de chaque classe (emploi du temps × planification mensuelle × fiches, cases modifiables, PDF / Excel) ; classeurs des fiches du jour, de la semaine ou du mois (PDF avec sommaire, Word, zip).
- **Communication et alertes ; santé, cantine et inclusion** (v1.26.0) : notes de service, circulaires et convocations diffusées aux écoles (ou reçues par Excel), boîte de réception et accusés de réception, note signée et état des accusés (QR), échéances et rappels, agenda partagé, messages aux parents (WhatsApp, SMS, copie), page d'alertes (échéances, notes non lues, convocations, décrochage, licences, stocks) ; visites médicales (IMC, aptitude reportée sur les licences, certificat d'aptitude et fiche signés), infirmerie et incidents, cantine (journal des repas, stocks et soldes), élèves à besoins spécifiques, scolarisation des filles, absences de l'appel et fiches de décrochage ; Excel commun (Niveau · Entité · Saison, mise à jour par clé d'unicité).
- **Sport scolaire, pilotage, logo UASCEP, résumés et icônes au trait** (v1.25.0) : sport scolaire complet (licences avec catégorie et aptitude, compétitions de l'école à la DDEMP en poules, élimination ou championnat, tirage, calendrier, feuilles de match, classements automatiques avec départage, athlétisme et records, jeux traditionnels, palmarès, qualifiés, diplômes signés avec QR, résultats versés à la saison UASCEP) ; tableau de bord du pilotage (effectifs G/F, ratios, évaluations, CEP, abandons, personnel, infrastructures, sport ; filtres, comparaisons, PDF/Excel) ; logo UASCEP modifiable avec la définition du sigle, en tête des documents UASCEP et sur les diplômes ; classeur Excel UASCEP aligné sur le modèle commun, cachets vert et noir ; résumés de Français classés par outils de la langue et de Mathématiques par domaine, rattachés aux dossiers, SA et séances et placés dans la progression annuelle (623 résumés) ; plus aucun émoji : icônes au trait communes aux applications.
- **Cachets, signatures et rapport de saison de l'UASCEP** (v1.24.0) : cachet de chaque responsable à tous les niveaux (école, UP, zone, CS, DDEMP) — généré rond « UASCEP » + niveau + entité autour et fonction au centre, griffe rectangulaire ou image importée, couleur — et signature digitale (dessinée ou importée), aperçu, réinitialisation ; documents signés avec cachets, visa de l'autorité hiérarchique, code de vérification et QR : composition du bureau, PV d'élection et d'installation, attestation de fonction, liste des bureaux ; vie du bureau par saison : calendrier, activités et résultats, fiches d'engagement, réunions et comptes rendus (rapporteur), journal de caisse, cotisations par école, budget prévu / réalisé et état financier (trésorier, visa du commissaire aux comptes), inventaire du matériel ; **rapport de fin de saison sportive** pré-rempli et modifiable (PDF signé par le rapporteur, le secrétaire général, le trésorier et le président, Excel).
- **Résumés pour chaque cours et chaque matière** (v1.23.0) : dans « Préparation de classe », 168 nouveaux résumés « l'essentiel à retenir » (303 au total) pour le CI, le CP, le CE1, le CE2, le CM1 et le CM2 en Français (par sous-matière : sons, lettres, syllabes, lecture, écriture, communication orale au CI / CP ; grammaire, conjugaison, orthographe, vocabulaire, lecture, expression écrite du CE1 au CM2), Mathématiques, Éducation sociale (faits vérifiés le 27/10/2026), EST (une par SA), EPS et Éducation artistique — règle, méthode, exemple, 3 exercices corrigés, version élève ; rattachés aux SA / unités : tableau cours × matière dans l'onglet Résumés et « Résumés de la semaine » à côté des fiches dans la planification. Résumés conçus selon le programme — à valider par le conseiller pédagogique.
- **Bureaux de l'UASCEP** (v1.22.0) : membres et responsables par école, unité pédagogique, zone pédagogique, circonscription scolaire et DDEMP — onglets par niveau, synthèse et anciens bureaux ; ajouter, modifier, supprimer, réinitialiser (avec archivage) et renouveler le bureau ; rubriques n° d'ordre, nom et prénoms, sexe, école, UP, zone, nom du RUP, fonction, qualité, contact, date d'élection, date de fin de mandat (calculée selon la durée), statut du mandat, observations ; UP, zones et RUP repris de la structure ; PDF avec signatures, Excel commun aux applications (export / modèle / import). Éditions école : bureau de l'école (UP et zone en lecture) ; CS : écoles, UP, zones et CS ; DDEMP : tous niveaux ; enseignant : lecture seule.
- **Lot 3 — inventaires CI / CP / CE2 / CM2, guides officiels CM1, Éducation sociale actualisée** (v1.20.0) : recueils de référence utilisés pour la structure seulement (docs/inventaire_fiches.md) ; 1 867 fiches APC conçues pour les séances absentes (CI 810, CP 621, CE2 227, CM2 209 — mention « Conçue selon l'APC — à valider par le conseiller pédagogique »), intrus et doublons internes écartés et listés ; 31 fiches d'EST CM2 transmises par la CS importées (14 fiches de même objet remplacées, fusions dans « Doublons ») ; guides officiels CM1 (Français, Mathématiques, EPS, EST : orientations par OCR, planification des SA) et fiches d'EPS CM1 réalignées ; 30 titres de SA d'ES / EPS ajoutés aux programmes ; Éducation sociale actualisée au 27/10/2026 (Constitution révisée en 2025, président Wadagni, 109 députés élus en janvier 2026, Sénat installé en juillet 2026 — sources citées) : 19 fiches corrigées, 19 résumés « Éducation sociale » CE1 → CM2, guide « Repères d'actualité institutionnelle du Bénin ».
- **Inventaire CM1 et résumés** (v1.19.0) : inventaire des séances CM1 d'un recueil de référence comparé à la bibliothèque (docs/inventaire_fiches.md) ; 233 fiches APC CM1 conçues pour les séances absentes (Français 25, Éducation sociale 96, EPS 2, Éducation artistique 110 : phases introduction / réalisation / retour et projection, activités de l'enseignant et des apprenants, résultats attendus, évaluation), rattachées aux SA / unités / semaines pour « Cette semaine » et portant la mention « Conçue selon l'APC — à valider par le conseiller pédagogique » ; nouvel onglet « Résumés — l'essentiel à retenir » : 116 résumés originaux (Mathématiques CE1 → CM2, Français CM1, révision CEP Français / Mathématiques / ES / EST) avec règle, méthode, exemple et 3 exercices corrigés, version enseignant et version élève imprimable, PDF à l'unité ou par lot ; état de l'inventaire CM1 dans « Fiches et guides manquants ». Lot 2 : 56 fiches de mathématiques CE1 / CM2 transmises par la CS importées (une par séquence, auteur conservé) après dédoublonnage (doublons listés) ; 138 fiches conçues d'après les recueils de référence (Mathématiques CE1, Français CE1, CE2 unité 12, Éducation artistique) ; guide officiel de Mathématiques CP (MEMP, 2022) dans « Guides pédagogiques » avec sa progression et 140 fiches CP (une par jour, texte relevé par OCR à relire).
- **Préparation de classe** (v1.18.0) : menu « Préparation de classe » dans les éditions école privée et école publique (application de l'école, portail /enseignant) et dans SCOLARIS Enseignant — « Cette semaine » d'après la planification mensuelle de la classe (ou annuelle du cours), programmes et progressions par cours et matière, guides pédagogiques (lecture et PDF), bibliothèque de 1 072 fiches de préparation APC (CI → CM2, maternelle) filtrable par cours, matière, sous-matière, SA, séance et semaine, PDF A4 au format APC signé et vérifiable, Word ; « Préparer une fiche » (vierge, d'après un modèle ou en adaptant une fiche) pour SES classes ; « fiches de la semaine » en un PDF ; le directeur consulte les fiches des enseignants. Fiches et guides manquants recensés (docs/fiches_et_guides_manquants.md) ; ceux conçus pour les combler portent la mention « Conçue selon l'APC — à valider par le conseiller pédagogique ». Sur téléphone, les listes de suggestions et longues listes déroulantes s'ouvrent dans un panneau de recherche au-dessus du clavier.
- **En-têtes fixes** (v1.17.0) : dans tous les tableaux, la ligne des rubriques reste visible pendant le défilement (sous la barre du haut et les barres d'outils collées), les grands tableaux défilent dans leur cadre avec la 1re colonne fixe quand ils débordent sur les côtés ; les titres de section des longs formulaires (fiches, rapports) restent visibles, l'en-tête du tableau se place dessous.
- **Registre d'appel et départements servis** (v1.16.0) : les absences prises par « Faire l'appel » entrent au registre (toutes les demi-journées du jour), une seule fois — une case corrigée dans le registre reste corrigée, un élève remis présent à l'appel en sort ; relevés et PDF les comptent. « Département(s) servi(s) » : plusieurs départements à cocher (fiche de carrière, personnel de la juridiction), import Excel « Atacora, Donga ».
- **Documents vérifiables** (v1.15.0) : registre de présence, relevés mensuels, tableau d'affichage, statistiques
  de présence (nouveau PDF avec courbe mensuelle), statistiques et résultats d'évaluation, synthèse, bilan annuel,
  tableau d'honneur et tous les documents en tableau signés portent un **code de vérification et un QR** (page
  `/verifier` : type, objet, date, auteur) à côté des signatures (titulaire, directeur + cachet). **EducMaster** :
  import du modèle officiel de notes rempli (4 feuilles, élève retrouvé par matricule EducMaster puis nom ; simulation ;
  évaluations manquantes créées) en plus de l'export rempli et de l'import des élèves par classe.
- **SCOLARIS Enseignant** (v1.14.0) : application personnelle de l'enseignant (SCOLARIS-Enseignant.apk,
  SCOLARIS-Enseignant-Installation.exe), sans passer par l'application de l'école. Premier lancement : son profil
  (NIP, matricule, grade, catégorie, dates de prise de service, diplômes), son école (secteur, CS, DDEMP, directeur)
  et ses classes ; menu réduit à son périmètre : ma classe (élèves ajoutés ou importés par lui, appel, notes,
  bulletins), emplois du temps, planifications annuelle et mensuelle, calendrier officiel, règlement intérieur,
  thèmes d'UP, documents officiels et « Mes certificats » (PDF pré-remplis), ma carrière, mon compte. Dans les
  applications d'école, portail `/enseignant` « SCOLARIS Enseignant » (installable) avec le même menu sur les données
  de l'école et le même périmètre. **Corrections** (v1.13) : modifier / supprimer un paiement ou une opération de
  caisse, réinitialiser les paiements d'un élève ou la contribution de cantine d'une classe.
- **Retour, mot de passe oublié** (v1.12.0) : bouton « ← Retour » (page précédente) et « 🏠 Accueil » en haut de chaque
  page ; lien « Mot de passe oublié ? » à la connexion : question de secours (définie dans « Mon compte ») pour choisir
  soi-même un nouveau mot de passe, ou demande à l'administrateur (Utilisateurs → « Mot de passe provisoire »), avec
  message WhatsApp à l'école ; œil 👁 pour afficher le mot de passe sur tous les champs.
- **Saisie manuelle sans Excel** (v1.11.0, CS et DDEMP) : nouvel onglet « Saisie manuelle (sans Excel) » : pour chaque
  école, les six fiches officielles (recensement primaire et maternelle, rentrée et fin d'année EP et EM) se remplissent
  à la main dans le formulaire officiel (mêmes calculs, mêmes contrôles, même PDF) ; état nominatif du personnel
  (directeur, adjoints, enseignants, administratifs, agents de soutien) saisi ligne par ligne, repris dans la gestion de
  carrière ; noms et téléphones des directeurs de toutes les écoles dans un seul tableau.
- **Caméra avant / arrière fiable** (v1.10.10) : le bouton « Basculer » choisit l'appareil d'après son nom (avant /
  arrière), sinon le suivant ; face imposée puis préférée : la bascule marche aussi sur les téléphones qui ignoraient
  la demande et rouvraient toujours la même caméra (photos des élèves, prise de photos de classe, signatures…).
- **Correctif PC (v1.10.9)** : l'installateur Windows embarque désormais TOUS les modules (la liste manuelle oubliait
  ceux ajoutés depuis la 1.8 : page d'accueil en « Internal Server Error » sur PC) ; dernier filet d'erreurs : toute
  erreur, même hors des pages, affiche la page d'erreur en français.
- **Erreurs et diagnostic** (v1.10.8) : en cas d'erreur interne, une page en français remplace « Internal Server
  Error » : version, page, nature de l'erreur, bouton d'envoi du rapport au concepteur par WhatsApp ; rapport complet
  dans erreurs.log (dossier des données) ; page /diagnostic (version, édition, contrôle de la base, dernières erreurs).
  Android : le cache de l'écran est vidé après chaque mise à jour (plus d'anciennes pages de la version précédente).
- **CEP : candidats et réussite selon les fiches** (v1.10.7, Examens) : rubrique 9 de la fiche de recensement (CEP,
  CEP Vie active, Ensemble, dont enfants handicapés × inscrits / ont composé / admis), annexe CEP de la fiche de fin
  d'année ou module CEP ; candidats par sexe et pourcentage, parité filles / garçons, taux de présence, taux de
  réussite par sexe, écart filles − garçons, moyenne et écart type des taux des écoles ; par CS, zone ou école ;
  public et privé à part ; graphiques au choix ; Excel.
- **Rubriques des fiches consolidées** (v1.10.6, Fiches des écoles) : toutes les rubriques de la fiche de recensement
  (EP, EM), du rapport de rentrée et de la fiche de fin d'année (EP, EM), dans l'ordre des fiches officielles :
  questions Oui / Non, cases et choix (nombre d'écoles et %), nombres et cellules de tableaux (somme, moyenne,
  écart type, min, max) ; par CS, zone ou école ; secteur public et privé à part ; Excel de toutes les rubriques.
- **Graphiques au choix** (v1.10.6) : chaque graphique des modules Effectifs, Infrastructures et Écoles s'affiche en
  courbe, histogramme, barres empilées, aires ou points ; « pour tous les graphiques » applique et retient le choix.
- **Module « Écoles : nombre, structure pédagogique et équipements »** (v1.10.6, Statistiques) : nombre d'écoles
  (EP, EM, EE), classes / sections autorisées et ouvertes, salles existantes et utilisées, classes simples, jumelées
  et multigrades, moyennes et **écarts types** (classes par école, élèves par école, élèves par classe), eau potable
  et sa source (SONEB, forage, adduction villageoise, **puits**, citerne), électricité et sa source, cantine, latrines,
  lavage des mains, clôture, domaine, jardin, bibliothèque, pharmacie, terrain de sport, titre de propriété ;
  recensement, rentrée ou fin d'année ; par CS, zone ou école ; public et privé à part ; courbes ; Excel.
- **Module « Infrastructures et mobilier »** (v1.10.5, Statistiques et division des infrastructures) : d'après la fiche
  de recensement, le rapport de rentrée ou la fiche de fin d'année (au choix), par CS, par zone ou par école, secteur
  public et privé à part : salles de classe (définitifs bon / mauvais état, mixtes, provisoires, sans mur ni toit, en
  construction ; existantes, utilisées ; élèves par salle), commodités (eau, électricité, latrines, lavage des mains,
  clôture, en % des écoles), mobilier du primaire avec **places assises et déficit**, mobilier de la maternelle,
  manuels par élève ; une courbe par tableau ; Excel.
- **Tableaux globaux des fiches** (Fiches des écoles) : pour la fiche de recensement (EP, EM) et les rapports de
  rentrée et de fin d'année (EP, EM), chaque rubrique chiffrée (infrastructures, locaux, mobilier, équipements,
  effectifs, finances…) avec une colonne par CS (DDEMP) ou par zone (CS) et le total ; Excel de toutes les rubriques.

## Nouveautés de la version 1.9.2

- Le **code d'accès personnel** est **désactivé pour le moment** : l'application s'ouvre comme avant, sans code ni
  bandeau. Le mécanisme reste prêt (acces.py : ACTIF = True, ou variable d'environnement CODES_ACCES=1, pour le réactiver).

## Nouveautés de la version 1.9.1

- **Garde-fou de la saisie des notes** (saisie des évaluations et notes par période) : chaque matière se saisit en
  deux cases, la **note principale** et la **note de performance** (case « P », sur 2) ; la note retenue est leur
  somme. Le perfectionnement n'est accordé qu'à partir de 10 (en dessous, la note reste telle quelle, performance 0) ;
  la somme ne dépasse jamais 20 (19 → performance 1 au plus). La case passe au **rouge** dès que la note principale
  atteint 20 (20/20 n'est possible qu'avec la performance), qu'une performance accompagne une note inférieure à 10,
  que la performance dépasse 2 ou que la somme dépasse 20 ; ces valeurs sont refusées à l'enregistrement.
- **Code d'accès personnel** : chaque compte doit saisir, une fois, le code délivré par le concepteur (Maître Aimé
  FACHE). Le code est lié au compte et à l'installation, n'expire pas, et se demande en un toucher par WhatsApp depuis
  la page « Code d'accès » ; l'administrateur ou le directeur envoie toutes les demandes et colle tous les codes en une
  fois (« Codes d'accès »). Délai de 15 jours après la mise à jour, puis blocage des comptes sans code. Le code est
  une signature numérique : seul le générateur du concepteur, qui n'est pas publié, peut le produire.

## Nouveautés de la version 1.9

- **Groupes WhatsApp** (menu « Groupes WhatsApp ») pour partager les informations :
  - école : groupe des enseignants, groupe de tout le personnel ;
  - circonscription scolaire : directeurs, enseignants (toute la CS ou une zone pédagogique), conseillers pédagogiques ;
  - DDEMP : directeurs, enseignants, chefs de circonscription, conseillers pédagogiques (filtre par CS et par zone).
  
  Les numéros (fiche de l'école, personnel transmis par les écoles, CP des zones) sont mis au format +229 01 XX XX XX XX ;
  le fichier de contacts (.vcf) fait apparaître dans « Nouveau groupe » de WhatsApp les seules personnes qui ont un
  compte ; le lien d'invitation est envoyé personne par personne avec suivi ; messages prêts à l'emploi (convocation,
  visite de classe, rappel, demande de transmission, résultats, information) à poster dans le groupe ou à envoyer
  à chacun, l'un après l'autre. WhatsApp n'autorise aucune application à créer le groupe à la place de son
  administrateur : la page guide les trois gestes à faire dans WhatsApp.

## Nouveautés de la version 1.8

- **Accueil par rôle** : grandes tuiles des actions principales du rôle connecté (directeur, secrétariat, comptabilité,
  fondateur ; CCS, CP et chefs de service dans les applications CS et DDEMP), avec l'état des sauvegardes.
- **« Ma classe »** (enseignant, ouvert directement à la connexion) : appel du jour, absences de la semaine, dernière
  évaluation (taux de réussite, notes manquantes), prochaines évaluations, élèves à suivre (absences répétées,
  non-maîtrise), boutons « Faire l'appel », « Saisir les notes », « Groupes de remédiation ».
- **Appel rapide** : un toucher sur le nom fait passer présent → absent → retard ; compteurs en direct, « Tous présents ».
- **Saisies hors ligne** : l'appel et les notes enregistrés sans réseau sont gardés sur l'appareil et envoyés
  automatiquement au retour de la connexion (badge « saisie(s) gardée(s) »). Les pages de classe restent consultables
  hors ligne.
- **Mise à jour depuis l'application** : un bandeau signale la nouvelle version publiée sur GitHub et propose le
  téléchargement de l'installateur ou de l'APK de la bonne édition.
- **Groupes de remédiation** après chaque évaluation (/evaluations/<n>/remediation, PDF, Excel) : par matière,
  soutien intensif (< 7), consolidation (7 à < 10), maîtrise (10 à < 15), approfondissement / tuteurs (≥ 15) ;
  maternelle : NA / ECA / A ; activités proposées par discipline, élèves en non-maîtrise, matières à renforcer.
- **Alertes de pilotage** (CS / DDEMP, /juridiction/alertes et résumé au tableau de bord) : écoles sans transmission
  ou sans transmission depuis 30 jours, manque d'enseignants, classes pléthoriques, écoles non visitées ce trimestre,
  retard des CP / CCS sur leur programmation, séances d'UP prévues et non tenues.

## Nouveautés de la version 1.7

| Menu | Contenu |
|---|---|
| **En-tête officiel** (SCOLARIS Autonome et SCOLARIS Public) | Emblème du MEMP (armoiries, « Ministère des Enseignements Maternel et Primaire », République du Bénin) en tête de la fiche d'inscription au CEP, des certificats et attestations, des bulletins, des fiches et listes de l'école ; **armoiries à la place du logo** sur la carte scolaire du candidat ; **carte d'identité scolaire** de l'élève refaite avec l'en-tête officiel |
| **Communes et villages** | Référentiel des unités administratives locales : 12 départements, 77 communes, 546 arrondissements, **5 290 villages et quartiers de ville** ; listes en cascade dans les formulaires (département → commune → arrondissement → village, lieu de naissance, résidence des parents, adresse de l'école) |
| **CEP** | **Signature digitale du parent** (au doigt ou à la souris) imprimée sur la fiche d'inscription au CEP et sur la fiche de renseignements |
| **Appareil photo** | Caméra avant / arrière sur toutes les prises de vue ; dans les applications Android, le bouton photo propose l'appareil photo (avant ou arrière) ou la galerie, y compris dans l'application légère SCOLARIS.apk |
| **Conseillers pédagogiques** (SCOLARIS Circonscription et DDEMP) | CP par zone ; programmation trimestrielle des activités ; journal des activités (suivis des directeurs, séances d'UP, formations groupées, conférences, concertations, autres activités) ; **bilan trimestriel et annuel des activités pédagogiques, niveau zone et niveau CS**, selon le canevas (1. réseau d'animation pédagogique, 2. activités menées, 3. concertations et autres activités, 4. taux de couverture, 5. résultats de l'évaluation d'étape, 6. analyse et problèmes majeurs, 7. commentaires), chiffres calculés et modifiables, analyse proposée ; Enregistrer, Valider, **Charger** (Excel), **Télécharger** (PDF avec en-tête officiel, signature et cachet ; Excel), Recalculer, **Réinitialiser**, **Supprimer** ; bilans envoyés à la DDEMP avec le paquet de la CS |

## Nouveautés de la version 1.6

| Menu | Contenu |
|---|---|
| **Tableau synoptique de l'école** (avant le tableau de bord, éditions privée et publique) | Identité (MEMP, DDEMP, CCS, EPP, CP de zone, zone pédagogique n°, UP, RUP, Co-RUP, année de création, dirigé par, grade et nom du directeur) ; **tableau du personnel enseignant** (matricule, NIP, promotion, catégorie FE / ACDPE / ACDPCTD, fonction, grade A-B-C, indices, cours tenus, anciennetés générale / département / école, dates de prise de service, retraite, dernière formation, diplômes académique et professionnel (CEAP, CAP), visite d'aptitude, note, visites CP/CCS et du directeur, participation à l'UP, gestion collégiale, contact) ; **comité de santé, bureau APE, comité de direction, comités de classe** ; **emplois du temps** officiels (MEMP 2016, CI → CM2, maternelle) modifiables ; **planification annuelle** par cours ; **règlement intérieur** officiel des écoles primaires (préambule, titres, 63 articles) modifiable ; import / export Excel et PDF |
| **Règles de calcul** | Anciennetés au 31 décembre de la première année de l'année scolaire en cours ; retraite à 60 ans (grade A), 58 (B), 55 (C), départ le 1er jour du trimestre qui suit le trimestre de naissance (né de janvier à mars → 1er avril, etc.) |
| **Données → EducMaster** | Onglet **maternelle** (appréciations), **modèles officiels EducMaster** servis tels quels et remplis par SCOLARIS : modèle d'importation des notes (primaire, 4 feuilles), modèle des élèves par classe (CM2 → maternelle 1, avec NPI et nationalité), modèle des agents ; import de ces modèles |
| **Scolarité / CEP** | Bouton **Supprimer** (ou Retirer) sur les inscrits, suppression par sélection ; suppression de la carte scolaire / carte d'identité |
| **Cantine → Vivres et stock** | Vivres (quantité, qualité, péremption, seuils), entrées / sorties / pertes / inventaires, sortie du jour, récapitulatifs, alertes, PDF, Excel, charger, réinitialiser |
| **Évaluations → Comité d'évaluation, épreuves et grilles** | Membres et qualifications, élaboration des épreuves (situation, consignes, items et barème, PDF sujet et corrigé), grilles de correction / d'évaluation / d'observation |
| **Certificats et cachets** | Ligne **NIP** avant la ligne du nom sur tous les certificats et attestations ; **griffe** (cachet rectangulaire du nom, préconçue à partir du titre et du nom) sur les documents signés ; la « Région pédagogique » (CRP) disparaît de toutes les fiches, seule la Circonscription scolaire reste |
| **Calendrier scolaire officiel** (onglet du tableau synoptique, et menu Scolarité) | Calendrier 2026-2027 de l'arrêté interministériel du 28 juillet 2026 prérempli (pré-rentrée, trimestres, congés, fériés, grandes vacances), modifiable au fil des années : ajouter, modifier, supprimer, recharger, réinitialiser, préparer l'année suivante, import / export Excel, PDF, vue des 12 mois, application au registre des jours de classe |
| **Thèmes d'UP, conférences pédagogiques et formations groupées** (onglet du synoptique, menu Évaluations) | Planning officiel DIIP 2026-2027 (12 thèmes maternelle, 12 primaire, 5 conférences, 5 formations groupées) avec axes, dates et suivi d'exécution ; ajouter, modifier, supprimer, recharger, réinitialiser, Excel, import, PDF |
| **Planification mensuelle (CE-CM)** (onglet du synoptique) | Grille officielle par classe et par mois (français par semaine, dictée, mathématiques, éducation sociale, EST, éducation artistique, EPS), dupliquer le mois précédent, PDF au modèle officiel signé par le titulaire et le directeur, Excel, import |
| **Périmètre de l'enseignant** | Chaque enseignant se connecte avec son identifiant et son mot de passe et accède à **ses classes** : élèves, appel, registres, notes et bulletins, évaluations, CEP, cantine, synthèse, épreuves, emplois du temps et planifications, règlement, calendrier, thèmes d'UP, documents, carrière, messages aux parents ; le domaine du directeur (tableau de bord, synoptique, finances, administration, recensement, données, secrétariat) lui est fermé ; sa **signature digitale** (Mon espace) est apposée sur les documents qu'il émet |
| **Caméra** | Capture photo avec bascule caméra avant / arrière et choix de l'appareil |
| **SCOLARIS Circonscription / DDEMP** | Voir [SCOLARIS_ADMINISTRATION.md](SCOLARIS_ADMINISTRATION.md) : classes par cours et par zone, divisions (rubriques AOF, lignes d'action), unités pédagogiques, conseillers pédagogiques, et tous les modules des écoles ouverts aux applications d'administration |

## Nouveautés de la version 1.3

| Menu | Contenu |
|---|---|
| **Interface** | Menu latéral fixe + zone de travail ; la barre du haut et les indicateurs restent visibles au défilement |
| **Administration → Écoles** | Plusieurs écoles (DDEMP, CS parmi les 118 circonscriptions, UP, zone, directeur/directrice, CCS), cachet officiel généré (arcs, étoiles, bleu ou rouge), signatures digitales ; rôle **fondateur** et tableau consolidé ; affectation des enseignants à leurs classes (et matières au secondaire) |
| **Scolarité** | Inscription complète (EducMaster, NIP, n° de table, centre d'examen, photo fichier ou caméra), import/export Excel des élèves, **registre de présence** par demi-journée, **calendrier** des jours de classe (mercredi = 1 demi-journée), **relevés mensuels de présence** (septembre → juin), **tableau d'affichage** (âges et scolarités par sexe) |
| **Évaluations** | Évaluations diagnostiques / formatives / sommatives d'étape / certificatives, matières cochées, seuil de **maîtrise** (primaire : seule condition de réussite, la moyenne sert au rang), bulletins, rapport, Excel, publication ; **statistiques**, **analyse et rapport**, **tableau d'honneur**, **bilan annuel** (M = (M_O + E_D)/2), **synthèse École / UP / CS** |
| **Examens (CEP)** | Fiche d'inscription au CEP (modèle officiel), **carte scolaire du candidat** recto/verso, **examen blanc CEP** et relevés de notes |
| **Cantine** | Montant par jour et par classe, paiements de la semaine, statistiques par genre, récapitulatifs jour/semaine/mois/année |
| **Données** | Import/export, **EducMaster** (primaire, secondaire), **conversion PDF → Excel/CSV** |
| **Espaces** | Espace élève (`/eleve`), espace enseignant (`/mon-espace`), espace parents (`/parent`), tableau du fondateur (`/fondateur`) |

Non réalisable dans un navigateur : la reconnaissance d'empreinte digitale.

## Modules (version 1.2)

| Menu | Contenu |
|---|---|
| **Scolarité** | Élèves (maternelle, primaire, secondaire), classes, **registre d'appel** (absences, retards, justifications), statistiques d'absences |
| **Notes** | Saisie des notes ou des appréciations (maternelle : Acquis / En cours / Non acquis), observations, résultats, bulletins et livrets PDF, publication aux parents |
| **Finances** | Paiements au guichet et reçus, impayés, **paiements en ligne** (FedaPay, KkiaPay), **trésorerie** (journal de caisse, bilan, budget), **personnel et paie** (CNSS, ITS, VPS, bulletins de paie) |
| **Parents** | Comptes parents, **espace parents** (notes, bulletins, absences, reçus, paiement en ligne, messages), messages WhatsApp en 1 clic et SMS automatiques |
| **Secrétariat** | Registre du courrier arrivé / départ, archives de documents numérisés |
| **Administration** | Paramètres de l'école, utilisateurs, réglages paiement en ligne, WhatsApp/SMS, taux de paie, sauvegarde, journal |

Espace parents : `/parent` (identifiant = numéro de téléphone du parent).

## Installation (Windows)

1. Installez **Python 3.10 ou plus** depuis python.org (cochez « Add Python to PATH »).
2. Décompressez le dossier `scolaris`, puis double-cliquez sur **`lancer.bat`**.
   La première fois, il installe Flask et ReportLab (connexion Internet nécessaire).
3. Le navigateur s'ouvre sur http://localhost:5100.
   Connexion : **admin / admin123** – un nouveau mot de passe est demandé tout de suite.

Pour essayer avec des données fictives : `venv\Scripts\python demo.py` **avant** toute vraie saisie
(2 classes, 12 élèves, notes du trimestre 1, paiements).

## Utilisation en réseau

Les autres postes de l'école (et les téléphones) se connectent à `http://ADRESSE-IP-DU-PC:5100`.
Pour que les QR codes imprimés pointent vers ce serveur, définissez l'adresse dans `config.py`
(`URL_PUBLIQUE`) ou dans la variable d'environnement `SCOLARIS_URL`.
Autorisez le port 5100 dans le pare-feu Windows si nécessaire.

## Paramétrage

Dans l'application : **Administration → Paramètres de l'établissement** (nom, année, périodes, logo,
cachet, signature). `config.py` ne contient que les valeurs par défaut.

### Valeurs par défaut — `config.py`

- `ECOLE` : nom, sigle, adresse, téléphone, nom du directeur, ville (en-têtes de tous les documents).
- `ANNEE_ACTIVE` : année scolaire en cours (ex. `2026-2027`).
- `PERIODES` : `Trimestre 1/2/3` par défaut (remplacez par `Semestre 1/2` si besoin).
- `MODES_PAIEMENT` : Espèces, MTN MoMo, Moov Money, Celtiis Cash, Virement.

Dans `static/ecole/`, déposez éventuellement **`logo.png`**, **`cachet.png`** et **`signature.png`** :
ils apparaissent automatiquement sur les documents.

## Règles de calcul (fichier `calcul.py`)

**Primaire** (CI → CM2)
- Moyenne = moyenne simple des matières notées (le coefficient n'est pas utilisé).
- Décision = règle des 2/3 sur les matières « standard » : ADMIS si le nombre de notes ≥ 10
  atteint ⌈2/3 × nombre de matières standard notées⌉.
- Arts plastiques, Arts vivants et EPS comptent dans la moyenne mais **pas** dans la règle des 2/3
  (modifiable dans la page *Matières*).

**Secondaire** (6ème → Tle)
- Moyenne pondérée Σ(note × coef) / Σ(coef) ; coefficients non appliqués en 6ème et 5ème.
- ADMIS si moyenne ≥ 10.
- Une matière sans note (LV2 non choisie, Philosophie en 4ème…) est ignorée et n'apparaît pas sur le bulletin.

**Saisie** : note de 0 à 20 (virgule acceptée), `D` = dispensé (exclu du calcul), vide = pas encore évalué.
**Rangs** : les élèves à égalité partagent le même rang (« 2e ex æquo »), le suivant est 4e.

Tests : `python -m unittest discover tests`

## Rôles

| Rôle | Accès |
|---|---|
| Administrateur | Tout, dont comptes utilisateurs, matières et journal |
| Directeur | Tout sauf l'administration ; peut annuler un reçu |
| Secrétaire | Élèves, classes, documents officiels |
| Comptable | Paiements, reçus, impayés |
| Enseignant | Son périmètre = ses classes (affectations) : élèves (fiches, photos), appel, registre, relevés, affichage, évaluations, notes et bulletins, synthèse, CEP (CM2), cantine, messages aux parents, comptes élèves, épreuves, visites, documents de l'enseignant, sa carrière, sa signature digitale (« Mon espace », `/mon-espace`) ; le domaine du directeur (tableau de bord, synoptique, finances, administration, données, secrétariat, suppression d'élèves) lui est refusé (403) — module `m_perimetre_enseignant` |

## Documents et vérification

Carte d'élève, certificat de fréquentation, attestation d'inscription, certificat de transfert,
fiche CEP (CM2), bulletins (individuels ou toute la classe en un PDF), reçus.
Chaque document porte un **code unique + QR code**. La page publique `/verifier/CODE` indique
si le document est authentique (un reçu annulé est signalé comme tel).

## Inscription des écoles intéressées

La page publique **`/rejoindre`** (sans connexion) permet à une école de demander à utiliser SCOLARIS :
établissement, département, effectif, contact, modules souhaités. Un lien y mène depuis la page de connexion.
L'administrateur suit les demandes dans **Écoles candidates** (statut, note interne, export CSV).
Protection anti-robots : champ piège invisible et 5 envois maximum par heure et par adresse IP.
Pour que des écoles extérieures y accèdent, l'application doit être hébergée sur un serveur joignable
depuis Internet (hébergeur Python, ou VPS avec nom de domaine et HTTPS).

## Sauvegarde

Administration → **Sauvegarde** télécharge un .zip complet (base, photos, logo).
En mode développement les données sont dans `instance/` ; dans la version installée, dans `%APPDATA%\SCOLARIS`.

## Limites de cette version

- Paiement en ligne : nécessite un compte marchand FedaPay ou KkiaPay au nom de l'école et une version
  de SCOLARIS accessible sur Internet (https). Au guichet, les paiements Mobile Money restent saisis à la main.
- WhatsApp : message pré-rempli, envoyé en 1 clic par le secrétariat (l'envoi 100 % automatique exige
  l'API WhatsApp Business de Meta, non incluse). SMS automatiques : via la passerelle HTTP de votre fournisseur.
- Paie : taux CNSS / ITS / VPS par défaut du Bénin, à faire confirmer par votre comptable (réglables).
- Pas encore de moyenne annuelle ; un enseignant sans aucune affectation voit toutes les classes (affectez-le à ses classes).

---

*SCOLARIS — Conception : Maître Aimé FACHE*
