import os
from cx_Freeze import setup, Executable

# ---------------- Versão ----------------
def verificar_versao():
    caminho = "version.txt"
    if os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as f:
            versao_atual = f.read().strip()
    else:
        versao_atual = "0.0.0"

    print(f"Versão atual: {versao_atual}")
    resposta = input("Deseja alterar a versão? (s/n): ").lower()

    if resposta == "s":
        nova = input("Digite a nova versão: ").strip()
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(nova)
        return nova

    return versao_atual


versao = verificar_versao()

# ---------------- Arquivos ----------------
base = "Win32GUI"
caminho_base = os.path.dirname(__file__)

imagens = [
    "add.png", "atribuir.png", "config.png", "crc.ico",
    "delete.png", "edit.png", "login_logo.png",
    "menu.png", "procedimento.png", "siafisk.jpg",
    "web.png", "xlsx.png"
]

outros_arquivos = [
    "version.txt",
    "loading.gif",
    "atualizador_externo.py",
]

include_files = []

for arq in imagens + outros_arquivos:
    include_files.append((os.path.join(caminho_base, arq), arq))

# ---------------- Executável ----------------
executables = [
    Executable(
        script="login.py",
        base=base,
        target_name="RelatorioFiscal.exe",
        icon="crc.ico"
    )
]

setup(
    name="RelatorioFiscal",
    version=versao,
    description="Sistema de Relatórios - CRCDF",
    options={
        "build_exe": {
            "packages": [
                "os", "sqlite3", "requests", "zipfile",
                "tempfile", "shutil", "ctypes",
                "packaging"
            ],
            "include_files": include_files,
            "include_msvcr": True
        }
    },
    executables=executables
)
