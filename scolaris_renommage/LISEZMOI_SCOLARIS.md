# GESCOL → SCOLARIS : renommage et logo

**SCOLARIS** remplace GESCOL partout : écrans, documents PDF et Excel, fichiers, scripts, Docker, Render, GitHub Actions,
applications Windows et Android. Le nom du concepteur est conservé et accompagne le nom de l'application
(« SCOLARIS 1.6 · Conception : Maître Aimé FACHE »).

## Contenu de ce dossier
| Fichier | Rôle |
|---|---|
| `renommer_scolaris.py` | script de renommage (à lancer une fois à la racine du projet) |
| `generer_icones.py` | génère les icônes PNG / ICO / Android à partir du logo (appelé par le script) |
| `scolaris-icone.svg` | icône (carré arrondi : soleil, livre ouvert, bande vert-jaune-rouge) |
| `scolaris-logo.svg`, `scolaris-logo.png` | logo horizontal avec le nom |
| `scolaris-banniere-github.png` | bannière 1280 × 640 (GitHub → Settings → Social preview) |

## Procédure (sur votre ordinateur, dans le dossier du projet)
1. **Appliquer d'abord** les correctifs de la version 1.6 (archive `gescol_correctifs_v16.zip`), pour que les fichiers
   modifiés soient eux aussi renommés.
2. Copier ce dossier à côté du projet, puis, à la racine du projet :
   ```
   python renommer_scolaris.py --essai        # simulation : ne modifie rien
   python renommer_scolaris.py                # renommage réel (sauvegarde créée : sauvegarde_avant_scolaris.zip)
   ```
3. Lancer les tests (les variables s'appellent désormais `SCOLARIS_EDITION`, `SCOLARIS_DATA`…) :
   `python -m unittest tests.test_calendrier` (et les autres `tests.test_*`).
4. Nouveau dépôt GitHub (le dépôt existant du même nom n'est pas touché) :
   ```
   git remote remove origin          # si le dossier était relié à l'ancien dépôt
   git add -A && git commit -m "SCOLARIS : nouveau nom et logo"
   git remote add origin https://github.com/<votre-compte>/scolaris.git
   git push -u origin main
   ```
   Pour le nom du dépôt, vérifiez d'abord sur github.com qu'il est libre (`scolaris`, sinon `scolaris-benin`).

## Ce que le script change
* le texte GESCOL / Gescol / gescol → SCOLARIS / Scolaris / scolaris dans tous les fichiers texte ;
* les noms de fichiers et dossiers (`scolaris.js`, `scolaris_serveur.py`, `SCOLARIS_PUBLIC.md`, `bj/scolaris/…`) ;
* le menu (icône à la place de la lettre « G »), la page de connexion, le favicon SVG, les icônes PNG / ICO de l'application
  installable, de Windows et d'Android ;
* les variables d'environnement (`SCOLARIS_DATA`, `SCOLARIS_EDITION`, `SCOLARIS_ADMIN_MDP`, `SCOLARIS_EN_LIGNE`, `SCOLARIS_URL`…).

## Compatibilité avec ce qui existe déjà
Les lignes marquées `LEGACY-GESCOL` ne sont jamais renommées. Elles permettent :
* de continuer à lire les anciennes variables `GESCOL_*` (Render, Docker, services déjà configurés) ;
* de réutiliser l'ancien dossier de données (`GESCOL`, `GESCOL_Public`, `GESCOL_CS`, `GESCOL_DDEMP`) et l'ancienne base
  `gescol.db` s'ils existent : **aucune donnée n'est perdue ni déplacée** ;
* d'accepter les anciens fichiers de transmission `.gescol` (les nouveaux sont des `.scolaris`).

## À savoir
* **Android** : l'identifiant de l'application passe de `bj.gescol…` à `bj.scolaris…`. Android la voit comme une nouvelle
  application : elle s'installe à côté de l'ancienne, sans la mettre à jour.
* **Windows** : le programme d'installation et le dossier de données portent le nouveau nom ; les données d'une installation
  existante sont reprises grâce à la compatibilité ci-dessus.
* **Render / Docker / PythonAnywhere** : renommez le service et le disque si vous voulez, ou gardez les anciens noms ;
  les variables `GESCOL_*` déjà saisies continuent de fonctionner.
* Les navigateurs déjà connectés devront se reconnecter (le nom des clés de stockage local change).
* Le script ne touche pas à `instance/`, `venv/`, `.git/`, `node_modules/`.
