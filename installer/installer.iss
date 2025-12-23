#define AppName "Schnuffs Promotion Alerts"
#define AppExe "SchnuffsPromotionAlerts.exe"
#define AppVersion "2.0.0"
#define AppDir "{commonpf}\SchnuffsPromotionAlerts"
#define ServiceName "SchnuffsPromotionAlerts"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={#AppDir}
DefaultGroupName={#AppName}
OutputBaseFilename=SchnuffsPromotionAlerts_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=files\SchnuffTwitchAlertIcon.ico
PrivilegesRequired=admin

[Files]
Source: "files\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "files\nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "files\.env.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "files\SchnuffTwitchAlertIcon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben"

[Run]
[Run]
; Service installieren (nur einmal!)
Filename: "{app}\nssm.exe"; Parameters: "install {#ServiceName} ""{app}\{#AppExe}"""; Flags: runhidden

; Arbeitsverzeichnis setzen
Filename: "{app}\nssm.exe"; Parameters: "set {#ServiceName} AppDirectory ""{app}"""; Flags: runhidden

; Autostart aktivieren
Filename: "{app}\nssm.exe"; Parameters: "set {#ServiceName} Start SERVICE_AUTO_START"; Flags: runhidden

; Restart bei Crash
Filename: "{sys}\sc.exe"; Parameters: "failure {#ServiceName} reset= 0 actions= restart/5000"; Flags: runhidden

; Service EINMAL starten
Filename: "{app}\nssm.exe"; Parameters: "start {#ServiceName}"; Flags: runhidden

[UninstallRun]
Filename: "{app}\nssm.exe"; \
Parameters: "remove {#ServiceName} confirm"; \
Flags: runhidden
