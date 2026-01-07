import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout,
    QStackedWidget, QListWidget, QGraphicsOpacityEffect, QMessageBox
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, QPropertyAnimation
from atribuir import AtribuirTab
from relatorio_atribuicoes import RelatorioAtribuicoesTab
from resultados_fiscal import ResultadosFiscalTab  # 🔹 Importando a nova aba
from db import get_user_permissions, get_user_id
from admin_tab import AdminTab
from resultado_mensal import ResultadoMensalTab
from resultado_mensal_crcdf import ResultadoMensalCRCDFTab
from log_acoes import LogAcoesTab


import sys
import traceback

def excecao_global(exctype, value, tb):
    print("EXCEÇÃO NÃO CAPTURADA:")
    traceback.print_exception(exctype, value, tb)

sys.excepthook = excecao_global


class FadingMenu(QWidget):
    """ Menu lateral moderno com tema escuro e animação fade, com zoom em hover. """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)  # 🔸 Aumentado para mais espaço nos nomes

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #CCCCCC;
                border-right: 1px solid #1f1f1f;
            }

            QListWidget {
                border: none;
                padding: 10px;
                background-color: transparent;
                font-size: 16px;
            }

            QListWidget::item {
                padding: 12px 14px;
                margin-bottom: 6px;
                border-radius: 6px;
                color: #002ebd;
                background-color: transparent;
                transition: background-color 0.3s ease, font-size 0.2s ease;
            }

            QListWidget::item:selected {
                background-color: #2e86de;
                color: white;
            }

            QListWidget::item:hover {
                background-color: #2e86de;
                color: white;
                font-size: 17px;
            }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.menu_list = QListWidget()
        self.layout.addWidget(self.menu_list)

        # Efeito de opacidade
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        # Animação
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.animation.setDuration(200)

        self.menu_open = False
        self.setVisible(False)

    def fade_in(self):
        if not self.menu_open:
            self.opacity_effect.setOpacity(0.0)
            self.setVisible(True)
            self.animation.stop()
            self.animation.setStartValue(0.0)
            self.animation.setEndValue(1.0)
            try:
                self.animation.finished.disconnect()
            except TypeError:
                pass
            self.animation.finished.connect(self.set_menu_open)
            self.animation.start()

    def fade_out(self):
        if self.menu_open:
            self.animation.stop()
            self.animation.setStartValue(1.0)
            self.animation.setEndValue(0.0)
            try:
                self.animation.finished.disconnect()
            except TypeError:
                pass
            self.animation.finished.connect(self.hide_and_reset)
            self.animation.start()

    def hide_and_reset(self):
        self.setVisible(False)
        self.menu_open = False

    def set_menu_open(self):
        self.menu_open = True


