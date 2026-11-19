; CMO Scenario Studio - Windows installer (Inno Setup 6).
;
; Built by packaging/build_release.py, which passes:
;   /DAppVersion=1.6.0          version (required)
;   /DSourceDir=...             the PyInstaller folder build\dist\CMO-Scenario-Studio
;   /DOutputDir=...             where to write CMO-Scenario-Studio-<version>-setup.exe
;   /DSign + /Scmostudio=...    optional: sign the setup and uninstaller with that signtool command ($f = file)
;
; Installs per machine into Program Files (asks for administrator rights). For testing, /CURRENTUSER installs
; for the current user only without elevation. Settings, libraries, the tile cache and projects live in the user's
; AppData / Documents and are never touched by installing, updating or uninstalling.
;
; Extra command-line switch: /NOLAUNCH - do not start the studio at the end of a silent install.

#ifndef AppVersion
  #error AppVersion must be defined (/DAppVersion=x.y.z)
#endif
#ifndef SourceDir
  #define SourceDir "..\build\dist\CMO-Scenario-Studio"
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif

#define AppName "CMO Scenario Studio"
#define AppExe "CMO-Scenario-Studio.exe"
#define AppUrl "https://github.com/MasonicTombomb/CMO-Scenario-Studio"

[Setup]
; Never change the AppId: it is how upgrades find the existing installation.
AppId={{8F1C2B7E-4A3D-4C59-9E21-5B7A6D3C1F40}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=CMO Scenario Studio
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=CMO-Scenario-Studio-{#AppVersion}-setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
LicenseFile=..\LICENSE
#ifdef Sign
SignTool=cmostudio
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "assoc"; Description: "Open .cmoproj project files with {#AppName}"; GroupDescription: "File types:"

[InstallDelete]
; Remove the previous version's libraries so nothing stale is left behind after an upgrade.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\User Manual"; Filename: "{app}\docs\manuals\CMO-Scenario-Studio-User-Manual.pdf"
Name: "{group}\Reference Manual"; Filename: "{app}\docs\manuals\CMO-Scenario-Studio-Reference-Manual.pdf"
Name: "{group}\Example projects"; Filename: "{app}\examples"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.cmoproj"; ValueType: string; ValueName: ""; ValueData: "CMOScenarioStudio.Project"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\CMOScenarioStudio.Project"; ValueType: string; ValueName: ""; ValueData: "CMO Scenario Studio project"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\CMOScenarioStudio.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\CMOScenarioStudio.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""; Tasks: assoc

[Run]
; Shown as "Launch" on the last page; also runs after a silent update (the in-app updater) unless /NOLAUNCH.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall runasoriginaluser; Check: ShouldLaunch

[Code]
function ShouldLaunch: Boolean;
var
  i: Integer;
begin
  Result := True;
  for i := 1 to ParamCount do
    if CompareText(ParamStr(i), '/NOLAUNCH') = 0 then
      Result := False;
end;
