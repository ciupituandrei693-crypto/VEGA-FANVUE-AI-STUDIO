; Optional Inno Setup recipe; requires prebuilt dist\VEGA\VEGA.exe on Windows.
#define MyAppName "VEGA Universal"
#define MyAppVersion "0.9.0-dev"
[Setup]
AppId={{32DA40C0-7B9F-4311-A989-A53B436EAB21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\VEGA Universal
DefaultGroupName=VEGA Universal
OutputDir=..\dist_installer
OutputBaseFilename=VEGA_Universal_v0_9_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
[Files]
Source: "..\dist\VEGA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\VEGA Universal"; Filename: "{app}\VEGA.exe"
Name: "{autodesktop}\VEGA Universal"; Filename: "{app}\VEGA.exe"; Tasks: desktopicon
[Tasks]
Name: desktopicon; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"
[Run]
Filename: "{app}\VEGA.exe"; Description: "Start VEGA Universal"; Flags: postinstall nowait skipifsilent