class MainApp(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()

        self.user_info = user_info or {"username": "desconhecido", "is_admin": False, "is_visitor": False}
        self.user_info.setdefault("is_visitor", False)

        self.page_resultado_mensal = ResultadoMensalTab(self.user_info)
        self.page_resultado_mensal_crcdf = ResultadoMensalCRCDFTab(self.user_info)
        self.page_resultados_fiscal = ResultadosFiscalTab(self.user_info)
        self.page_relatorio_atribuicoes = RelatorioAtribuicoesTab(self.user_info)
        self.page_resultados_fiscal.metas_atualizadas.connect(self.atualizar_resultado_mensal)

        self.page_atribuir = AtribuirTab(self.user_info)

        # 🔹 Conectar sinais de atualização
        self.page_resultados_fiscal.metas_atualizadas.connect(self.atualizar_resultado_mensal)
        self.page_relatorio_atribuicoes.atualizar_resultado_mensal.connect(
            self.page_resultado_mensal.load_resultado_mensal)
        self.page_relatorio_atribuicoes.atualizar_resultados_fiscal.connect(self.page_resultados_fiscal.load_data)

        # 🔹 Conectar os sinais da aba Atribuir
        self.page_atribuir.atualizar_resultados_fiscal.connect(self.page_resultados_fiscal.load_data)
        self.page_atribuir.atualizar_resultado_mensal.connect(self.page_resultado_mensal.load_resultado_mensal)
        self.page_atribuir.atualizar_resultado_mensal_crcdf.connect(
            self.page_resultado_mensal_crcdf.load_resultado_mensal)

        self.initUI()

    def initUI(self):
        try:
            self.setWindowTitle('S.I.A FISC CRCDF')
            self.setGeometry(100, 100, 1000, 600)
            self.setWindowIcon(QIcon("crc.ico"))

            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            main_layout = QHBoxLayout(self.central_widget)

            self.menu_widget = FadingMenu(self)
            self.menu_widget.hide()

            self.menu_button = QPushButton()
            self.menu_button.setIcon(QIcon("menu.png"))
            self.menu_button.setIconSize(QSize(20, 20))
            self.menu_button.setFixedSize(30, 30)
            self.menu_button.setStyleSheet("border: none; background: transparent;")
            self.menu_button.clicked.connect(self.toggle_menu)

            menu_button_layout = QVBoxLayout()
            menu_button_layout.addWidget(self.menu_button)
            menu_button_layout.addStretch()

            self.pages = QStackedWidget()
            self.admin_page = AdminTab(
                main_app=self,
                relatorio_atribuicoes_tab=self.page_relatorio_atribuicoes,  # <- precisa existir
                resultados_fiscal_tab=self.page_resultados_fiscal,
                resultado_mensal_tab=self.page_resultado_mensal,
                resultado_mensal_crcdf_tab=self.page_resultado_mensal_crcdf
            )

            self.all_pages = {
                "Atribuir": self.page_atribuir,
                "Relatório de Atribuições": self.page_relatorio_atribuicoes,
                "Resultados do Fiscal": self.page_resultados_fiscal,
                "Resultado Mensal": self.page_resultado_mensal,
                "Resultado Mensal - CRCDF": self.page_resultado_mensal_crcdf,
                "Administração": self.admin_page,
                "Log de Ações": LogAcoesTab()
            }

            user_id = get_user_id(self.user_info["username"]) if self.user_info else None
            if user_id is None:
                QMessageBox.critical(self, "Erro", "Não foi possível obter as permissões do usuário.")
                return

            self.permissions = get_user_permissions(user_id) or {}

            while self.pages.count() > 0:
                widget = self.pages.widget(0)
                self.pages.removeWidget(widget)
                widget.deleteLater()

            self.menu_widget.menu_list.clear()

            if self.user_info["is_admin"]:
                for tab_name, widget in self.all_pages.items():
                    self.pages.addWidget(widget)
                    self.menu_widget.menu_list.addItem(tab_name)



            elif self.user_info["is_visitor"]:

                nome_visivel = {

                    "Resultado Mensal": "Resultado Mensal - CFC",

                    "Resultado Mensal - CRCDF": "Resultado Mensal - CRCDF",

                    "Relatório de Atribuições": "Relatório de Atribuições",

                    "Resultados do Fiscal": "Resultados do Fiscal",

                }

                for tab_name, widget in self.all_pages.items():

                    if self.permissions.get(tab_name, False):
                        self.pages.addWidget(widget)

                        self.menu_widget.menu_list.addItem(nome_visivel.get(tab_name, tab_name))



            else:
                nome_visivel = {
                    "Atribuir": "Atribuir Procedimentos",
                    "Relatório de Atribuições": "Relatório de Atribuições",
                    "Resultados do Fiscal": "Resultados do Fiscal",
                    "Resultado Mensal": "Resultado Mensal - CFC",
                    "Resultado Mensal - CRCDF": "Resultado Mensal - CRCDF",
                    "Administração": "Painel de Administração",
                    "Log de Ações": "Histórico de Ações"
                }

                for tab_name, widget in self.all_pages.items():
                    if self.permissions.get(tab_name, False):
                        self.pages.addWidget(widget)
                        self.menu_widget.menu_list.addItem(nome_visivel.get(tab_name, tab_name))

                self.page_atribuir.atualizar_relatorio.connect(self.page_relatorio_atribuicoes.load_data)

            self.menu_widget.menu_list.itemClicked.connect(self.change_tab)
            main_layout.addWidget(self.menu_widget)
            main_layout.addLayout(menu_button_layout)
            main_layout.addWidget(self.pages)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro inesperado ao inicializar interface: {str(e)}")

    def atualizar_resultado_mensal(self):
        print("[SINAL RECEBIDO] Atualizando resultado mensal após alteração de metas")

        resultado_mensal_tab = self.page_resultado_mensal  # ou self.all_pages.get("Resultado Mensal")
        resultado_mensal_crcdf_tab = self.page_resultado_mensal_crcdf
        self.page_resultados_fiscal.load_data()

        if resultado_mensal_tab and hasattr(resultado_mensal_tab, 'load_resultado_mensal'):
            resultado_mensal_tab.load_resultado_mensal()

        if resultado_mensal_crcdf_tab and hasattr(resultado_mensal_crcdf_tab, 'load_resultado_mensal'):
            resultado_mensal_crcdf_tab.load_resultado_mensal()
            # E conectar assim:
            self.page_relatorio_atribuicoes.atualizar_resultados_fiscal.connect(
                self.recarregar_resultados_fiscal
            )

    def recarregar_resultados_fiscal(self):
        try:
            print("[SINAL RECEBIDO] Atualizando resultados fiscais via recarregar_resultados_fiscal()")
            if hasattr(self, 'page_resultados_fiscal'):
                self.page_resultados_fiscal.load_data()
        except Exception as e:
            import traceback
            print("[ERRO ao recarregar resultados fiscais]:", traceback.format_exc())

    def toggle_menu(self):
        """ Alterna a visibilidade do menu lateral com animação """
        if not self.menu_widget.menu_open:
            self.menu_widget.fade_in()
        else:
            self.menu_widget.fade_out()

    def change_tab(self, item):
        """ Alterna entre as abas ao clicar no menu e fecha o menu com animação """
        index = self.menu_widget.menu_list.row(item)
        self.pages.setCurrentIndex(index)
        self.menu_widget.fade_out()

def main():
    app = QApplication(sys.argv)
    ex = MainApp()
    ex.show()
    sys.exit(app.exec_())

    # Adicionar este método para atualizar a aba de resultado mensal



if __name__ == '__main__':
    main()
