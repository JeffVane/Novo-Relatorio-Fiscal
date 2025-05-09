; Instalador para o RelatorioFiscal - CRCDF
[Setup]
AppName=RelatorioFiscal
AppVersion=1.0
DefaultDirName={pf}\RelatorioFiscal
DefaultGroupName=RelatorioFiscal
OutputDir=output
OutputBaseFilename=Instalador_RelatorioFiscal
Compression=lzma
SolidCompression=yes
SetupIconFile=crc.ico

[Files]
Source: "build\exe.win-amd64-3.13\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar RelatorioFiscal"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\RelatorioFiscal.exe"; Description: "Executar após instalar"; Flags: nowait postinstall skipifsilent
