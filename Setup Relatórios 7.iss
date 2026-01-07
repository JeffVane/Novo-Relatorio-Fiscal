; Instalador para o RelatorioFiscal - CRCDF

#define AppVersion Trim(FileRead(FileOpen("version.txt")))
#define BuildDir "build\exe.win-amd64-3.13"

[Setup]
AppName=S.I.A FISK
AppVersion={#AppVersion}
DefaultDirName={pf}\RelatorioFiscal
DefaultGroupName=RelatorioFiscal
OutputDir=output
OutputBaseFilename=Instalador_RelatorioFiscal
Compression=lzma
SolidCompression=yes
SetupIconFile=crc.ico

UsePreviousAppDir=yes
DisableProgramGroupPage=yes

CloseApplications=yes
CloseApplicationsFilter=RelatorioFiscal.exe
RestartApplications=no

[Files]
; Instala todos os arquivos da build
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar RelatorioFiscal"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\RelatorioFiscal.exe"; Description: "Executar após instalar"; Flags: nowait postinstall skipifsilent
