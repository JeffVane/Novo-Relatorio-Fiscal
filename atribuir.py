from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QMessageBox,
                             QDialog, QFormLayout, QLineEdit, QLabel, QComboBox, QCheckBox,QGridLayout,QListWidget,QListWidgetItem,QSizePolicy,QStackedLayout,QProgressBar,QTabWidget)
from PyQt5.QtGui import QIcon,QIntValidator
from PyQt5.QtCore import QSize, Qt, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebEngineWidgets import QWebEngineDownloadItem
from PyQt5.QtWidgets import QApplication
import os
from PyQt5.QtGui import QMovie

import pandas as pd
from db import get_procedures, insert_agendamento, assign_procedure, connect_db
from db import registrar_log

class CancelReasonDialog(QDialog):
    """ Janela para inserir o motivo do cancelamento """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Motivo do Cancelamento")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        self.label = QLabel("Informe o motivo do cancelamento:")
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Digite o motivo...")

        self.save_button = QPushButton("Salvar")
        self.save_button.clicked.connect(self.accept)

        layout.addWidget(self.label)
        layout.addWidget(self.reason_input)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

    def get_reason(self):
        """ Retorna o motivo inserido pelo usuário """
        return self.reason_input.text().strip()

class AddAgendamentoDialog(QDialog):
    """ Janela para adicionar um novo agendamento manualmente """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Agendamento Manualmente")
        self.setFixedSize(550, 300)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Campo Data
        self.data_conclusao = QLineEdit()
        self.data_conclusao.setPlaceholderText("DD-MM-YYYY")
        self.data_conclusao.textChanged.connect(self.format_date_input)

        # Campos do formulário
        self.numero_agendamento = QLineEdit()

        self.fiscal = QLineEdit()
        self.fiscal.setReadOnly(True)  # 🔒 Campo não editável
        if parent and hasattr(parent, "user_info"):
            self.fiscal.setText(parent.user_info.get("username", "").strip())  # 🔹 Preenche com o fiscal logado

        self.tipo_registro = QLineEdit()
        self.numero_registro = QLineEdit()
        self.nome = QLineEdit()

        # Layout do formulário
        form_layout.addRow(QLabel("Data Conclusão:"), self.data_conclusao)
        form_layout.addRow(QLabel("Número Agendamento:"), self.numero_agendamento)
        form_layout.addRow(QLabel("Fiscal:"), self.fiscal)
        form_layout.addRow(QLabel("Tipo Registro:"), self.tipo_registro)
        form_layout.addRow(QLabel("Número Registro:"), self.numero_registro)
        form_layout.addRow(QLabel("Nome:"), self.nome)

        layout.addLayout(form_layout)

        # Botões
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Salvar")
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_save.clicked.connect(self.save_data)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def format_date_input(self):
        """Formata o campo de data para inserir '-' automaticamente."""
        text = self.data_conclusao.text()

        # Remove qualquer caractere não numérico
        text = ''.join(filter(str.isdigit, text))

        # Formata para 'DD-MM-YYYY'
        if len(text) > 2:
            text = text[:2] + '-' + text[2:]
        if len(text) > 5:
            text = text[:5] + '-' + text[5:]
        if len(text) > 10:
            text = text[:10]  # Limita o comprimento máximo a 'DD-MM-YYYY'

        # Atualiza o texto no campo de entrada
        self.data_conclusao.blockSignals(True)  # Evita loops infinitos
        self.data_conclusao.setText(text)
        self.data_conclusao.blockSignals(False)

    def save_data(self):
        """Salva os dados inseridos pelo usuário na tabela da aba 'Atribuir'."""
        try:
            agendamento_data = self.get_data()

            # Validação dos campos
            missing_fields = [key for key, value in agendamento_data.items() if not value]
            if missing_fields:
                QMessageBox.warning(
                    self,
                    "Erro",
                    f"Os seguintes campos estão vazios: {', '.join(missing_fields)}"
                )
                return

            # Validação de formato de data
            if not self.validate_date(agendamento_data["Data Conclusão"]):
                QMessageBox.warning(
                    self,
                    "Erro",
                    "A data de conclusão deve estar no formato DD-MM-YYYY."
                )
                return

            # Validação do número de agendamento
            if not agendamento_data["Número Agendamento"].isdigit():
                QMessageBox.warning(
                    self,
                    "Erro",
                    "O número do agendamento deve conter apenas números."
                )
                return

            # Atualizar a tabela da aba 'Atribuir'
            if hasattr(self.parent(), "add_agendamento_to_table"):
                self.parent().add_agendamento_to_table(agendamento_data)
                print(f"[DEBUG] Agendamento adicionado à tabela da aba 'Atribuir': {agendamento_data}")

            # 🔹 Registrar log da ação
            fiscal_nome = agendamento_data["Fiscal"].strip()
            detalhes = (
                f"Data: {agendamento_data['Data Conclusão']}, "
                f"Nº Agendamento: {agendamento_data['Número Agendamento']}, "
                f"Tipo Registro: {agendamento_data['Tipo Registro']}, "
                f"Nº Registro: {agendamento_data['Número Registro']}, "
                f"Nome: {agendamento_data['Nome']}"
            )
            registrar_log(usuario=fiscal_nome, acao="Inclusão de agendamento manual", detalhes=detalhes)

            # Mensagem final
            QMessageBox.information(self, "Sucesso", "Agendamento adicionado com sucesso!")
            self.close()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro inesperado: {e}")
            print(f"[ERRO] Erro inesperado: {e}")

    def validate_date(self, date_str):
        """Valida se a data está no formato DD-MM-YYYY."""
        from datetime import datetime
        try:
            datetime.strptime(date_str, "%d-%m-%Y")
            return True
        except ValueError:
            return False

    def get_data(self):
        """ Retorna os dados inseridos pelo usuário """
        return {
            "Data Conclusão": self.data_conclusao.text(),
            "Número Agendamento": self.numero_agendamento.text(),
            "Fiscal": self.fiscal.text(),
            "Tipo Registro": self.tipo_registro.text(),
            "Número Registro": self.numero_registro.text(),
            "Nome": self.nome.text()
        }

