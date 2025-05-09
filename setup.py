import os
from cx_Freeze import setup, Executable

base = "Win32GUI"

# Caminho absoluto da pasta onde está o setup.py
caminho_base = os.path.dirname(__file__)

# Lista de imagens com caminho absoluto
imagens = [
    "add.png", "atribuir.png", "config.png", "crc.ico", "delete.png",
    "edit.png", "login_logo.png", "menu.png", "procedimento.png",
    "siafisk.jpg", "web.png", "xlsx.png"
]

include_files = [os.path.join(caminho_base, img) for img in imagens]
include_files.append(os.path.join(caminho_base, "dejavu-fonts-ttf-2.37.tar.bz2"))

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
    version="1.0",
    description="Sistema de Relatórios - CRCDF",
    options={
        "build_exe": {
            "packages": ["os", "sqlite3"],
            "include_files": include_files
        }
    },
    executables=executables
)
