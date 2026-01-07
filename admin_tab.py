from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox,
    QMessageBox, QListWidget, QListWidgetItem, QDialog, QFormLayout, QHBoxLayout,
    QGroupBox, QScrollArea, QSplitter, QFrame, QTabWidget, QGridLayout, QSpacerItem,
    QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
import sqlite3
from db import (
    add_user, get_user_id, set_user_permissions, get_procedures, add_procedure,
    delete_procedure, add_or_update_weight, get_weights, get_users
)
from db import connect_db



class ModernDialog(QDialog):
    """Base para diálogos com estilo moderno"""

    def __init__(self, parent=None, title="Diálogo", size=(600, 450)):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(*size)

        # Estilo moderno
        self.setStyleSheet("""
            QDialog {
                background-color: #f7f9fc;
                border: 1px solid #dce1e8;
                border-radius: 8px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QLabel[heading="true"] {
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 12px;
                color: #1e3a8a;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #dce1e8;
                border-radius: 4px;
                background-color: white;
                selection-background-color: #3498db;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QPushButton {
                padding: 8px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c638e;
            }
            QPushButton[success="true"] {
                background-color: #27ae60;
            }
            QPushButton[success="true"]:hover {
                background-color: #2ecc71;
            }

            QPushButton[danger="true"] {
                background-color: #e74c3c;
            }
            QPushButton[danger="true"]:hover {
                background-color: #c0392b;
            }
            QListWidget {
                border: 1px solid #dce1e8;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f0f0f0;
                outline: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #d6eaf8;
                color: #2c3e50;
            }
            QCheckBox {
                spacing: 8px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dce1e8;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton#btn_reset_data {
                background-color: #e67e22;
            }
            QPushButton#btn_reset_data:hover {
                background-color: #d35400;
            }

        """)




