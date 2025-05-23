import os
from cx_Freeze import setup, Executable

base = "Win32GUI"
caminho_base = os.path.dirname(__file__)

# Imagens e outros arquivos estáticos
imagens = [
    "add.png", "atribuir.png", "config.png", "crc.ico", "delete.png",
    "edit.png", "login_logo.png", "menu.png", "procedimento.png",
    "siafisk.jpg", "web.png", "xlsx.png"
]

# Arquivos adicionais obrigatórios
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
        target_name="RelatorioFiscal 2.exe",
        icon="crc.ico"
    )
]

setup(
    name="RelatorioFiscal",
    version="1.0",
    description="Sistema de Relatórios - CRCDF",
    options={
        "build_exe": {
            "packages": ["os", "sqlite3", "requests", "zipfile", "tempfile", "shutil", "ctypes"],
            "include_files": include_files,
            "include_msvcr": True  # Para evitar erro de DLL ausente
        }
    },
    executables=executables
)
