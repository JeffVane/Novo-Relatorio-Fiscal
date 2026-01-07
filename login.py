import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QGraphicsOpacityEffect)
from PyQt5.QtGui import QIcon, QPixmap,QMovie
from PyQt5.QtCore import QPropertyAnimation, Qt,QTimer,QSize,QThread,pyqtSignal
from PyQt5.QtWidgets import QMessageBox
from db import check_login, get_users  # Buscar usuários do banco de dados
from main import MainApp  # Importa a tela principal
import os
from db import connect_db
import sys
import os
import subprocess
import requests
import tempfile
import os
import ctypes
import sys
from PyQt5.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt5.QtCore import QEventLoop
from packaging.version import Version, InvalidVersion


# ---------------- Configurações ----------------
REPO_OWNER = "JeffVane"
REPO_NAME = "Novo-Relatorio-Fiscal"
BRANCH = "main"

VERSION_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/version.txt"
LOCAL_VERSION_FILE = "version.txt"

# GitHub API (latest release)
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

# Nome do instalador que você sobe no Release
INSTALLER_ASSET_NAME = "Instalador_RelatorioFiscal.exe"
# ----------------------------------------------


def get_remote_version():
    try:
        r = requests.get(VERSION_URL, timeout=10)
        r.raise_for_status()
        return r.text.strip()
    except:
        return None


def get_local_version():
    try:
        with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "0.0.0"


def parse_version(v: str) -> Version:
    # garante comparação correta (1.10.0 > 1.2.0)
    try:
        return Version(v.strip())
    except InvalidVersion:
        # se vier algo estranho no version.txt, evita crash
        return Version("0.0.0")


def get_latest_installer_url():
    """
    Busca o último release e encontra a URL do asset do instalador.
    """
    r = requests.get(LATEST_RELEASE_API, timeout=10)
    r.raise_for_status()
    data = r.json()

    assets = data.get("assets", [])
    for a in assets:
        if a.get("name") == INSTALLER_ASSET_NAME:
            return a.get("browser_download_url")

    raise RuntimeError(f"Asset '{INSTALLER_ASSET_NAME}' não encontrado no Latest Release.")


class DownloadThread(QThread):
    progress_update = pyqtSignal(int, float, float)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url

    def run(self):
        try:
            temp_dir = tempfile.gettempdir()
            installer_path = os.path.join(temp_dir, INSTALLER_ASSET_NAME)

            with requests.get(self.download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                total = int(r.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 2 * 1024 * 1024  # 2 MB

                with open(installer_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total > 0:
                                percent = int((downloaded / total) * 100)
                                mb_downloaded = downloaded / (1024 * 1024)
                                mb_total = total / (1024 * 1024)
                                self.progress_update.emit(percent, mb_downloaded, mb_total)

            self.finished.emit(installer_path)

        except Exception as e:
            self.error.emit(str(e))


def verificar_atualizacao():
    remote_txt = get_remote_version()
    local_txt = get_local_version()

    if not remote_txt:
        return False  # sem internet / sem version.txt

    remote = parse_version(remote_txt)
    local = parse_version(local_txt)

    # Só atualiza se for realmente maior
    if remote <= local:
        return False

    if not QApplication.instance():
        _ = QApplication(sys.argv)

    resposta = QMessageBox.question(
        None,
        "Atualização disponível",
        f"Uma nova versão do sistema está disponível!\n\n"
        f"Versão atual: {local}\nNova versão: {remote}\n\n"
        f"Deseja baixar e instalar agora?",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.Yes
    )

    if resposta != QMessageBox.Yes:
        return False

    try:
        installer_url = get_latest_installer_url()
    except Exception as e:
        QMessageBox.critical(None, "Erro", f"Não foi possível localizar o instalador no GitHub Releases:\n{e}")
        return False

    progress = QProgressDialog("Preparando download...", "Cancelar", 0, 100)
    progress.setWindowTitle("Baixando Atualização")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumWidth(420)
    progress.setValue(0)
    progress.show()

    thread = DownloadThread(installer_url)

    def atualizar_barra(percent, mb_down, mb_total):
        progress.setValue(percent)
        progress.setLabelText(f"Baixando: {mb_down:.1f} MB de {mb_total:.1f} MB")

    def ao_finalizar(caminho):
        progress.close()
        ctypes.windll.shell32.ShellExecuteW(None, "runas", caminho, None, None, 1)
        sys.exit(0)

    def ao_errar(mensagem):
        progress.close()
        QMessageBox.critical(None, "Erro", f"Erro ao baixar instalador:\n{mensagem}")
        loop.quit()

    thread.progress_update.connect(atualizar_barra)
    thread.finished.connect(ao_finalizar)
    thread.error.connect(ao_errar)

    loop = QEventLoop()
    thread.finished.connect(loop.quit)
    thread.error.connect(loop.quit)

    thread.start()
    loop.exec_()

    return True



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

                # Fecha a janela de login
                self.close()

                # Exibe a tela de carregamento
                loading = LoadingScreen()
                if loading.exec_() == QDialog.Accepted:
                    self.accept()  # Sinaliza que o login foi bem-sucedido para abrir a MainApp
            # Fecha a janela de login e abre o MainApp

            else:
                QMessageBox.warning(self, "Erro de Login", "Usuário ou senha incorretos! Tente novamente.")
                print(f"[ERROR] Login inválido para usuário: {username}")

                # 🔹 Limpa apenas o campo de senha para tentar novamente
                self.input_password.clear()

        except Exception as e:
            QMessageBox.critical(self, "Erro Crítico", f"Ocorreu um erro inesperado ao tentar fazer login:\n{str(e)}")
            print(f"[ERROR] Erro inesperado ao fazer login: {e}")


def main():
    try:
        app = QApplication(sys.argv)

        # ⬇️ Chama o verificador, e impede que a aplicação continue até terminar
        atualizado = verificar_atualizacao()
        if not atualizado:  # Só continua se não foi atualizado agora
            login_window = LoginWindow()
            if login_window.exec_() == QDialog.Accepted:
                main_window = MainApp(login_window.user_info)
                main_window.show()
                sys.exit(app.exec_())
        else:
            sys.exit(0)  # já reiniciou a aplicação via instalador

    except Exception as e:
        print(f"[ERROR] Erro inesperado na aplicação: {str(e)}")
        QMessageBox.critical(None, "Erro Crítico", f"Erro inesperado: {str(e)}")


class LoadingScreen(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Carregando sistema...")
        self.setFixedSize(250, 250)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setStyleSheet("background-color: white;")
        self.setWindowIcon(QIcon("crc.ico"))

        layout = QVBoxLayout()

        # Label que exibirá o GIF
        self.label_animation = QLabel(self)
        self.label_animation.setAlignment(Qt.AlignCenter)

        self.movie = QMovie("loading.gif")
        self.movie.setScaledSize(QSize(100, 100))  # Ajuste o tamanho do GIF aqui
        self.label_animation.setMovie(self.movie)

        layout.addWidget(self.label_animation)

        # Texto opcional abaixo do GIF
        label_text = QLabel("Inicializando...")
        label_text.setAlignment(Qt.AlignCenter)
        label_text.setStyleSheet("font-size: 14px; color: #333;")
        layout.addWidget(label_text)

        self.setLayout(layout)
        self.movie.start()

        # Simula tempo de carregamento
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.accept)
        self.timer.start(3000)



if __name__ == "__main__":
    main()