class AssignMultipleProceduresDialog(QDialog):
    def __init__(self, agendamento_data, user_info, parent=None):
        super().__init__(parent)
        self.agendamento = agendamento_data  # Certifique-se de armazenar corretamente
        self.user_info = user_info  # Certifique-se de armazenar corretamente

        self.quantity_widgets = {}  # Para armazenar os campos de entrada das quantidades

        self.setWindowTitle("Atribuir Procedimentos ao Agendamento")
        self.setFixedSize(1200, 500)

        # Validar os dados do agendamento
        if not isinstance(self.agendamento, dict) or "Número Agendamento" not in self.agendamento:
            QMessageBox.critical(self, "Erro", "Dados do agendamento estão inválidos ou incompletos.")
            self.reject()
            return

        self.procedures = get_procedures()  # Carrega os procedimentos do banco

        if not self.procedures:
            QMessageBox.warning(self, "Erro", "Nenhum procedimento disponível para atribuição.")
            self.reject()
            return

        # Chama a função init_ui() correta
        self.init_ui()

    def init_ui(self):
        """Configura a interface principal."""
        layout = QVBoxLayout()

        # Título e instruções
        instructions = QLabel(
            f"Selecione os procedimentos e insira a quantidade para o agendamento {self.agendamento['Número Agendamento']}:")
        instructions.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(instructions)

        # Lista de procedimentos com checkboxes
        self.list_widget = QListWidget()

        # 🔹 Limpa a lista antes de adicionar novos itens para evitar duplicação
        self.list_widget.clear()

        # 🔹 Conjunto para evitar duplicatas
        procedures_in_list = set()

        for procedure in self.procedures:
            procedure_name = procedure["name"]

            if procedure_name in procedures_in_list:
                continue  # Pula se já estiver na lista

            procedures_in_list.add(procedure_name)
            item = QListWidgetItem(procedure_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, procedure)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # Área para campos de quantidade
        self.quantity_form = QFormLayout()
        self.quantity_widgets = {}

        # Atualiza os campos de quantidade com base na seleção
        self.list_widget.itemChanged.connect(self.update_quantity_fields)

        quantity_widget_container = QWidget()
        quantity_widget_container.setLayout(self.quantity_form)
        layout.addWidget(quantity_widget_container)

        # Botões de ação
        btn_layout = QHBoxLayout()

        self.btn_save = QPushButton("Salvar")
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")

        self.btn_save.clicked.connect(self.save_assignments)
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def update_quantity_fields(self, item):
        """ Adiciona ou remove campos de quantidade com base na seleção e evita duplicação. """
        procedure = item.data(Qt.UserRole)
        procedure_name = procedure["name"]

        if item.checkState() == Qt.Checked:
            if procedure_name.lower() == "cancelado":
                # 🔹 Se for "Cancelado", abrir a janela de motivo
                if procedure_name in self.quantity_widgets:
                    return  # Já existe, não adiciona novamente

                dialog = CancelReasonDialog(self)
                if dialog.exec_():
                    reason = dialog.get_reason()
                    if not reason:
                        QMessageBox.warning(self, "Erro", "O motivo do cancelamento não pode ser vazio.")
                        item.setCheckState(Qt.Unchecked)  # Desmarca a opção
                        return

                    # Salvar o motivo no dicionário para evitar duplicação
                    self.quantity_widgets[procedure_name] = ("Motivo:", reason)

                    # Criar um rótulo para exibir o motivo
                    procedure_label = QLabel(f"{procedure_name}: {reason}")
                    procedure_label.setStyleSheet("font-weight: bold; font-size: 14px; color: red;")

                    self.quantity_form.addRow(procedure_label)
            else:
                # 🔹 Evita adicionar um campo duplicado
                if procedure_name in self.quantity_widgets:
                    return  # Já existe, não adiciona novamente

                # Criar campo de quantidade para os demais procedimentos
                quantity_input = QLineEdit()
                quantity_input.setPlaceholderText("Quantidade")
                quantity_input.setValidator(QIntValidator())  # Aceitar apenas números
                quantity_input.setStyleSheet("font-weight: bold; font-size: 14px;")

                procedure_label = QLabel(procedure_name)
                procedure_label.setStyleSheet("font-weight: bold; font-size: 14px;")

                # Adiciona ao dicionário de widgets
                self.quantity_widgets[procedure_name] = (procedure_label, quantity_input)
                self.quantity_form.addRow(procedure_label, quantity_input)

                font = item.font()
                font.setBold(True)
                item.setFont(font)
        else:
            # 🔹 Remover o campo de quantidade ou motivo se o item for desmarcado
            if procedure_name in self.quantity_widgets:
                procedure_label, _ = self.quantity_widgets.pop(procedure_name)
                self.quantity_form.removeRow(procedure_label)

                font = item.font()
                font.setBold(False)
                item.setFont(font)

    def save_assignments(self):
        """Salva os procedimentos e quantidades no banco de dados e registra no log."""
        try:
            procedures_quantities = []

            for procedure_name, (procedure_label, value) in self.quantity_widgets.items():
                if procedure_name.lower() == "cancelado":
                    procedures_quantities.append((procedure_name, value))  # O motivo já é um texto
                else:
                    quantity = value.text().strip()
                    if not quantity.isdigit() or int(quantity) <= 0:
                        QMessageBox.warning(self, "Erro",
                                            f"A quantidade para {procedure_name} deve ser um número válido!")
                        return
                    procedures_quantities.append((procedure_name, int(quantity)))

            if not procedures_quantities:
                QMessageBox.warning(self, "Erro",
                                    "Selecione pelo menos um procedimento e insira uma quantidade válida.")
                return

            print(f"[DEBUG] Salvando os procedimentos: {procedures_quantities}")

            # Passa o nome do usuário logado corretamente para a função
            assign_procedure(self.user_info["username"], self.agendamento, procedures_quantities)

            # 🔹 REGISTRA A AÇÃO NO LOG
            from db import registrar_log
            usuario = self.user_info["username"]
            numero_agendamento = self.agendamento.get("Número Agendamento", "desconhecido")
            fiscal = self.agendamento.get("Fiscal", "desconhecido")

            detalhes = f"Procedimentos atribuídos ao agendamento {numero_agendamento} do fiscal {fiscal}: "

            partes = []
            for nome, valor in procedures_quantities:
                if isinstance(valor, str):  # caso seja cancelado com motivo
                    partes.append(f"{nome} (motivo: {valor})")
                else:
                    partes.append(f"{nome} (quantidade: {valor})")

            detalhes += ", ".join(partes)

            registrar_log(usuario, "Atribuição de procedimentos", detalhes)

            # ⬇️⬇️ AQUI: EMITINDO OS SINAIS para recarregar as abas
            if self.parent():
                self.parent().atualizar_relatorio.emit()
                self.parent().atualizar_resultados_fiscal.emit()
                self.parent().atualizar_resultado_mensal.emit()
                self.parent().atualizar_resultado_mensal_crcdf.emit()

            QMessageBox.information(self, "Sucesso", "Procedimentos atribuídos com sucesso!")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao salvar os procedimentos:\n{str(e)}")
            print(f"[ERRO] {e}")

    def clear_layout(self, layout):
        """ Remove todos os widgets de um layout """
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())


