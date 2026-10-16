; Inno Setup : fabrique SCOLARIS-Installation-x.y.z.exe à partir de dist\SCOLARIS
; Compiler depuis la racine du projet :  iscc /DVersion=1.3.0 packaging\windows\scolaris.iss
; Applications jumelles :  iscc /DVersion=1.6.0 /DEdition=publique|cs|ddemp packaging\windows\scolaris.iss
;   -> SCOLARIS-Public-Installation-x.y.z.exe (dossier, données, port 5001 et raccourcis séparés)

#ifndef Version
  #define Version "1.6.0"
#endif
#ifndef Edition
  #define Edition "privee"
#endif
#if Edition == "publique"
  #define Nom "SCOLARIS Public"
  #define Fichier "SCOLARIS-Public-Installation-"
  #define Donnees "SCOLARIS_Public"
  #define Port "5001"
  #define Id "{{9A4D2C61-3B7E-4E15-8F0B-2C6E9D41A7F3}"
#elif Edition == "cs"
  #define Nom "SCOLARIS Circonscription"
  #define Fichier "SCOLARIS-Circonscription-Installation-"
  #define Donnees "SCOLARIS_CS"
  #define Port "5002"
  #define Id "{{3E7B5A90-61C4-4F2D-9B8E-0A4C7D2F5E16}"
#elif Edition == "ddemp"
  #define Nom "SCOLARIS DDEMP"
  #define Fichier "SCOLARIS-DDEMP-Installation-"
  #define Donnees "SCOLARIS_DDEMP"
  #define Port "5003"
  #define Id "{{C82F4D17-0B9A-4E63-A5D1-7F3E2B6C9A48}"
#else
  #define Nom "SCOLARIS"
  #define Fichier "SCOLARIS-Installation-"
  #define Donnees "SCOLARIS"
  #define Port "5000"
  #define Id "{{6C1E2B7A-4F3D-4B7E-9C2A-7D5E3F1A9B20}"
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
