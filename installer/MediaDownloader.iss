#include "version.iss"
[Setup]
AppId={{930B332D-ABBA-47BE-AB0C-5D09AC0BB694}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=MediaDownloader-Setup
SetupIconFile=..\app\resources\icon.ico
UninstallDisplayIcon={app}\MediaDownloader.exe
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
[Tasks]
Name: desktopicon; Description: "Create a desktop shortcut"; Flags: unchecked
[Files]
Source: "..\dist\MediaDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\MediaDownloader.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\MediaDownloader.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\MediaDownloader.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent runasoriginaluser