class AtribuirTab(QWidget):
    atualizar_relatorio = pyqtSignal()
    atualizar_resultados_fiscal = pyqtSignal()
    atualizar_resultado_mensal = pyqtSignal()
    atualizar_resultado_mensal_crcdf = pyqtSignal()

    # 🔹 Sinal para atualizar a aba "Relatório de Atribuições"
    def __init__(self, user_info=None):  # Agora aceita user_info
        super().__init__()
        self.user_info = user_info  # Guarda info do usuário logado
        self.loading_indicator = None  # Inicializa o indicador de carregamento
        self.initUI()

    def initUI(self):
        layout_principal = QVBoxLayout()

        # ✅ Título da Página
        self.title_label = QLabel("✅ Atribuir Procedimentos")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 6px;")
        layout_principal.addWidget(self.title_label)

        # ➕ Botões de Ação e Opções - todos na mesma linha
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.setSpacing(10)

        # Botão Adicionar Agendamento
        self.addAgendamentoButton = QPushButton("Adicionar Agendamento")
        self.addAgendamentoButton.setIcon(QIcon("add.png"))
        self.addAgendamentoButton.setIconSize(QSize(14, 14))
        self.addAgendamentoButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.addAgendamentoButton.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        self.addAgendamentoButton.clicked.connect(self.add_manual_agendamento)
        top_buttons_layout.addWidget(self.addAgendamentoButton)

        # Botão Atribuir Procedimento(s)
        self.assignButton = QPushButton("Atribuir Procedimento(s)")
        self.assignButton.setIcon(QIcon("atribuir.png"))
        self.assignButton.setIconSize(QSize(14, 14))
        self.assignButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.assignButton.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-size: 11px;
                font-weight: bold;
                padding: 5px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.assignButton.clicked.connect(self.open_assign_procedure_dialog)
        top_buttons_layout.addWidget(self.assignButton)

        # ⚙️ Botão de opções
        self.optionsButton = QPushButton()
        self.optionsButton.setIcon(QIcon('config.png'))
        self.optionsButton.setIconSize(QSize(16, 16))
        self.optionsButton.setFixedSize(30, 30)
        self.optionsButton.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.optionsMenu = QMenu()
        self.loadSheetAction = self.optionsMenu.addAction(QIcon("xlsx.png"), "Carregar Planilha")
        self.loadSheetAction.triggered.connect(self.load_spreadsheet)
        self.openExternalWebsiteAction = self.optionsMenu.addAction(QIcon("web.png"),
                                                                    "Fiscalização Eletrônica (Externo)")
        self.openExternalWebsiteAction.triggered.connect(self.open_external_website)
        self.openInternalWebsiteAction = self.optionsMenu.addAction(QIcon("web.png"),
                                                                    "Fiscalização Eletrônica (Interno)")
        self.openInternalWebsiteAction.triggered.connect(self.open_internal_website)
        self.optionsButton.setMenu(self.optionsMenu)
        top_buttons_layout.addWidget(self.optionsButton)

        # Adicione um espaçador
        top_buttons_layout.addStretch(1)

        layout_principal.addLayout(top_buttons_layout)

        # Usar QStackedLayout para alternar entre a tabela, o webview e o loading
        self.stacked_layout = QStackedLayout()

        # 🧾 Tabela
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data Conclusão", "Número Agendamento", "Fiscal",
            "Tipo Registro", "Número Registro", "Nome"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        column_widths = [120, 150, 150, 120, 120, 200]
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: #002060;
                color: white;
                font-weight: bold;
                padding: 3px;
                border: 1px solid white;
            }
        """)
        self.table_widget = QWidget()
        table_layout = QVBoxLayout()
        table_layout.addWidget(self.table)
        self.table_widget.setLayout(table_layout)
        self.stacked_layout.addWidget(self.table_widget)
        self.table_index = 0  # Guarda o índice da tabela

        # 🌐 Área para o navegador web
        self.webview = QWebEngineView()
        self.webview.page().profile().downloadRequested.connect(self.handle_download)
        self.webview.loadFinished.connect(self.hide_loading_indicator)  # Esconde ao terminar o carregamento
        self.webview_widget = QWidget()
        webview_layout = QVBoxLayout()
        webview_layout.addWidget(self.webview)
        self.webview_widget.setLayout(webview_layout)
        self.stacked_layout.addWidget(self.webview_widget)
        self.webview_index = 1  # Guarda o índice do webview

        # ⏳ Indicador de carregamento
        self.loading_indicator = QProgressBar()
        self.loading_indicator.setRange(0, 0)  # Modo indeterminado
        self.loading_indicator.setAlignment(Qt.AlignCenter)
        self.loading_indicator.setStyleSheet("QProgressBar::chunk { background-color: #007bff; }")  # Azul primário
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout()
        loading_layout.addWidget(self.loading_indicator)
        self.loading_widget.setLayout(loading_layout)
        self.stacked_layout.addWidget(self.loading_widget)
        self.loading_index = 2  # Guarda o índice do loading

        layout_principal.addLayout(self.stacked_layout)

        self.setLayout(layout_principal)

        # Inicialmente, mostra a tabela
        self.stacked_layout.setCurrentIndex(self.table_index)

    def show_loading_indicator(self):
        """ Mostra o indicador de carregamento (ProgressBar) """
        print("[DEBUG] Mostrando indicador de carregamento (ProgressBar)")
        try:
            self.stacked_layout.setCurrentIndex(self.loading_index)
            self.loading_indicator.setVisible(True)
        except Exception as e:
            print(f"[ERRO] Ocorreu um erro em show_loading_indicator: {e}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao mostrar o indicador de carregamento:\n{e}")

    def hide_loading_indicator(self, ok):
        """ Esconde o indicador de carregamento (ProgressBar) """
        print(f"[DEBUG] Escondendo indicador de carregamento (ProgressBar). Sucesso: {ok}")
        try:
            self.loading_indicator.setVisible(False)
            if ok:
                self.stacked_layout.setCurrentIndex(self.webview_index)
            else:
                self.stacked_layout.setCurrentIndex(self.webview_index)
                QMessageBox.critical(self, "Erro ao Carregar Página", "Ocorreu um erro ao carregar a página da web.")
        except Exception as e:
            print(f"[ERRO] Ocorreu um erro em hide_loading_indicator: {e}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao esconder o indicador de carregamento:\n{e}")

    def handle_download(self, download):
        """Controla downloads do QWebEngineView com segurança total."""
        try:
            if download.state() != download.DownloadRequested:
                print("[INFO] Download ignorado: estado diferente de 'Requested'")
                return

            suggested_filename = download.suggestedFileName()
            print(f"[DEBUG] Nome sugerido para download: {suggested_filename}")

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Arquivo",
                os.path.join(os.path.expanduser("~"), suggested_filename)
            )

            if not path:
                print("[INFO] Usuário cancelou o salvamento do arquivo.")
                download.cancel()
                return

            print(f"[INFO] Caminho escolhido: {path}")
            download.setPath(path)
            download.accept()

            # Protege referência para não ser coletada
            self._current_download = download

            def on_download_finished():
                try:
                    if download.state() == download.DownloadCompleted:
                        QMessageBox.information(self, "Download Concluído", f"Arquivo salvo em:\n{path}")
                    elif download.state() == download.DownloadCancelled:
                        QMessageBox.warning(self, "Download Cancelado", "O download foi cancelado.")
                    else:
                        QMessageBox.critical(self, "Erro", "O download não foi concluído com sucesso.")
                except Exception as e:
                    print(f"[ERRO] Dentro do on_download_finished: {e}")
                    QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao finalizar o download:\n{e}")
                finally:
                    self._current_download = None

            # Conecta finalização com tratamento de erro
            download.finished.connect(on_download_finished)

        except Exception as e:
            print(f"[ERRO] Falha ao iniciar o download: {e}")
            QMessageBox.critical(self, "Erro", f"Falha ao tentar iniciar o download:\n{e}")

    def open_external_website(self):
        """ Abre o website externo no navegador padrão """
        QDesktopServices.openUrl(QUrl("https://crcdf.cfc.org.br/spwDF/scc/login.aspx"))

    def open_internal_website(self):
        """ Abre o website interno dentro da aba e ocupa o espaço """
        print("[DEBUG] open_internal_website chamado")
        self.show_loading_indicator()  # Mostra o indicador de carregamento PRIMEIRO
        try:
            self.webview.load(QUrl("https://crcdf.cfc.org.br/spwDF/scc/login.aspx"))
            # NÃO altere o índice para webview aqui. O sinal loadFinished fará isso.
        except Exception as e:
            print(f"[ERRO] Ocorreu um erro ao carregar a página interna: {e}")
            QMessageBox.critical(self, "Erro ao Carregar Página", f"Ocorreu um erro ao carregar a página da web:\n{e}")
            self.stacked_layout.setCurrentIndex(self.table_index)  # Retorna para a tabela em caso de erro
            self.hide_loading_indicator(False)  # Garante que o indicador seja escondido

    def load_spreadsheet(self):
        """ Carrega a planilha Excel e exibe os dados na tabela """
        try:
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getOpenFileName(self, "Carregar Planilha", "", "Excel Files (*.xls *.xlsx)",
                                                      options=options)

            if not fileName:
                return

            if not fileName.lower().endswith(('.xls', '.xlsx')):
                QMessageBox.warning(self, "Erro", "Selecione um arquivo Excel válido (*.xls ou *.xlsx).")
                return

            try:
                df = pd.read_excel(fileName)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao abrir a planilha",
                                     f"Não foi possível abrir o arquivo.\nErro: {str(e)}")
                return

            if df.empty:
                QMessageBox.warning(self, "Aviso", "A planilha está vazia. Selecione um arquivo com dados.")
                return

            self.display_data(df)
            self.stacked_layout.setCurrentIndex(self.table_index)  # Mostra a tabela após carregar a planilha

        except Exception as e:
            QMessageBox.critical(self, "Erro inesperado", f"Ocorreu um erro inesperado:\n{str(e)}")

    def display_data(self, df):
        """ Exibe os dados da planilha na tabela """
        try:
            if df.empty:
                QMessageBox.warning(self, "Aviso", "A planilha está vazia. Selecione um arquivo com dados.")
                return

            from datetime import datetime

            if "Data Conclusão" in df.columns:
                df["Data Conclusão"] = pd.to_datetime(df["Data Conclusão"], errors="coerce").dt.strftime('%d-%m-%Y')

                total_antes = len(df)
                df = df[df["Data Conclusão"].notna() & (df["Data Conclusão"].str.strip() != "")].copy()
                ignorados_invalidas = total_antes - len(df)

                hoje = datetime.today()
                mes_atual = hoje.month
                ano_atual = hoje.year

                df["Data Conclusão Datetime"] = pd.to_datetime(df["Data Conclusão"], format='%d-%m-%Y', errors="coerce")

                antes_filtro_data = len(df)
                df = df[
                    (df["Data Conclusão Datetime"].dt.year == ano_atual) &
                    (df["Data Conclusão Datetime"].dt.month == mes_atual)
                    ]
                ignorados_anteriores = antes_filtro_data - len(df)

                df.drop(columns=["Data Conclusão Datetime"], inplace=True)

                total_ignorados = ignorados_invalidas + ignorados_anteriores
                if total_ignorados > 0:
                    mensagem = []
                    if ignorados_invalidas:
                        mensagem.append(f"{ignorados_invalidas} com data inválida")
                    if ignorados_anteriores:
                        mensagem.append(f"{ignorados_anteriores} de mês ou ano anterior")
                    QMessageBox.information(self, "Agendamentos Ignorados", f"{' e '.join(mensagem)} foram ignorados.")

            conn = connect_db()
            cursor = conn.cursor()

            if self.user_info["is_admin"]:
                query = "SELECT numero_agendamento FROM agendamentos_procedimentos"
            else:
                sanitized_username = self.user_info["username"].replace(" ", "_").lower()
                table_name = f"procedimentos_{sanitized_username}"
                query = f"SELECT numero_agendamento FROM {table_name}"

            cursor.execute(query)
            assigned_agendamentos = {str(row[0]).strip() for row in cursor.fetchall() if row[0]}
            conn.close()

            df["Número Agendamento"] = df["Número Agendamento"].astype(str).str.strip()
            df = df[~df["Número Agendamento"].isin(assigned_agendamentos)].copy()

            if not self.user_info["is_admin"]:
                fiscal_logado = self.user_info["username"]
                df = df[df["Fiscal"].str.upper() == fiscal_logado.upper()]

            if df.empty:
                QMessageBox.information(self, "Informação", "Nenhum novo agendamento disponível para exibição.")
                return

            self.table.setColumnCount(len(df.columns))
            self.table.setRowCount(len(df))
            self.table.setHorizontalHeaderLabels(df.columns)

            for i in range(len(df)):
                self.table.setRowHeight(i, 30)
                for j in range(len(df.columns)):
                    value = str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                    self.table.setItem(i, j, item)

            for i in range(self.table.rowCount()):
                max_height = 0
                for j in range(self.table.columnCount()):
                    item = self.table.item(i, j)
                    if item:
                        rect = self.table.visualItemRect(item)
                        if rect.height() > max_height:
                            max_height = rect.height()
                self.table.setRowHeight(i, max(30, max_height + 10))

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exibir os dados na tabela:\n{str(e)}")
            print(f"[ERRO] Erro ao exibir dados: {e}")

    def add_manual_agendamento(self):
        """ Abre a janela para adicionar um novo agendamento manualmente """
        try:
            dialog = AddAgendamentoDialog(self)
            if dialog.exec_():
                agendamento_data = dialog.get_data()
                self.add_agendamento_to_table(agendamento_data)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro inesperado ao adicionar agendamento:\n{e}")

    def add_agendamento_to_table(self, agendamento_data):
        """Adiciona um novo agendamento à tabela."""
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        for i, key in enumerate(["Data Conclusão", "Número Agendamento", "Fiscal",
                                 "Tipo Registro", "Número Registro", "Nome"]):
            value = agendamento_data[key]
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row_position, i, item)
        print(f"[DEBUG] Novo agendamento adicionado à tabela: {agendamento_data}")

    def open_assign_procedure_dialog(self):
        """ Abre a janela para atribuir múltiplos procedimentos """
        try:
            if self.table.rowCount() == 0:
                QMessageBox.warning(self, "Erro", "A tabela está vazia. Não há agendamentos para selecionar.")
                return

            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Erro", "Selecione um agendamento primeiro!")
                return

            agendamento_data = {
                "Data Conclusão": self.table.item(selected_row, 0).text(),
                "Número Agendamento": self.table.item(selected_row, 1).text(),
                "Fiscal": self.table.item(selected_row, 2).text(),
                "Tipo Registro": self.table.item(selected_row, 3).text(),
                "Número Registro": self.table.item(selected_row, 4).text(),
                "Nome": self.table.item(selected_row, 5).text()
            }

            if not hasattr(self, 'user_info') or not self.user_info:
                QMessageBox.critical(self, "Erro", "Informações do usuário não estão disponíveis!")
                return

            dialog = AssignMultipleProceduresDialog(agendamento_data, self.user_info, self)
            if dialog.exec_():
                self.table.removeRow(selected_row)
                self.atualizar_relatorio.emit()
                self.atualizar_resultados_fiscal.emit()

                QMessageBox.information(self, "Sucesso", "Procedimento atribuído com sucesso!")

        except Exception as e:
            QMessageBox.critical(self, "Erro inesperado", f"Ocorreu um erro ao abrir o diálogo:\n{str(e)}")
            print(f"[ERRO] {e}")

    def load_spreadsheet(self):
        """ Carrega a planilha Excel e exibe os dados na tabela """
        try:
            options = QFileDialog.Options()
            fileName, _ = QFileDialog.getOpenFileName(self, "Carregar Planilha", "", "Excel Files (*.xls *.xlsx)",
                                                      options=options)

            if not fileName:
                return

            if not fileName.lower().endswith(('.xls', '.xlsx')):
                QMessageBox.warning(self, "Erro", "Selecione um arquivo Excel válido (*.xls ou *.xlsx).")
                return

            try:
                # Tenta ler o arquivo
                df = pd.read_excel(fileName)
            except Exception as e:
                QMessageBox.critical(self, "Erro ao abrir a planilha",
                                     f"Não foi possível abrir o arquivo.\nErro: {str(e)}")
                return

            if df.empty:
                QMessageBox.warning(self, "Aviso", "A planilha está vazia. Selecione um arquivo com dados.")
                return

            # ⚙️ INÍCIO DA VALIDAÇÃO DOS CAMPOS OBRIGATÓRIOS E FEEDBACK DETALHADO
            required_columns = [
                "Data Conclusão", "Número Agendamento", "Fiscal",
                "Tipo Registro", "Número Registro", "Nome"
            ]

            # Remove espaços em branco do início/fim dos nomes das colunas lidas
            df.columns = df.columns.str.strip()

            planilha_columns = list(df.columns)
            missing_columns = [col for col in required_columns if col not in planilha_columns]

            error_message = []

            # Checa se o número de colunas está correto (para evitar index out of range)
            if len(planilha_columns) != len(required_columns):
                error_message.append(
                    f"A planilha deve ter **{len(required_columns)}** colunas. Sua planilha tem **{len(planilha_columns)}**."
                )

            # Checa coluna por coluna e fornece feedback sobre o nome incorreto
            for i, expected_col in enumerate(required_columns):
                if i < len(planilha_columns):
                    actual_col = planilha_columns[i]
                    if actual_col != expected_col:
                        error_message.append(
                            f"Coluna na posição {i + 1} **incorreta** ('{actual_col}'). "
                            f"O correto é **'{expected_col}'**."
                        )
                elif expected_col in missing_columns:
                    # Se faltar no final e já for reportado no 'missing_columns', não precisa repetir
                    pass

            # Se ainda houver colunas faltando, lista elas
            if missing_columns and not error_message:  # Se o erro for SÓ de colunas faltando (e não na ordem)
                error_message.append(
                    f"As seguintes colunas estão faltando: {', '.join(missing_columns)}."
                )

            # Se houver qualquer erro, exibe a mensagem detalhada e retorna
            if error_message:
                final_error = "Erro de Formato da Planilha. Por favor, verifique:\n\n"
                final_error += "\n".join(error_message)
                final_error += f"\n\nColunas Esperadas (Ordem Exata): {', '.join(required_columns)}"

                QMessageBox.critical(self, "Erro de Formato da Planilha", final_error)
                return

            # 💡 Otimização: Se a validação passou, garante que apenas as colunas necessárias sejam usadas, na ordem correta
            df = df[required_columns]
            # ⚙️ FIM DA VALIDAÇÃO DOS CAMPOS OBRIGATÓRIOS E FEEDBACK DETALHADO

            self.display_data(df)
            self.stacked_layout.setCurrentIndex(self.table_index)  # Mostra a tabela após carregar a planilha

        except Exception as e:
            QMessageBox.critical(self, "Erro inesperado", f"Ocorreu um erro inesperado:\n{str(e)}")

    def add_manual_agendamento(self):
        """ Abre a janela para adicionar um novo agendamento manualmente """
        try:
            dialog = AddAgendamentoDialog(self)
            if dialog.exec_():
                agendamento_data = dialog.get_data()
                self.add_agendamento_to_table(agendamento_data)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro inesperado ao adicionar agendamento:\n{e}")

    def add_agendamento_to_table(self, agendamento_data):
        """Adiciona um novo agendamento à tabela."""
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        for i, key in enumerate(["Data Conclusão", "Número Agendamento", "Fiscal",
                                 "Tipo Registro", "Número Registro", "Nome"]):
            value = agendamento_data[key]
            item = QTableWidgetItem(value)
            item.setFlags(item.flags() ^ Qt.ItemIsEditable)
            self.table.setItem(row_position, i, item)
        print(f"[DEBUG] Novo agendamento adicionado à tabela: {agendamento_data}")

    def open_assign_procedure_dialog(self):
        """ Abre a janela para atribuir múltiplos procedimentos """
        try:
            if self.table.rowCount() == 0:
                QMessageBox.warning(self, "Erro", "A tabela está vazia. Não há agendamentos para selecionar.")
                return

            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Erro", "Selecione um agendamento primeiro!")
                return

            agendamento_data = {
                "Data Conclusão": self.table.item(selected_row, 0).text(),
                "Número Agendamento": self.table.item(selected_row, 1).text(),
                "Fiscal": self.table.item(selected_row, 2).text(),
                "Tipo Registro": self.table.item(selected_row, 3).text(),
                "Número Registro": self.table.item(selected_row, 4).text(),
                "Nome": self.table.item(selected_row, 5).text()
            }

            if not hasattr(self, 'user_info') or not self.user_info:
                QMessageBox.critical(self, "Erro", "Informações do usuário não estão disponíveis!")
                return

            dialog = AssignMultipleProceduresDialog(agendamento_data, self.user_info, self)
            if dialog.exec_():
                self.table.removeRow(selected_row)
                self.atualizar_relatorio.emit()
                self.atualizar_resultados_fiscal.emit()
                self.atualizar_resultado_mensal.emit()
                self.atualizar_resultado_mensal_crcdf.emit()
                QMessageBox.information(self, "Sucesso", "Procedimento atribuído com sucesso!")

        except Exception as e:
            QMessageBox.critical(self, "Erro inesperado", f"Ocorreu um erro ao abrir o diálogo:\n{str(e)}")
            print(f"[ERRO] {e}")


class RelatorioAtribuicoesTab(QWidget):
    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.title_label = QLabel("📊 Relatório de Atribuições")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Data Atribuição", "Fiscal", "Nº Agendamento", "Tipo Registro",
            "Nº Registro", "Nome", "Procedimento", "Quantidade/Motivo"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        column_widths = [150, 150, 150, 120, 120, 200, 200, 150]
        for i, width in enumerate(column_widths):
            self.table.setColumnWidth(i, width)
        self.table.setStyleSheet("""
            QHeaderView::section {
                background-color: #002060;
                color: white;
                font-weight: bold;
                padding: 3px;
                border: 1px solid white;
            }
        """)
        layout.addWidget(self.table)

        self.load_report_data()

        layout.addWidget(QLabel("<i>Relatório gerado automaticamente ao atribuir procedimentos.</i>"))

        self.setLayout(layout)

    def load_report_data(self):
        try:
            conn = connect_db()
            cursor = conn.cursor()

            if self.user_info["is_admin"]:
                cursor.execute("""
                    SELECT
                        strftime('%d-%m-%Y %H:%M:%S', ap.data_atribuicao),
                        ap.fiscal,
                        ap.numero_agendamento,
                        ap.tipo_registro,
                        ap.numero_registro,
                        ap.nome,
                        p.name,
                        ap.quantidade
                    FROM agendamentos_procedimentos ap
                    JOIN procedimentos p ON ap.procedimento_id = p.id
                    ORDER BY ap.data_atribuicao DESC
                """)
                report_data = cursor.fetchall()
            else:
                sanitized_username = self.user_info["username"].replace(" ", "_").lower()
                table_name = f"procedimentos_{sanitized_username}"
                if self.check_table_exists(cursor, table_name):
                    cursor.execute(f"""
                        SELECT
                            strftime('%d-%m-%Y %H:%M:%S', pa.data_atribuicao),
                            '{self.user_info["username"]}',
                            pa.numero_agendamento,
                            pa.tipo_registro,
                            pa.numero_registro,
                            pa.nome,
                            p.name,
                            pa.quantidade
                        FROM {table_name} pa
                        JOIN procedimentos p ON pa.procedimento_id = p.id
                        ORDER BY pa.data_atribuicao DESC
                    """)
                    report_data = cursor.fetchall()
                else:
                    report_data = []

            conn.close()

            self.populate_table(report_data)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao carregar o relatório:\n{str(e)}")
            print(f"[ERRO] Erro ao carregar relatório: {e}")

    def check_table_exists(self, cursor, table_name):
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        return cursor.fetchone() is not None

    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for i, row_data in enumerate(data):
            for j, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
            self.table.setRowHeight(i, 30)

class ConfigTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        title_label = QLabel("⚙️ Configurações")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title_label)
        layout.addWidget(QLabel("<i>Nenhuma configuração específica disponível nesta versão.</i>"))
        self.setLayout(layout)

class MainWindow(QWidget):
    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.setWindowTitle("Sistema de Atribuição de Procedimentos")
        self.setGeometry(100, 100, 1200, 700)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.atribuir_tab = AtribuirTab(self.user_info)
        self.relatorio_tab = RelatorioAtribuicoesTab(self.user_info)
        self.config_tab = ConfigTab()

        self.tabs.addTab(self.atribuir_tab, "Atribuir")
        self.tabs.addTab(self.relatorio_tab, "Relatório")
        self.tabs.addTab(self.config_tab, "Configurações")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.atribuir_tab.atualizar_relatorio.connect(self.relatorio_tab.load_report_data)


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login")
        self.setFixedSize(300, 150)
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Usuário:", self.username_input)
        form_layout.addRow("Senha:", self.password_input)
        layout.addLayout(form_layout)
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.check_login)
        layout.addWidget(self.login_button)
        self.setLayout(layout)
        self.user_info = None

    def check_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT username, password, is_admin FROM users WHERE username=?", (username,))
        user_data = cursor.fetchone()
        conn.close()

        if user_data and user_data[1] == password:
            self.user_info = {"username": user_data[0], "is_admin": bool(user_data[2])}
            self.accept()
        else:
            QMessageBox.warning(self, "Erro", "Usuário ou senha incorretos.")

    def get_user_info(self):
        return self.user_info

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    login_dialog = LoginDialog()
    if login_dialog.exec_() == QDialog.Accepted:
        user_info = login_dialog.get_user_info()
        if user_info:
            main_window = MainWindow(user_info)
            main_window.show()
            sys.exit(app.exec_())