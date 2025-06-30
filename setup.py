import os
from cx_Freeze import setup, Executable


# 🔥 ETAPA 1: Verificar e atualizar versão manualmente no terminal
def verificar_versao():
    caminho = "version.txt"
    if os.path.exists(caminho):
        with open(caminho, "r") as file:
            versao_atual = file.read().strip()
    else:
        versao_atual = "0.0.0"

    print(f"Versão atual: {versao_atual}")
    resposta = input("Deseja alterar a versão? (s/n): ").strip().lower()

    if resposta == "s":
        nova_versao = input("Digite a nova versão: ").strip()
        with open(caminho, "w") as file:
            file.write(nova_versao)
        print(f"Versão alterada para {nova_versao}")
        return nova_versao
    else:
        print(f"Versão mantida: {versao_atual}")
        return versao_atual


# 🔥 Captura a versão antes de empacotar
versao = verificar_versao()


# 🔥 ETAPA 2: Empacotamento
base = "Win32GUI"
caminho_base = os.path.dirname(__file__)

imagens = [
    "add.png", "atribuir.png", "config.png", "crc.ico", "delete.png",
    "edit.png", "login_logo.png", "menu.png", "procedimento.png",
    "siafisk.jpg", "web.png", "xlsx.png"
]

outros_arquivos = [
    "dejavu-fonts-ttf-2.37.tar.bz2",
    "version.txt",
    "loading.gif",
    "atualizador_externo.py"
]

include_files = [os.path.join(caminho_base, arq) for arq in imagens + outros_arquivos]

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
            "packages": ["os", "sqlite3", "requests", "zipfile", "tempfile", "shutil", "ctypes"],
            "include_files": include_files,
            "include_msvcr": True
        }
    },
    executables=executables
)
