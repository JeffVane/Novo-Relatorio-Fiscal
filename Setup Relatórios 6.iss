; Instalador para o RelatorioFiscal - CRCDF
[Setup]
AppName=S.I.A FISK
AppVersion=1.3
DefaultDirName={pf}\RelatorioFiscal
DefaultGroupName=RelatorioFiscal
OutputDir=output
OutputBaseFilename=Instalador_RelatorioFiscal
Compression=lzma
SolidCompression=yes
SetupIconFile=crc.ico

[Files]
; Instala todos os arquivos da build
Source: "build\exe.win-amd64-3.13\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; Garante que o atualizador_externo.py está incluso (redundante, mas seguro)
Source: "build\exe.win-amd64-3.13\atualizador_externo.py"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\RelatorioFiscal"; Filename: "{app}\RelatorioFiscal.exe"; WorkingDir: "{app}"
Name: "{group}\Desinstalar RelatorioFiscal"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\RelatorioFiscal.exe"; Description: "Executar após instalar"; Flags: nowait postinstall skipifsilent
