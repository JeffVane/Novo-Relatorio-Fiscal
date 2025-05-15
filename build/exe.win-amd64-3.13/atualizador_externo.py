
import os
import sys
import requests
import zipfile
import shutil
import tempfile
import subprocess
import ctypes

REPO_OWNER = "JeffVane"
REPO_NAME = "Novo-Relatorio-Fiscal"
BRANCH = "main"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
APP_DIR = os.path.dirname(os.path.abspath(__file__))

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        script = os.path.abspath(__file__)
        params = ' '.join([f'"{arg}"' for arg in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit(0)

def baixar_e_extrair_zip():
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, "update.zip")

    response = requests.get(ZIP_URL)
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    extracted_path = os.path.join(temp_dir, f"{REPO_NAME}-{BRANCH}")

    for item in os.listdir(extracted_path):
        if item.startswith(".git"):
            continue
        src = os.path.join(extracted_path, item)
        dst = os.path.join(APP_DIR, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst, ignore_errors=True)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    os.remove(zip_path)
    shutil.rmtree(extracted_path, ignore_errors=True)

def reiniciar_aplicacao():
    app_path = os.path.join(APP_DIR, "login.py")
    subprocess.Popen(["python", app_path], shell=True)

if __name__ == "__main__":
    run_as_admin()
    baixar_e_extrair_zip()
    reiniciar_aplicacao()
