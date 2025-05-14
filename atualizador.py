import requests
import zipfile
import os
import shutil
import sys

# Configurações do repositório
REPO_OWNER = "JeffVane"
REPO_NAME = "Novo-Relatorio-Fiscal"
BRANCH = "main"

# URLs
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/version.txt"
LOCAL_VERSION_FILE = "version.txt"
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def get_remote_version():
    try:
        response = requests.get(VERSION_URL)
        response.raise_for_status()
        return response.text.strip()
    except Exception as e:
        print(f"[ERRO] Falha ao buscar versão remota: {e}")
        return None


def get_local_version():
    try:
        with open(os.path.join(APP_DIR, LOCAL_VERSION_FILE), "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def baixar_e_extrair_zip():
    print("⬇️  Baixando nova versão...")
    zip_path = os.path.join(APP_DIR, "update.zip")
    response = requests.get(ZIP_URL)
    with open(zip_path, "wb") as f:
        f.write(response.content)

    print("📦 Extraindo arquivos...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(APP_DIR)

    os.remove(zip_path)

    folder_name = f"{REPO_NAME}-{BRANCH}"
    extracted_path = os.path.join(APP_DIR, folder_name)

    for item in os.listdir(extracted_path):
        s = os.path.join(extracted_path, item)
        d = os.path.join(APP_DIR, item)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

    shutil.rmtree(extracted_path)
    print("✅ Atualização concluída.")


def atualizar_se_necessario():
    local_version = get_local_version()
    remote_version = get_remote_version()

    if remote_version and remote_version != local_version:
        print(f"🔄 Atualização disponível: {local_version} → {remote_version}")
        baixar_e_extrair_zip()
        with open(os.path.join(APP_DIR, LOCAL_VERSION_FILE), "w") as f:
            f.write(remote_version)
        print("🚀 Reiniciando o programa (login.py)...")
        os.execv(sys.executable, [sys.executable, "login.py"])
    else:
        print("✅ Programa já está na versão mais recente.")
        os.system("python login.py")


if __name__ == "__main__":
    atualizar_se_necessario()
