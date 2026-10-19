; Inno Setup : fabrique SCOLARIS-Installation-x.y.z.exe à partir de dist\SCOLARIS
; Compiler depuis la racine du projet :  iscc /DVersion=1.3.0 packaging\windows\scolaris.iss
; Applications jumelles :  iscc /DVersion=1.10.4 /DEdition=publique|cs|ddemp packaging\windows\scolaris.iss
;   -> SCOLARIS-Public-Installation-x.y.z.exe (dossier, données, port 5101 et raccourcis séparés)

#ifndef Version
  #define Version "1.10.4"
#endif
#ifndef Edition
  #define Edition "privee"
#endif
#if Edition == "publique"
  #define Nom "SCOLARIS Public"
  #define Fichier "SCOLARIS-Public-Installation-"
  #define Donnees "SCOLARIS_Public"
  #define Port "5101"
  #define Id "{{F7AD2F18-22FD-4036-ABCF-D5212E63321E}"
#elif Edition == "cs"
  #define Nom "SCOLARIS Circonscription"
  #define Fichier "SCOLARIS-Circonscription-Installation-"
  #define Donnees "SCOLARIS_CS"
  #define Port "5102"
  #define Id "{{31FD371E-D78C-46E3-9869-AD27F484A129}"
#elif Edition == "ddemp"
  #define Nom "SCOLARIS DDEMP"
  #define Fichier "SCOLARIS-DDEMP-Installation-"
  #define Donnees "SCOLARIS_DDEMP"
  #define Port "5103"
  #define Id "{{07A8651F-A359-4DAE-9B08-6E7E76C225FC}"
#else
  #define Nom "SCOLARIS"
  #define Fichier "SCOLARIS-Installation-"
  #define Donnees "SCOLARIS"
  #define Port "5100"
  #define Id "{{615F2F30-6FE0-4293-BD01-EB6D706FE8E7}"
#endif

[Setup]
AppId={#Id}
AppName={#Nom}
AppVersion={#Version}
AppPublisher=SCOLARIS – Conception : Maître Aimé FACHE
AppCopyright=Conception : Maître Aimé FACHE
DefaultDirName={autopf}\{#Nom}
DefaultGroupName={#Nom}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename={#Fichier}{#Version}
SetupIconFile=..\..\static\icons\scolaris.ico
UninstallDisplayIcon={app}\SCOLARIS.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Créer une icône sur le bureau"; GroupDescription: "Raccourcis :"
Name: "demarrage"; Description: "Lancer {#Nom} au démarrage de Windows (recommandé pour le PC serveur de l'école)"; GroupDescription: "Démarrage :"
Name: "parefeu"; Description: "Autoriser les tablettes et téléphones du Wi-Fi à se connecter (pare-feu Windows)"; GroupDescription: "Réseau :"

[Files]
Source: "..\..\dist\SCOLARIS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#Nom}"; Filename: "{app}\SCOLARIS.exe"
Name: "{group}\Dossier des données {#Nom}"; Filename: "{userappdata}\{#Donnees}"
Name: "{group}\Désinstaller {#Nom}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#Nom}"; Filename: "{app}\SCOLARIS.exe"; Tasks: bureau
Name: "{userstartup}\{#Nom}"; Filename: "{app}\SCOLARIS.exe"; Parameters: "--sans-navigateur"; Tasks: demarrage

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#Nom}"""; Flags: runhidden; Tasks: parefeu
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#Nom}"" dir=in action=allow protocol=TCP localport={#Port} profile=any"; Flags: runhidden; Tasks: parefeu
Filename: "{app}\SCOLARIS.exe"; Description: "Lancer {#Nom} maintenant"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#Nom}"""; Flags: runhidden; RunOnceId: "SupprRegleParefeu"

[UninstallDelete]
Type: files; Name: "{app}\edition.txt"

[Messages]
french.FinishedLabel={#Nom} est installé.%n%nVos données sont enregistrées dans le dossier « {#Donnees} » de votre profil Windows : elles sont conservées si vous désinstallez ou mettez à jour {#Nom}.%n%nPremière connexion : admin / admin123.

#if Edition != "privee"
[Code]
// Édition imposée par l'installateur : edition.txt à côté de SCOLARIS.exe (lu par config.py)
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SaveStringToFile(ExpandConstant('{app}\edition.txt'), '{#Edition}', False);
end;
#endif