class AdminTab(QWidget):
    def __init__(self,relatorio_atribuicoes_tab=None, resultados_fiscal_tab=None, resultado_mensal_tab=None, resultado_mensal_crcdf_tab=None, main_app=None):
        super().__init__()
        self.relatorio_atribuicoes_tab = relatorio_atribuicoes_tab
        self.resultados_fiscal_tab = resultados_fiscal_tab
        self.resultado_mensal_tab = resultado_mensal_tab
        self.resultado_mensal_crcdf_tab = resultado_mensal_crcdf_tab
        self.initUI()
        self.main_app = main_app

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("Painel de Administração")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dce1e8;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f5fa;
                border: 1px solid #dce1e8;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e1eaf5;
            }
        """)

        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)
        users_layout.setContentsMargins(15, 15, 15, 15)
        users_layout.setSpacing(10)

        user_form_group = QGroupBox("Adicionar Novo Usuário")
        user_form_layout = QGridLayout(user_form_group)
        user_form_layout.setSpacing(10)

        self.input_username = QLineEdit()
        self.input_username.setPlaceholderText("Nome do usuário")
        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Senha")
        self.input_password.setEchoMode(QLineEdit.Password)

        type_group = QGroupBox("Tipo de Usuário")
        type_layout = QVBoxLayout(type_group)
        self.checkbox_admin = QCheckBox("Administrador")
        self.checkbox_admin.setToolTip("Acesso total ao sistema")
        self.checkbox_fiscal = QCheckBox("Fiscal")
        self.checkbox_fiscal.setToolTip("Usuário com função de fiscal")
        self.checkbox_visitor = QCheckBox("Visitante")
        self.checkbox_visitor.setToolTip("Acesso limitado apenas para visualização")
        type_layout.addWidget(self.checkbox_admin)
        type_layout.addWidget(self.checkbox_fiscal)
        type_layout.addWidget(self.checkbox_visitor)

        permissions_group = QGroupBox("Permissões de Acesso")
        permissions_layout = QVBoxLayout(permissions_group)
        self.permission_list = QListWidget()
        self.permission_list.setAlternatingRowColors(True)
        self.tabs = [
            "Atribuir", "Relatório de Atribuições", "Resultados do Fiscal",
            "Resultado Mensal", "Resultado Mensal - CRCDF", "Administração", "Log de Ações"
        ]
        for tab in self.tabs:
            item = QListWidgetItem(tab)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.permission_list.addItem(item)
        permissions_layout.addWidget(self.permission_list)

        user_form_layout.addWidget(QLabel("Nome de Usuário:"), 0, 0)
        user_form_layout.addWidget(self.input_username, 0, 1)
        user_form_layout.addWidget(QLabel("Senha:"), 1, 0)
        user_form_layout.addWidget(self.input_password, 1, 1)
        user_form_layout.addWidget(type_group, 2, 0, 1, 2)
        user_form_layout.addWidget(permissions_group, 3, 0, 1, 2)

        user_actions_layout = QHBoxLayout()
        user_actions_layout.setSpacing(10)

        # Adiciona um QSpacerItem ANTES dos botões para empurrá-los para a direita
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        user_actions_layout.addItem(spacer)

        self.btn_add_user = QPushButton("🗂Salvar Informações do Novo Usuário")
        self.btn_add_user.setObjectName("btn_add_user")
        self.btn_add_user.clicked.connect(self.add_user)
        self.btn_add_user.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        user_actions_layout.addWidget(self.btn_add_user)

        self.btn_exportar_relatorios = QPushButton("🧾Exportar Relatórios")
        self.btn_exportar_relatorios.setObjectName("btn_exportar_relatorios")
        self.btn_exportar_relatorios.clicked.connect(self.exportar_relatorios_escolhidos)
        self.btn_exportar_relatorios.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        user_actions_layout.addWidget(self.btn_exportar_relatorios)

        self.btn_reset_data = QPushButton("🧨 Zerar Banco de Dados")
        self.btn_reset_data.setObjectName("btn_reset_data")
        self.btn_reset_data.setProperty("danger", "true")
        self.btn_reset_data.clicked.connect(self.zerar_dados_procedimentos)
        user_actions_layout.addWidget(self.btn_reset_data)

        self.btn_edit_users = QPushButton("✏️ Editar Usuários Existentes")
        self.btn_edit_users.clicked.connect(self.abrir_edicao_usuarios)
        user_actions_layout.addWidget(self.btn_edit_users)

        users_layout.addWidget(user_form_group)
        users_layout.addLayout(user_actions_layout)

        procedures_tab = QWidget()
        procedures_layout = QVBoxLayout(procedures_tab)
        procedures_layout.setContentsMargins(15, 15, 15, 15)
        procedures_layout.setSpacing(15)

        proc_title_label = QLabel("Gerenciamento de Procedimentos")
        proc_title_font = QFont()
        proc_title_font.setBold(True)
        proc_title_label.setFont(proc_title_font)
        procedures_layout.addWidget(proc_title_label)

        self.btn_add_procedure = QPushButton("➕ Adicionar Novo Procedimento")
        self.btn_add_procedure.setObjectName("btn_add_procedure")
        self.btn_add_procedure.clicked.connect(self.add_procedure)
        procedures_layout.addWidget(self.btn_add_procedure, alignment=Qt.AlignLeft)

        content_layout = QHBoxLayout()

        list_group = QGroupBox("📋 Lista de Procedimentos")
        list_layout = QVBoxLayout()
        self.procedure_list = QListWidget()
        self.procedure_list.setWordWrap(True)
        self.procedure_list.setAlternatingRowColors(True)
        self.procedure_list.itemClicked.connect(
            self.on_procedure_selected)
        list_layout.addWidget(self.procedure_list)
        list_group.setLayout(list_layout)
        content_layout.addWidget(list_group, 2)

        edit_group = QGroupBox("✏️ Editar Procedimento")
        edit_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.input_procedure_name = QLineEdit()
        self.input_procedure_name.setPlaceholderText("Nome do Procedimento")
        self.input_procedure_weight = QLineEdit()
        self.input_procedure_weight.setPlaceholderText("Peso (ex: 1.0)")
        self.input_procedure_weight.setText("1")
        form_layout.addRow("Nome:", self.input_procedure_name)
        form_layout.addRow("Peso:", self.input_procedure_weight)
        edit_layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        buttons_layout.addStretch(1)
        self.btn_edit_procedure = QPushButton("🔄 Atualizar Informações")
        self.btn_edit_procedure.setObjectName("btn_edit_procedure")
        self.btn_edit_procedure.clicked.connect(self.edit_procedure_weight)
        self.btn_edit_procedure.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_edit_procedure.setProperty("success", "true")
        self.btn_edit_procedure.hide()
        buttons_layout.addWidget(self.btn_edit_procedure)

        self.btn_delete_procedure = QPushButton("🗑️ Remover")
        self.btn_delete_procedure.setObjectName("btn_delete_procedure")
        self.btn_delete_procedure.clicked.connect(self.delete_procedure)
        self.btn_delete_procedure.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_delete_procedure.setProperty("danger", "true")
        self.btn_delete_procedure.hide()
        buttons_layout.addWidget(self.btn_delete_procedure)
        edit_layout.addLayout(buttons_layout)

        edit_group.setLayout(edit_layout)
        content_layout.addWidget(edit_group, 3)

        procedures_layout.addLayout(content_layout)

        tab_widget.addTab(users_tab, "Gerenciar Usuários")
        tab_widget.addTab(procedures_tab, "Gerenciar Procedimentos")

        main_layout.addWidget(tab_widget)


        self.setLayout(main_layout)

        # Aplicar stylesheet (mantido como no original)
        self.setStyleSheet("""
            /* Estilo base já existente */
            QWidget {
                background-color: #f7f9fc;
            }
            QLabel {
                color: #2c3e50;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #dce1e8;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QCheckBox {
                color: #2c3e50;
                spacing: 8px;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dce1e8;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QListWidget {
                border: 1px solid #dce1e8;
                border-radius: 4px;
                background-color: white;
                alternate-background-color: #f5f8fa;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ecf0f1;
            }
            QListWidget::item:selected {
                background-color: #d6eaf8;
                color: #2c3e50;
            }

            /* Estilo para todos os botões */
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 5px 10px;
                border: none;
                border-radius: 4px;
                min-height: 35px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
                box-shadow: 0 2px 5px rgba(0, 0, 0, 0.2);
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }

            /* Botão de adicionar usuário (verde) */
            QPushButton#btn_add_user {
                background-color: #27ae60;
            }
            QPushButton#btn_add_user:hover {
                background-color: #2ecc71;
            }
            QPushButton#btn_add_user:pressed {
                background-color: #219653;
            }

            /* Botão de adicionar procedimento (azul/verde) */
            QPushButton#btn_add_procedure {
                background-color: #3498db;
                padding: 1px 5px;
                font-size: 11px;
            }
            QPushButton#btn_add_procedure:hover {
                background-color: #2980b9;
            }

            /* Botão de atualizar (azul -> verde como no original) */
            QPushButton#btn_edit_procedure {
                background-color: #29b946; /* Era verde no seu CSS original */
            }
            QPushButton#btn_edit_procedure:hover {
                background-color: #0c6e20;
            }

            /* Botão de remover (vermelho) */
            QPushButton#btn_delete_procedure {
                background-color: #e74c3c;
            }
            QPushButton#btn_delete_procedure:hover {
                background-color: #c0392b;
            }

            /* Botão de exportar relatórios (roxo) */
            QPushButton#btn_exportar_relatorios {
                background-color: #007dbd;
            }
            QPushButton#btn_exportar_relatorios:hover {
                background-color: #0085d5;
            }
        """)

        # Carregar procedimentos iniciais
        self.load_procedures()

    def load_procedures(self):
        self.procedure_list.clear()
        weights = get_weights()
        for p in get_procedures():
            name = p["name"]
            weight = weights.get(name, 1.0)
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, name)
            item.setData(Qt.UserRole + 1, weight)
            item.setData(Qt.UserRole + 2, p["id"])  # 💡 guardar o ID!
            self.procedure_list.addItem(item)

    def on_procedure_selected(self, item):
        """Manipula a seleção de um procedimento da lista"""
        if not item:
            return

        self.input_procedure_name.setText(item.data(Qt.UserRole))
        self.input_procedure_weight.setText(str(item.data(Qt.UserRole + 1)))
        self.selected_procedure_id = item.data(Qt.UserRole + 2)
        self.btn_edit_procedure.show()
        self.btn_delete_procedure.show()

    def on_item_selected(self, item):
        if not item:
            return

        self.input_procedure_name.setText(item.data(Qt.UserRole))
        self.input_procedure_weight.setText(str(item.data(Qt.UserRole + 1)))
        self.selected_procedure_id = item.data(Qt.UserRole + 2)  # ID salvo!
        self.btn_edit_procedure.show()
        self.btn_delete_procedure.show()

    def add_procedure(self):
        # Usar o método da própria classe em vez do parent
        if not self.verificar_senha_admin():
            QMessageBox.warning(self, "Acesso negado", "Ação cancelada. Senha de administrador incorreta.")
            return

        dialog = AddProcedureDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, weight = dialog.get_data()

            if not name:
                QMessageBox.warning(self, "Erro", "O nome do procedimento é obrigatório.")
                return

            try:
                weight_value = float(weight)
                if weight_value <= 0:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Erro", "O peso deve ser um número positivo.")
                return

            try:
                add_procedure(name, "")
                add_or_update_weight(name, weight_value)
                QMessageBox.information(self, "Sucesso", "Procedimento adicionado com sucesso!")
                self.load_procedures()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Erro", f"O procedimento '{name}' já existe.")

    def edit_procedure_weight(self):
        try:
            # Usar o método da própria classe em vez do parent
            if not self.verificar_senha_admin():
                QMessageBox.warning(self, "Acesso negado", "Ação cancelada. Senha de administrador incorreta.")
                return

            name = self.input_procedure_name.text().strip()
            weight = self.input_procedure_weight.text().strip()

            if not name:
                QMessageBox.warning(self, "Erro", "Selecione um procedimento para editar.")
                return

            try:
                weight_value = float(weight)
                if weight_value <= 0:
                    raise ValueError("O peso deve ser positivo")
            except ValueError:
                QMessageBox.warning(self, "Erro", "O peso deve ser um número positivo.")
                return

            add_or_update_weight(name, weight_value)
            QMessageBox.information(self, "Sucesso", "Peso atualizado com sucesso!")
            self.load_procedures()
            self.input_procedure_name.clear()
            self.input_procedure_weight.setText("1.0")

        except Exception as e:
            QMessageBox.critical(self, "Erro Fatal", f"Ocorreu um erro: {e}")

    def delete_procedure(self):
        try:
            # Usar o método da própria classe em vez do parent
            if not self.verificar_senha_admin():
                QMessageBox.warning(self, "Acesso negado", "Ação cancelada. Senha de administrador incorreta.")
                return

            if not hasattr(self, 'selected_procedure_id'):
                QMessageBox.warning(self, "Erro", "Selecione um procedimento válido para remover.")
                return

            reply = QMessageBox.question(
                self, "Confirmar exclusão",
                "Tem certeza que deseja excluir este procedimento?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                delete_procedure(self.selected_procedure_id)
                QMessageBox.information(self, "Sucesso", "Procedimento removido com sucesso!")
                self.load_procedures()
                self.input_procedure_name.clear()
                self.input_procedure_weight.setText("1.0")
                del self.selected_procedure_id  # limpa o ID

        except Exception as e:
            QMessageBox.critical(self, "Erro Fatal", f"Ocorreu um erro: {e}")


    def verificar_senha_admin(self):
        """ Abre o diálogo e verifica se a senha informada é de um admin válido """
        dialog = AdminPasswordDialog(self)
        if not dialog.exec_():
            return False

        senha_digitada = dialog.get_password()

        try:
            conn = sqlite3.connect(r'\\192.168.0.120\BancoSiaFisk\application.db')
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE is_admin = 1")
            senhas = [row[0] for row in cursor.fetchall()]
            conn.close()

            return senha_digitada in senhas
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao verificar senha: {e}")
            return False

    def add_user(self):
        if not self.verificar_senha_admin():  # Alterado para self.verificar_senha_admin()
            QMessageBox.warning(self, "Acesso negado", "Ação cancelada. Senha de administrador incorreta.")
            return

        """ Adiciona um novo usuário ao banco de dados e configura permissões """
        try:
            username = self.input_username.text().strip()
            password = self.input_password.text().strip()

            if not username or not password:
                QMessageBox.warning(self, "Erro", "Usuário e senha não podem estar vazios!")
                return

            is_admin = self.checkbox_admin.isChecked()
            is_fiscal = self.checkbox_fiscal.isChecked()
            is_visitor = self.checkbox_visitor.isChecked()

            if sum([is_admin, is_fiscal, is_visitor]) != 1:
                QMessageBox.warning(self, "Erro", "Selecione apenas uma opção: Administrador, Fiscal ou Visitante!")
                return

            add_user(username, password, int(is_admin), int(is_fiscal))

            user_id = get_user_id(username)
            if not user_id:
                QMessageBox.critical(self, "Erro", "Não foi possível obter o ID do usuário.")
                return

            permissions = {self.permission_list.item(i).text(): self.permission_list.item(i).checkState() == Qt.Checked
                           for i in range(self.permission_list.count())}

            set_user_permissions(user_id, permissions)

            # Mostrar mensagem de sucesso com estilo moderno
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("Sucesso")
            msg.setText(f"Usuário '{username}' adicionado com sucesso!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()

            # Limpar campos
            self.input_username.clear()
            self.input_password.clear()
            self.checkbox_admin.setChecked(False)
            self.checkbox_fiscal.setChecked(False)
            self.checkbox_visitor.setChecked(False)

        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "Erro", f"O usuário '{username}' já existe!")

    def exportar_relatorios_escolhidos(self):
        dialog = ExportSelectionDialog(self)
        if dialog.exec_():
            selecionado = dialog.get_selection()

            if selecionado["atribuicoes"]:
                if self.relatorio_atribuicoes_tab:
                    self.relatorio_atribuicoes_tab.exportar_pdf_excel()
                else:
                    QMessageBox.warning(self, "Erro",
                                        "A aba 'Relatório de Atribuições' não está carregada.")

            if selecionado["fiscal"]:
                if self.resultados_fiscal_tab:
                    self.resultados_fiscal_tab.exportar_pdf_excel()
                else:
                    QMessageBox.warning(self, "Erro", "A aba 'Resultados do Fiscal' não está carregada.")

            if selecionado["mensal"]:
                if self.resultado_mensal_tab:
                    self.resultado_mensal_tab.exportar_pdf_excel()
                else:
                    QMessageBox.warning(self, "Erro", "A aba 'Resultado Mensal' não está carregada.")

            if selecionado["crcdf"]:
                if self.resultado_mensal_crcdf_tab:
                    self.resultado_mensal_crcdf_tab.exportar_pdf_excel()
                else:
                    QMessageBox.warning(self, "Erro", "A aba 'Resultado Mensal - CRCDF' não está carregada.")

            # ✅ Novo: Exportar Relatório de Atribuições
            if hasattr(self, "relatorio_atribuicoes_tab") and self.relatorio_atribuicoes_tab:
                try:
                    self.relatorio_atribuicoes_tab.exportar_pdf_excel()
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Erro ao exportar Relatório de Atribuições:\n{e}")

    def zerar_dados_procedimentos(self):
        if not self.verificar_senha_admin():
            QMessageBox.warning(self, "Acesso negado", "Ação cancelada. Senha de administrador incorreta.")
            return

        confirm = QMessageBox.question(
            self, "Confirmar",
            "Tem certeza de que deseja **zerar todos os dados** dos usuários (procedimentos e pesos)?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            try:
                from db import reset_user_data
                reset_user_data()

                # 🆕 Zerar metas
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE procedures SET meta_cfc = 0, meta_crcdf = 0")
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Sucesso", "Dados dos usuários e metas zerados com sucesso!")

                self.load_procedures()

                if self.main_app and hasattr(self.main_app, 'atualizar_resultado_mensal'):
                    self.main_app.atualizar_resultado_mensal()

                if self.main_app and hasattr(self.main_app.page_resultados_fiscal, 'load_data'):
                    self.main_app.page_resultados_fiscal.load_data()


            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao zerar dados: {e}")

    def abrir_edicao_usuarios(self):
        from PyQt5.QtWidgets import QListWidgetItem

        class EditUserDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("Editar Usuários")
                self.setFixedSize(500, 450)
                self.selected_user = None

                layout = QVBoxLayout(self)

                # Lista de usuários
                self.user_list = QListWidget()
                self.user_list.itemClicked.connect(self.load_user_info)
                layout.addWidget(QLabel("Usuários cadastrados:"))
                layout.addWidget(self.user_list)

                self.username_input = QLineEdit()
                self.username_input.setPlaceholderText("Novo nome de usuário")

                self.password_input = QLineEdit()
                self.password_input.setPlaceholderText("Nova senha")
                self.password_input.setEchoMode(QLineEdit.Password)

                self.admin_check = QCheckBox("Administrador")
                self.fiscal_check = QCheckBox("Fiscal")
                self.visitor_check = QCheckBox("Visitante")

                layout.addWidget(self.username_input)
                layout.addWidget(self.password_input)
                layout.addWidget(self.admin_check)
                layout.addWidget(self.fiscal_check)
                layout.addWidget(self.visitor_check)

                # Permissões
                self.permission_list = QListWidget()
                for aba in ["Atribuir", "Relatório de Atribuições", "Resultados do Fiscal",
                            "Resultado Mensal", "Resultado Mensal - CRCDF", "Administração", "Log de Ações"]:
                    item = QListWidgetItem(aba)
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked)
                    self.permission_list.addItem(item)
                layout.addWidget(QLabel("Permissões:"))
                layout.addWidget(self.permission_list)

                btn_save = QPushButton("Salvar Alterações")
                btn_save.clicked.connect(self.save_changes)
                layout.addWidget(btn_save)

                self.load_users()

            def load_users(self):
                from db import get_users
                self.user_list.clear()
                for u in get_users():
                    self.user_list.addItem(u)

            def load_user_info(self, item):
                from db import connect_db, get_user_id, get_user_permissions
                self.selected_user = item.text()
                self.username_input.setText(self.selected_user)

                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute("SELECT password, is_admin, is_fiscal, role FROM users WHERE username = ?",
                               (self.selected_user,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    senha, is_admin, is_fiscal, role = row
                    self.password_input.setText(senha)
                    self.admin_check.setChecked(bool(is_admin))
                    self.fiscal_check.setChecked(bool(is_fiscal))
                    self.visitor_check.setChecked(role == "visitante")

                    user_id = get_user_id(self.selected_user)
                    permissoes = get_user_permissions(user_id)
                    for i in range(self.permission_list.count()):
                        item = self.permission_list.item(i)
                        item.setCheckState(Qt.Checked if permissoes.get(item.text(), False) else Qt.Unchecked)

            def save_changes(self):
                from db import connect_db, get_user_id, set_user_permissions
                try:
                    new_name = self.username_input.text().strip()
                    new_pass = self.password_input.text().strip()
                    is_admin = int(self.admin_check.isChecked())
                    is_fiscal = int(self.fiscal_check.isChecked())
                    is_visitor = self.visitor_check.isChecked()
                    role = "visitante" if is_visitor else "usuario"

                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET username = ?, password = ?, is_admin = ?, is_fiscal = ?, role = ?
                        WHERE username = ?
                    """, (new_name, new_pass, is_admin, is_fiscal, role, self.selected_user))
                    conn.commit()

                    user_id = get_user_id(new_name)
                    permissions = {
                        self.permission_list.item(i).text(): self.permission_list.item(i).checkState() == Qt.Checked
                        for i in range(self.permission_list.count())
                    }
                    set_user_permissions(user_id, permissions)

                    QMessageBox.information(self, "Sucesso", "Usuário atualizado com sucesso!")
                    self.load_users()

                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao salvar alterações: {e}")

        dialog = EditUserDialog(self)
        dialog.exec_()


class ExportSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Escolher Abas para Exportar")
        self.setFixedSize(300, 250)              # ↑ um pouco mais alto

        layout = QVBoxLayout(self)

        # ✔️ NOVA ABA
        self.chk_atribuicoes = QCheckBox("Relatório de Atribuições")
        self.chk_fiscal      = QCheckBox("Resultados do Fiscal")
        self.chk_mensal      = QCheckBox("Resultado Mensal - CFC")
        self.chk_crcdf       = QCheckBox("Resultado Mensal - CRCDF")

        # Deixe os que quiser pré-marcados
        for chk in (self.chk_atribuicoes, self.chk_fiscal,
                    self.chk_mensal, self.chk_crcdf):
            chk.setChecked(True)
            layout.addWidget(chk)

        btn = QPushButton("Exportar")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

    def get_selection(self):
        """Retorna quais abas o usuário escolheu exportar."""
        return {
            "atribuicoes": self.chk_atribuicoes.isChecked(),
            "fiscal":      self.chk_fiscal.isChecked(),
            "mensal":      self.chk_mensal.isChecked(),
            "crcdf":       self.chk_crcdf.isChecked()
        }



class AdminPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirmação de Senha")
        self.setFixedSize(350, 150)

        layout = QVBoxLayout(self)

        label = QLabel("Digite a senha de administrador para continuar:")
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.input.setPlaceholderText("Senha do administrador")

        btn_confirm = QPushButton("Confirmar")
        btn_confirm.clicked.connect(self.accept)

        layout.addWidget(label)
        layout.addWidget(self.input)
        layout.addWidget(btn_confirm)

    def get_password(self):
        return self.input.text().strip()

class AddProcedureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Procedimento")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome do Procedimento")

        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("Peso (ex: 1.0)")
        self.weight_input.setText("1.0")

        form.addRow("Nome:", self.name_input)
        form.addRow("Peso:", self.weight_input)

        layout.addLayout(form)

        button_box = QHBoxLayout()
        self.confirm_btn = QPushButton("Salvar")
        self.confirm_btn.clicked.connect(self.accept)
        button_box.addWidget(self.confirm_btn)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        button_box.addWidget(cancel_btn)

        layout.addLayout(button_box)

    def get_data(self):
        return self.name_input.text().strip(), self.weight_input.text().strip()
