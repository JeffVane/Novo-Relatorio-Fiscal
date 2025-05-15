import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QGraphicsOpacityEffect)
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtWidgets import QMessageBox
from db import check_login, get_users  # Buscar usuários do banco de dados
from main import MainApp  # Importa a tela principal
import os
from db import connect_db
import requests
import zipfile
import tempfile
import shutil

# Configurações do GitHub
REPO_OWNER = "JeffVane"
REPO_NAME = "Novo-Relatorio-Fiscal"
BRANCH = "main"
ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/version.txt"
LOCAL_VERSION_FILE = "version.txt"


def get_remote_version():
    try:
        response = requests.get(VERSION_URL)
        response.raise_for_status()
        return response.text.strip()
    except:
        return None

def get_local_version():
    try:
        with open(LOCAL_VERSION_FILE, "r") as f:
            return f.read().strip()
    except:
        return "0.0.0"



def baixar_e_extrair_zip():
    temp_dir = tempfile.gettempdir()
    zip_path = os.path.join(temp_dir, "update.zip")

    response = requests.get(ZIP_URL)
    with open(zip_path, "wb") as f:
        f.write(response.content)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    extracted_path = os.path.join(temp_dir, f"{REPO_NAME}-{BRANCH}")

    # Copia os arquivos para o diretório atual
    for item in os.listdir(extracted_path):
        src = os.path.join(extracted_path, item)
        dst = os.path.join(os.getcwd(), item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    os.remove(zip_path)
    shutil.rmtree(extracted_path)


def verificar_atualizacao():
    remote = get_remote_version()
    local = get_local_version()

    if remote and remote != local:
        if not QApplication.instance():
            _ = QApplication(sys.argv)

        resposta = QMessageBox.question(
            None,
            "Atualização disponível",
            f"Uma nova versão do sistema está disponível!\n\n"
            f"Versão atual: {local}\nNova versão: {remote}\n\n"
            f"Deseja atualizar agora?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if resposta == QMessageBox.Yes:
            try:
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
                        continue  # pula arquivos ocultos
                    src = os.path.join(extracted_path, item)
                    dst = os.path.join(os.getcwd(), item)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst, ignore_errors=True)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

                with open(LOCAL_VERSION_FILE, "w") as f:
                    f.write(remote)

                os.execv(sys.executable, [sys.executable, __file__])
            except Exception as e:
                QMessageBox.critical(None, "Erro ao atualizar", f"Erro ao atualizar:\n{str(e)}")





class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - SIAFISC CRCDF")
        self.setFixedSize(400, 320)  # Ajustado para acomodar os elementos
        self.setWindowIcon(QIcon("crc.png"))  # Ícone da janela

        # Aplicar fundo branco para evitar efeito preto no fade-in
        self.setStyleSheet("background-color: white;")

        layout = QVBoxLayout()

        # Adicionando a logo acima dos campos
        self.logo = QLabel(self)
        pixmap = QPixmap("siafisk.jpg")  # Substitua pelo caminho correto da logo
        self.logo.setPixmap(pixmap.scaled(450, 450, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo)

        # Campo para selecionar usuário
        self.label_user = QLabel("Usuário:")
        self.input_user = QComboBox()
        users = get_users()  # Obtém os usuários do banco de dados
        if users:
            self.input_user.addItems(users)
        else:
            self.input_user.addItem("Nenhum usuário cadastrado")

        # Aplicando estilo moderno à `QComboBox`
        self.input_user.setStyleSheet("""
            QComboBox {
                background-color: #f8f9fa;
                border: 2px solid #007BFF;
                border-radius: 10px;
                padding: 6px;
                font-size: 14px;
            }
            QComboBox:hover {
                border: 2px solid #0056b3;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                selection-background-color: #007BFF;
            }
        """)

        layout.addWidget(self.label_user)
        layout.addWidget(self.input_user)

        # Campo de senha
        self.label_password = QLabel("Senha:")
        self.input_password = QLineEdit()
        self.input_password.setEchoMode(QLineEdit.Password)  # Ocultar senha

        # Estilo para campo de senha
        self.input_password.setStyleSheet("""
            QLineEdit {
                border: 2px solid #007BFF;
                border-radius: 10px;
                padding: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0056b3;
            }
        """)

        layout.addWidget(self.label_password)
        layout.addWidget(self.input_password)

        # Botão de login estilizado
        self.btn_login = QPushButton("Entrar")
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                font-size: 14px;
                border-radius: 10px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004494;
            }
        """)
        self.btn_login.clicked.connect(self.validate_login)
        layout.addWidget(self.btn_login)

        self.setLayout(layout)

        # Aplicar animação de fade-in ao abrir a janela
        self.apply_fade_in_animation()

    def load_users(self):
        """ Carrega usuários do banco de dados e preenche a ComboBox """
        try:
            users = get_users()
            if users:
                self.input_user.addItems(users)
            else:
                self.input_user.addItem("Nenhum usuário cadastrado")
                self.input_user.setEnabled(False)  # 🔹 Desativa o campo se não houver usuários
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar usuários: {str(e)}")
            self.input_user.addItem("Erro ao carregar usuários")
            self.input_user.setEnabled(False)  # 🔹 Desativa o campo em caso de erro

    def apply_fade_in_animation(self):
        """ Animação de fade-in ao iniciar a tela de login """
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)  # Inicia completamente invisível

        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(10000)  # Tempo do efeito (ms)
        self.animation.setStartValue(0.0)  # Começa invisível
        self.animation.setEndValue(1.0)  # Fica totalmente visível
        self.animation.start()

    def validate_login(self):
        """ Valida o login verificando o banco de dados """
        try:
            username = self.input_user.currentText().strip()
            password = self.input_password.text().strip()

            if username == "Nenhum usuário cadastrado":
                QMessageBox.warning(self, "Erro de Login", "Nenhum usuário cadastrado. Contate o administrador!")
                return

            user = check_login(username, password)

            if user:
                try:
                    user_id = user["id"]
                    is_admin = user["is_admin"]
                    is_fiscal = user.get("is_fiscal", False)  # 🔹 Certifica que `is_fiscal` sempre está presente
                    is_visitor = not (is_admin or is_fiscal)  # 🔹 Se não for admin nem fiscal, é visitante!

                except KeyError as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao processar os dados do usuário: {str(e)}")
                    print(f"[ERROR] Erro ao processar dados do usuário: {e}")
                    return

                QMessageBox.information(self, "Login Bem-Sucedido", f"Bem-vindo(a), {username}!")

                # ✅ Armazena corretamente `is_visitor`
                self.user_info = {
                    "username": username,
                    "is_admin": is_admin,
                    "is_fiscal": is_fiscal,
                    "is_visitor": is_visitor
                }

                self.accept()  # Fecha a janela de login e abre o MainApp

            else:
                QMessageBox.warning(self, "Erro de Login", "Usuário ou senha incorretos! Tente novamente.")
                print(f"[ERROR] Login inválido para usuário: {username}")

                # 🔹 Limpa apenas o campo de senha para tentar novamente
                self.input_password.clear()

        except Exception as e:
            QMessageBox.critical(self, "Erro Crítico", f"Ocorreu um erro inesperado ao tentar fazer login:\n{str(e)}")
            print(f"[ERROR] Erro inesperado ao fazer login: {e}")


def main():
    """ Inicia a aplicação com a tela de login """
    try:
        verificar_atualizacao()  # ⬅️ ADICIONE AQUI
        app = QApplication(sys.argv)
        login_window = LoginWindow()

        if login_window.exec_() == QDialog.Accepted:
            main_window = MainApp(login_window.user_info)
            main_window.show()
            sys.exit(app.exec_())
    except Exception as e:
        print(f"[ERROR] Erro inesperado na aplicação: {str(e)}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado: {str(e)}")



if __name__ == "__main__":
    main()
