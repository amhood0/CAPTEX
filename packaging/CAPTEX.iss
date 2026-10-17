#define MyAppName "CAPTEX"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "CAPTEX"
#define MyAppExeName "CAPTEX.exe"

[Setup]
AppId={{BF027831-4405-4C6A-BE07-E1603C2FD761}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\CAPTEX
DefaultGroupName=CAPTEX
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=CAPTEX-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\CAPTEX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CAPTEX"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\CAPTEX"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch CAPTEX"; Flags: nowait postinstall skipifsilent
