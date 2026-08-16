#define MyAppName "AI Subscription Usage"
#ifndef MyAppVersion
#define MyAppVersion "0.4.0"
#endif
#define MyAppExeName "AI Subscription Usage.exe"

[Setup]
AppId={{42A9A10D-2AFB-4A39-9B57-EB13244437C5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\AI Subscription Usage
DefaultGroupName={#MyAppName}
OutputDir=..\dist-installer
OutputBaseFilename=AI-Subscription-Usage-{#MyAppVersion}-Windows-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\AI Subscription Usage.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Tasks]
Name: "startup"; Description: "Start AI Subscription Usage when Windows starts"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch AI Subscription Usage"; Flags: nowait postinstall skipifsilent
