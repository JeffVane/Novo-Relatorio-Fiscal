from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QMenu, QAction, QInputDialog, QComboBox, QDialog, QLineEdit, QListWidget, QPushButton,
    QListWidgetItem, QHBoxLayout, QScrollArea,QLabel
)
from PyQt5.QtCore import Qt, QPoint, QSize
from PyQt5.QtGui import QFont, QIcon,QColor, QKeySequence
from PyQt5.QtGui import QFontMetrics
from PyQt5.QtWidgets import QToolTip, QShortcut,QAbstractItemView,QApplication
from PyQt5.QtGui import QPalette
from db import get_assigned_procedures, get_procedures  # Importação correta
from db import connect_db
from datetime import datetime
from db import registrar_log
from PyQt5.QtCore import pyqtSignal
from datetime import datetime, timedelta
import pandas as pd


ORIGEM_EXCEL = datetime(1899, 12, 30)   # regra do Excel



class CancelReasonDialog(QDialog):
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
        return self.reason_input.text().strip()

class FilterDialog(QDialog):
    """ Janela de filtro com seleção de mês e checkboxes """
    def __init__(self, parent, column_index, all_values, selected_values, apply_filter_callback, update_total_callback):
        super().__init__(parent)
        self.setWindowTitle("Filtrar Dados")
        self.column_index = column_index
        self.apply_filter_callback = apply_filter_callback
        self.update_total_callback = update_total_callback  # Callback para atualizar a label

        # Garante que `all_values` seja uma lista válida
        self.all_values = list(all_values) if isinstance(all_values, (set, list)) else []
        self.selected_values = selected_values if isinstance(selected_values, set) else set()

        layout = QVBoxLayout()

        # 🔹 Adicionando seleção de mês
        self.month_selector = QComboBox(self)
        self.month_selector.addItem("Todos os meses")  # Opção padrão
        self.month_selector.addItems([
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        ])
        self.month_selector.currentIndexChanged.connect(self.filter_by_month)  # Atualiza filtro ao mudar mês
        layout.addWidget(QLabel("Filtrar por Mês:"))
        layout.addWidget(self.month_selector)

        # 🔹 Campo de pesquisa
        self.search_box = QLineEdit(self)
        self.search_box.setPlaceholderText("Pesquisar...")
        self.search_box.textChanged.connect(self.filter_values)
        layout.addWidget(self.search_box)

        # 🔹 Lista de opções com checkboxes
        self.list_widget = QListWidget(self)
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        self.list_widget.setMinimumHeight(250)
        self.list_widget.setMaximumHeight(400)
        layout.addWidget(self.list_widget)

        # Adicionar "Selecionar Tudo"
        self.select_all_item = QListWidgetItem("(Selecionar Tudo)")
        self.select_all_item.setCheckState(Qt.Checked if len(self.selected_values) == len(self.all_values) else Qt.Unchecked)
        self.list_widget.addItem(self.select_all_item)

        # Adicionar valores à lista
        self.populate_list(self.all_values)

        # Conectar evento para marcar/desmarcar todos
        self.list_widget.itemChanged.connect(self.toggle_select_all)

        # 🔹 Botões de OK e Cancelar
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancelar")
        self.ok_button.clicked.connect(self.apply_filter)
        self.cancel_button.clicked.connect(self.close)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def populate_list(self, values):
        """ Popula a lista de datas na interface """
        self.list_widget.clear()

        # Adicionar "Selecionar Tudo" novamente
        self.select_all_item = QListWidgetItem("(Selecionar Tudo)")
        self.select_all_item.setCheckState(Qt.Checked if len(self.selected_values) == len(values) else Qt.Unchecked)
        self.list_widget.addItem(self.select_all_item)

        for value in sorted(values):
            item = QListWidgetItem(value)
            item.setCheckState(Qt.Checked if value in self.selected_values else Qt.Unchecked)
            self.list_widget.addItem(item)

    def toggle_select_all(self, item):
        """ Seleciona ou desmarca todos os itens """
        if item == self.select_all_item:
            state = self.select_all_item.checkState()
            for i in range(1, self.list_widget.count()):  # Ignorar "(Selecionar Tudo)"
                self.list_widget.item(i).setCheckState(state)

    def filter_values(self):
        """ Filtra os valores da lista com base no texto digitado """
        search_text = self.search_box.text().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.text() == "(Selecionar Tudo)" or search_text in item.text().lower():
                item.setHidden(False)
            else:
                item.setHidden(True)

    def filter_by_month(self):
        """ Atualiza a lista para mostrar apenas datas do mês selecionado, sem fechar o filtro """
        selected_month = self.month_selector.currentIndex()

        if selected_month == 0:
            # 🔹 Se "Todos os meses" for selecionado, restaurar a lista original
            self.populate_list(self.all_values)
            return

        filtered_values = set()
        for value in self.all_values:
            try:
                date = datetime.strptime(value, "%d-%m-%Y")
                if date.month == selected_month:
                    filtered_values.add(value)
            except ValueError:
                continue  # Ignorar erros na conversão de data

        self.populate_list(filtered_values)

    def apply_filter(self):
        """ Aplica o filtro e atualiza a contagem de agendamentos """
        selected_values = set()
        for i in range(1, self.list_widget.count()):  # Ignorar "(Selecionar Tudo)"
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected_values.add(item.text())

        if not selected_values:
            QMessageBox.warning(self, "Aviso", "Selecione pelo menos um valor para filtrar.")
            return

        self.apply_filter_callback(self.column_index, selected_values)
        self.update_total_callback(selected_values)  # Atualiza a contagem da label
        self.close()



class RelatorioAtribuicoesTab(QWidget):
    atualizar_resultado_mensal = pyqtSignal()
    atualizar_resultados_fiscal = pyqtSignal()
    def __init__(self, user_info, parent=None):
        super().__init__(parent)  # 🔹 Corrige a passagem do parent corretamente
        self.user_info = user_info  # 🔹 Agora armazenando corretamente o usuário logado
        self.data = []
        self.original_data = []
        self.active_filters = {}
        self.unique_column_values = {}
        self.initUI()


    def initUI(self):
        layout = QVBoxLayout()

        total_layout = QHBoxLayout()
        # 🔹 ADICIONE - Seletor de Ano ANTES dos totais
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Filtrar Ano:"))
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2026", "2025", "2024", "2023", "Todos"])
        self.year_combo.setCurrentText("2026")
        self.year_combo.currentTextChanged.connect(self.load_data)
        year_layout.addWidget(self.year_combo)
        layout.addLayout(year_layout)


        # 🔹 Configuração do Tooltip para aparecer com fonte adequada
        QToolTip.setFont(QFont("DejaVu", 10))  # Define o tamanho da fonte do tooltip

        # 🔹 Define a paleta de cores para o tooltip
        palette = QPalette()
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))  # Cor de fundo do tooltip
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))  # Cor do texto do tooltip
        QToolTip.setPalette(palette)  # 🔹 Aplica a paleta corretamente

        self.title_label = QLabel("📋Relatório De Atribuições")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.title_label)

        # 🔹 Label para Total de Agendamentos
        self.total_agendamentos_label = QLabel("Total Agendamentos: 0")
        self.total_agendamentos_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 16px; 
            color: #333;
            background-color: rgb(230, 235, 242);
            padding: 8px;
            border-radius: 10px;
        """)
        self.total_agendamentos_label.setAlignment(Qt.AlignCenter)

        # 🔹 Label para Total de Procedimentos
        self.total_procedimentos_label = QLabel("Total Procedimentos: 0")
        self.total_procedimentos_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 16px; 
            color: #333;
            background-color: rgb(230, 235, 242);
            padding: 8px;
            border-radius: 10px;
        """)
        self.total_procedimentos_label.setAlignment(Qt.AlignCenter)

        total_layout.addStretch()
        total_layout.addWidget(self.total_agendamentos_label)
        total_layout.addWidget(self.total_procedimentos_label)
        total_layout.addStretch()
        layout.addLayout(total_layout)

        self.table = QTableWidget()
        # --- habilita seleção e foco para copiar ---
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)  # ou SelectItems, se preferir célula-a-célula
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # permite Shift+Cliques, Ctrl+C, etc.
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # ------------------------------------------

        # 🔹 Define as colunas da tabela baseado no tipo de usuário
        if self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False):
            self.table.setColumnCount(8)  # Com coluna "Fiscal"
            self.table.setHorizontalHeaderLabels([
                "Dt.Conclusão", "N.º Agend.", "Fiscal", "Tipo Registro",
                "Registro", "Nome", "Procedimento", "Quant."
            ])
            column_widths = [120, 120, 100, 150, 150, 200, 300, 90]
        else:
            self.table.setColumnCount(7)  # Sem coluna "Fiscal"
            self.table.setHorizontalHeaderLabels([
                "Dt.Conclusão", "N.º Agend.", "Tipo Registro",
                "Registro", "Nome", "Procedimento", "Quant."
            ])
            column_widths = [100, 100, 100, 100, 680, 280, 90]

        for index, width in enumerate(column_widths):
            self.table.setColumnWidth(index, width)

        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)
        # --- atalho Ctrl+C para copiar área selecionada ---
        QShortcut(QKeySequence("Ctrl+C"), self.table, self.copiar_tabela_para_clipboard)
        # -------------------------------------------------

        # 🔹 Determinar a posição da coluna "Quant." corretamente
        quantidade_index = 7 if (
                self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)) else 6

        self.table.horizontalHeader().setSectionResizeMode(quantidade_index, QHeaderView.Fixed)  # Mantém "Quant." fixa

        self.table.setWordWrap(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().sectionClicked.connect(self.show_filter_menu)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.table.horizontalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: rgb(0, 32, 96);
                color: white;
                font-weight: bold;
                padding: 5px;
                border: 1px solid white;
            }
        """)

        self.load_data()

    def load_data(self):
        """ Carrega os procedimentos atribuídos do banco de dados e exibe na tabela """
        # 🔹 LIMPA COMPLETAMENTE OS FILTROS E DADOS AO TROCAR O ANO
        self.active_filters.clear()
        self.unique_column_values.clear()
        self.data = []  # Limpa os dados atuais
        self.original_data = []  # Limpa os dados originais

        try:
            if not self.user_info:
                QMessageBox.critical(self, "Erro", "As informações do usuário não foram carregadas.")
                return

            username = self.user_info["username"]
            is_admin = self.user_info["is_admin"]
            is_visitor = self.user_info["is_visitor"]

            conn = connect_db()
            cursor = conn.cursor()

            # 🔹 Visitantes e Administradores carregam TODAS as tabelas de usuários
            if is_admin or is_visitor:
                print(f"[DEBUG] Visitante/Admin logado - carregando TODOS os procedimentos.")
                cursor.execute("SELECT username FROM users")
                users = cursor.fetchall()

                for user in users:
                    sanitized_username = user[0].replace(" ", "_").lower()
                    table_name = f"procedimentos_{sanitized_username}"

                    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if cursor.fetchone():
                        try:
                            cursor.execute(f"SELECT * FROM {table_name}")
                            registros = cursor.fetchall()

                            # 🔹 APLICA FILTRO DE ANO
                            ano_selecionado = self.year_combo.currentText()
                            if ano_selecionado != "Todos":
                                ano_int = int(ano_selecionado)
                                registros = [
                                    r for r in registros
                                    if self.parse_dt(r[1]).year == ano_int
                                ]

                            # Verificar se os registros têm colunas suficientes
                            if registros and len(registros[0]) < 9:
                                print(
                                    f"[ERROR] Tabela '{table_name}' retornou um número inesperado de colunas: {len(registros[0])}")
                                continue

                            print(f"[DEBUG] Registros encontrados para {sanitized_username}: {len(registros)}")
                            self.data.extend(registros)
                        except Exception as e:
                            print(f"[ERROR] Falha ao carregar dados da tabela '{table_name}': {str(e)}")

            # 🔹 Usuários comuns carregam apenas seus próprios dados
            else:
                sanitized_username = username.replace(" ", "_").lower()
                table_name = f"procedimentos_{sanitized_username}"

                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                if cursor.fetchone():
                    cursor.execute(f"SELECT * FROM {table_name}")
                    registros = cursor.fetchall()

                    # 🔹 APLICA FILTRO DE ANO PARA USUÁRIO COMUM
                    ano_selecionado = self.year_combo.currentText()

                    if ano_selecionado == "Todos":
                        self.data = registros
                    else:
                        ano_int = int(ano_selecionado)
                        self.data = [
                            r for r in registros
                            if self.parse_dt(r[1]).year == ano_int
                        ]

                    print(f"[DEBUG] Registros carregados para {username}: {len(self.data)}")

            conn.close()
            self.original_data = self.data[:]  # Faz uma cópia dos dados originais

            if not self.data:
                # Limpa a tabela se não houver dados
                self.table.setRowCount(0)
                self.total_agendamentos_label.setText("Total Agendamentos: 0")
                self.total_procedimentos_label.setText("Total Procedimentos: 0")
                QMessageBox.information(self, "Informação",
                                        f"Nenhum procedimento encontrado para o ano {ano_selecionado}.")
                return

            self.populate_table(self.data)  # ✅ Agora os dados são carregados corretamente

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exibir os dados na tabela:\n{str(e)}")
            print(f"[ERROR] Erro ao exibir os dados na tabela: {e}")

    @staticmethod
    def parse_dt(valor: object) -> datetime:
        """Converte valor vindo do banco para datetime; devolve datetime.min se falhar."""
        try:
            # serial do Excel (int/float ou string numérica)
            if isinstance(valor, (int, float)) or (isinstance(valor, str) and valor.isdigit()):
                return ORIGEM_EXCEL + timedelta(days=int(float(valor)))

            # formatos comuns de string
            for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(valor), fmt)
                except ValueError:
                    pass
        except Exception:
            pass
        return datetime.min  # sentinela “inválido”

    def populate_table(self, data):
        """ Preenche a tabela com os dados e fonte fixa, sem reduzir tamanho para caber na célula. """
        self.table.clearContents()
        self.table.setRowCount(len(data))

        default_font = QFont()
        default_font.setPointSize(10)  # Tamanho fixo de fonte

        hoje = datetime.today()
        mes_atual = hoje.month
        ano_atual = hoje.year

        incluir_fiscal = self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)
        is_admin = self.user_info.get("is_admin", False)

        # Ordena os agendamentos mais recentes para o topo
        data.sort(key=lambda row: self.parse_dt(row[1]), reverse=True)


        for i, row in enumerate(data):
            colunas = [
                str(row[1]),  # Data Conclusão
                str(row[2]),  # Número Agendamento
                str(row[3]),  # Fiscal (se visível)
                str(row[4]),  # Tipo Registro
                str(row[5]),  # Número Registro
                str(row[6]),  # Nome
                str(row[7]),  # Procedimento
                str(row[8]),  # Quantidade
            ]

            if not incluir_fiscal:
                colunas.pop(2)  # Remove "Fiscal" para usuários comuns

            try:
                data_conclusao = datetime.strptime(row[1], "%d-%m-%Y")
                bloquear_linha = (
                    (data_conclusao.year < ano_atual) or
                    (data_conclusao.year == ano_atual and data_conclusao.month < mes_atual)
                )
            except:
                bloquear_linha = False

            is_cancelado = "cancelado" in colunas[(6 if incluir_fiscal else 5)].lower()

            for j, cell in enumerate(colunas):
                item = QTableWidgetItem(cell)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
                item.setFont(default_font)

                # Estilização para procedimentos cancelados
                if is_cancelado:
                    item.setForeground(QColor(200, 0, 0))
                    item.setToolTip("🚫 Procedimento cancelado")

                    if not is_admin:
                        item.setFlags(Qt.NoItemFlags)
                    else:
                        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                # Estilização para bloqueio por mês anterior
                elif bloquear_linha:
                    item.setBackground(QColor(245, 245, 245))
                    item.setToolTip("🔒 Procedimento concluído em mês anterior")
                    if not is_admin:
                        item.setFlags(Qt.NoItemFlags)
                    else:
                        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                else:
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.table.setItem(i, j, item)

        altura_fixa = 40
        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, altura_fixa)

        self.update_agendamento_count()

    def copiar_tabela_para_clipboard(self):
        """Copia a área selecionada da tabela no formato tabulado para a área de transferência."""
        ranges = self.table.selectedRanges()
        if not ranges:
            return

        texto = []
        for sel in ranges:
            for row in range(sel.topRow(), sel.bottomRow() + 1):
                linha = []
                for col in range(sel.leftColumn(), sel.rightColumn() + 1):
                    item = self.table.item(row, col)
                    linha.append(item.text() if item else "")
                texto.append("\t".join(linha))
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(texto).strip())

    def update_agendamento_count(self, filtered_values=None):
        """ Atualiza os rótulos 'Total Agendamentos' e 'Total Procedimentos', ignorando cancelados """
        try:
            column_index = 1  # Coluna "N.º Agend."
            unique_agendamentos = set()
            total_procedimentos = 0

            for row in range(self.table.rowCount()):
                item = self.table.item(row, column_index)
                date_item = self.table.item(row, 0)  # Coluna "Dt.Conclusão"
                procedure_item = self.table.item(row, 6 if self.user_info.get("is_admin", False) or self.user_info.get(
                    "is_visitor", False) else 5)

                if item and date_item and procedure_item:
                    agendamento = item.text()
                    data_conclusao = date_item.text()
                    procedimento = procedure_item.text().lower()

                    # 🔴 SE FOR CANCELADO, NÃO CONTA NO TOTAL
                    if "cancelado" in procedimento:
                        continue

                    if not filtered_values or data_conclusao in filtered_values:
                        unique_agendamentos.add(agendamento)

                    # 🔹 Contabiliza o total de procedimentos válidos
                    total_procedimentos += 1

            total_unique = len(unique_agendamentos)
            self.total_agendamentos_label.setText(f"Total Agendamentos: {total_unique}")
            self.total_procedimentos_label.setText(f"Total Procedimentos: {total_procedimentos}")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao contar agendamentos e procedimentos:\n{str(e)}")

    def show_filter_menu(self, column_index):
        """ Exibe um menu de filtro ao clicar no cabeçalho da coluna """
        try:
            if column_index not in self.unique_column_values:
                self.unique_column_values[column_index] = set()

            # Converter valores para string antes de aplicar filtro
            all_values = set(
                str(self.original_data[row][column_index + 1])  # +1 porque o banco começa no índice 1
                for row in range(len(self.original_data))
            )

            selected_values = self.active_filters.get(column_index, all_values)

            if not all_values:
                QMessageBox.warning(self, "Aviso", "Não há valores disponíveis para filtrar nesta coluna.")
                return

            # Criar e exibir o filtro de dados, agora com seleção de mês
            self.filter_dialog = FilterDialog(
                self, column_index, sorted(all_values), selected_values,
                self.apply_filter, self.update_agendamento_count  # 🔹 Atualiza a contagem da label
            )
            self.filter_dialog.exec_()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao exibir menu de filtro:\n{str(e)}")

    def apply_filter(self, column_index, selected_values):
        """ Aplica um filtro cumulativo sem remover as opções disponíveis.
            Se nenhum valor for selecionado, remove o filtro e exibe todos os dados.
        """
        try:
            if not self.original_data:
                self.original_data = self.data[:]  # Garante que os dados originais sejam mantidos

            # Se nenhum valor for selecionado, remove o filtro dessa coluna
            if not selected_values:
                self.active_filters.pop(column_index, None)
            else:
                self.active_filters[column_index] = selected_values

            # Se nenhum filtro estiver ativo, mostra todos os dados originais
            if not self.active_filters:
                self.populate_table(self.original_data)
                return

            # Aplica todos os filtros ativos cumulativamente
            filtered_data = self.original_data[:]
            for col_index, values in self.active_filters.items():
                filtered_data = [row for row in filtered_data if str(row[col_index + 1]) in values]

            print(f"[DEBUG] Dados filtrados: {filtered_data}")  # 🔹 Debug

            self.populate_table(filtered_data)

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao aplicar filtro:\n{str(e)}")

    def clear_filter(self, column_index=None):
        """ Remove um filtro específico ou todos os filtros """
        if column_index is None:
            self.active_filters.clear()  # Remove todos os filtros
        else:
            self.active_filters.pop(column_index, None)  # Remove apenas um filtro

        # Reaplica os filtros restantes
        filtered_data = self.original_data[:]
        for col_index, values in self.active_filters.items():
            filtered_data = [row for row in filtered_data if str(row[col_index]) in values]

        self.populate_table(filtered_data)

    from datetime import datetime

    def show_context_menu(self, position: QPoint):
        """ Exibe menu de contexto apenas para procedimentos editáveis """
        try:
            index = self.table.indexAt(position)  # Obtém o índice da célula clicada

            # 🔹 Se o clique foi em uma área vazia, não exibe o menu
            if not index.isValid():
                print("[INFO] Menu de contexto cancelado - Clique em área vazia.")
                return

            # 🔹 Se for visitante, não exibe o menu
            if self.user_info.get("is_visitor", False):
                print("[INFO] Visitante não tem acesso ao menu de contexto.")
                return

            selected_row = index.row()  # Obtém a linha clicada
            if selected_row == -1:
                return  # Se nenhuma linha estiver selecionada, não exibe o menu

            # 🔹 Verifica se o usuário é administrador
            is_admin = self.user_info.get("is_admin", False)

            # Obtém a data de conclusão da linha selecionada
            item_data_conclusao = self.table.item(selected_row, 0)  # Coluna "Dt.Conclusão"
            if not item_data_conclusao or item_data_conclusao.text().strip() == "":
                return  # Se não houver data, não exibe o menu

            data_conclusao_str = item_data_conclusao.text().strip()

            try:
                # Converter string para data
                data_conclusao = datetime.strptime(data_conclusao_str, "%d-%m-%Y")

                # Obtém o mês e ano atual
                hoje = datetime.today()
                mes_atual = hoje.month
                ano_atual = hoje.year

                # Definir regra de bloqueio para usuários comuns (se for de um mês anterior ao mês atual)
                bloquear_linha = not is_admin and (
                        data_conclusao.year < ano_atual or (
                            data_conclusao.year == ano_atual and data_conclusao.month < mes_atual)
                )

            except ValueError as e:
                print(f"[ERROR] Erro ao processar a data de conclusão '{data_conclusao_str}': {e}")
                return  # Se houver erro na data, não exibe o menu

            # 🔹 Verificar se o procedimento foi cancelado
            coluna_procedimento_index = 6 if self.user_info.get("is_admin", False) or self.user_info.get("is_visitor",
                                                                                                         False) else 5
            item_procedimento = self.table.item(selected_row, coluna_procedimento_index)

            is_cancelado = item_procedimento and "cancelado" in item_procedimento.text().lower()

            # 🔹 Se for um usuário comum e a linha for bloqueada ou cancelada, não exibir o menu
            if not is_admin and (bloquear_linha or is_cancelado):
                QMessageBox.warning(self, "Ação Bloqueada", "❌ Você não pode editar este procedimento.")
                print(f"[INFO] Menu NÃO exibido - Procedimento bloqueado ({data_conclusao_str}) ou cancelado.")
                return

            # Criar menu de contexto apenas para procedimentos permitidos
            menu = QMenu(self)

            edit_quantity_action = QAction(QIcon("edit.png"), "Editar Quantidade", self)
            edit_procedure_action = QAction(QIcon("edit.png"), "Editar Procedimento Atribuído", self)
            delete_scheduling_action = QAction(QIcon("delete.png"), "Excluir Agendamento", self)
            add_procedure_action = QAction(QIcon("add.png"), "Incluir Procedimento", self)
            edit_agendamento_action = QAction(QIcon("edit.png"), "Editar Dados do Agendamento", self)


            edit_agendamento_action.triggered.connect(self.edit_agendamento)
            menu.addAction(edit_agendamento_action)

            edit_quantity_action.triggered.connect(self.edit_quantity)
            edit_procedure_action.triggered.connect(self.edit_procedure)
            delete_scheduling_action.triggered.connect(self.delete_scheduling)
            add_procedure_action.triggered.connect(self.add_procedure)

            menu.addAction(edit_quantity_action)
            menu.addAction(edit_procedure_action)
            menu.addSeparator()
            menu.addAction(delete_scheduling_action)
            menu.addAction(add_procedure_action)


            # Exibir o menu de contexto na posição do clique
            menu.exec_(self.table.viewport().mapToGlobal(position))


        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao abrir menu de contexto:\n{str(e)}")

    def edit_quantity(self):
        """ Permite editar a quantidade de um agendamento selecionado e salva no banco de dados """
        try:
            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Aviso", "Selecione um agendamento para editar a quantidade.")
                return
    
            # 🔹 Determinar a posição correta das colunas baseado no tipo de usuário
            incluir_fiscal = self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)
            col_fiscal = 2 if incluir_fiscal else None
            col_quantidade = 7 if incluir_fiscal else 6
            col_procedimento = col_quantidade - 1
    
            quantidade_item = self.table.item(selected_row, col_quantidade)
            numero_agendamento_item = self.table.item(selected_row, 1)
            procedimento_item = self.table.item(selected_row, col_procedimento)
            fiscal_item = self.table.item(selected_row, col_fiscal) if col_fiscal is not None else None
    
            if not quantidade_item or not numero_agendamento_item or not procedimento_item:
                QMessageBox.warning(self, "Erro", "Os dados do agendamento não foram encontrados.")
                return
    
            quantidade_atual = quantidade_item.text().strip()
            numero_agendamento = numero_agendamento_item.text().strip()
            procedimento = procedimento_item.text().strip()
    
            # Fiscal responsável
            fiscal_nome = fiscal_item.text().strip() if fiscal_item else self.user_info["username"]
    
            # 🔹 Se a quantidade atual contém texto (ex: "cancelado"), pedir confirmação
            if not quantidade_atual.isdigit():
                resposta = QMessageBox.question(
                    self,
                    "Confirmação",
                    f"O procedimento está cancelado com o motivo: '{quantidade_atual}'.\n"
                    "Deseja substituir por um valor numérico?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if resposta == QMessageBox.No:
                    return  # 🔚 Sai da função
                quantidade_atual = "1"  # Valor inicial para editar
    
            # 🔹 Solicita nova quantidade
            nova_quantidade, ok = QInputDialog.getInt(
                self, "Editar Quantidade", "Nova Quantidade:", int(quantidade_atual), min=1
            )
    
            if not ok:
                return  # 🔚 Sai se o usuário cancelou o diálogo
    
            # Atualiza visualmente na tabela
            self.table.setItem(selected_row, col_quantidade, QTableWidgetItem(str(nova_quantidade)))
    
            # 🔹 Atualiza no banco de dados
            conn = connect_db()
            cursor = conn.cursor()
    
            sanitized_fiscal = fiscal_nome.replace(" ", "_").lower()
            table_name = f"procedimentos_{sanitized_fiscal}"
    
            cursor.execute(f"""
                SELECT quantidade FROM {table_name}
                WHERE numero_agendamento = ? AND procedimento = ?
            """, (numero_agendamento, procedimento))
    
            resultado = cursor.fetchone()
    
            if resultado:
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET quantidade = ?
                    WHERE numero_agendamento = ? AND procedimento = ?
                """, (nova_quantidade, numero_agendamento, procedimento))
            else:
                cursor.execute(f"""
                    INSERT INTO {table_name} (numero_agendamento, procedimento, quantidade)
                    VALUES (?, ?, ?)
                """, (numero_agendamento, procedimento, nova_quantidade))
    
            conn.commit()
            conn.close()
    
            QMessageBox.information(self, "Sucesso",
                                    f"Quantidade do procedimento '{procedimento}' no agendamento '{numero_agendamento}' foi alterada com sucesso!")
            print(f"[DEBUG] Quantidade atualizada para '{nova_quantidade}' na tabela '{table_name}'.")

            detalhes = (
                f"Agendamento: {numero_agendamento}, Procedimento: {procedimento}, "
                f"Quantidade anterior: {quantidade_atual}, Nova quantidade: {nova_quantidade}"
            )
            registrar_log(self.user_info["username"], "Edição de Quantidade", detalhes)
            self.atualizar_resultado_mensal.emit()


        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao editar quantidade:\n{str(e)}")
            print(f"[ERRO] {e}")


    def edit_procedure(self):
        """ Permite editar o procedimento atribuído e salva a alteração no banco de dados """
        try:
            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Aviso", "Selecione um procedimento para editar.")
                return

            incluir_fiscal = self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)
            col_fiscal = 2 if incluir_fiscal else None
            col_procedimento = 6 if incluir_fiscal else 5
            col_quantidade = col_procedimento + 1

            procedimento_item = self.table.item(selected_row, col_procedimento)
            numero_agendamento_item = self.table.item(selected_row, 1)
            quantidade_item = self.table.item(selected_row, col_quantidade)
            fiscal_item = self.table.item(selected_row, col_fiscal) if col_fiscal is not None else None

            if not procedimento_item or not numero_agendamento_item or not quantidade_item:
                QMessageBox.warning(self, "Erro", "Os dados do agendamento não foram encontrados.")
                return

            procedimento_atual = procedimento_item.text().strip()
            numero_agendamento = numero_agendamento_item.text().strip()
            quantidade_atual = quantidade_item.text().strip()
            fiscal_nome = fiscal_item.text().strip() if fiscal_item else self.user_info["username"]

            procedimentos = [proc["name"] for proc in get_procedures()]
            if not procedimentos:
                QMessageBox.warning(self, "Erro", "Nenhum procedimento disponível para seleção.")
                return

            novo_procedimento, ok = QInputDialog.getItem(
                self, "Editar Procedimento", "Selecione o novo procedimento:",
                procedimentos, editable=False
            )
            if not ok:
                return

            # 🔹 Se for CANCELADO, perguntar o motivo
            if novo_procedimento.strip().lower() == "cancelado":
                dialog = CancelReasonDialog(self)
                if dialog.exec_():
                    motivo = dialog.get_reason()
                    if not motivo:
                        QMessageBox.warning(self, "Erro", "O motivo do cancelamento não pode ser vazio.")
                        return
                    nova_quantidade = motivo
                else:
                    return
            else:
                nova_quantidade, ok_qtd = QInputDialog.getInt(
                    self, "Quantidade", "Informe a nova quantidade:",
                    value=int(quantidade_atual) if quantidade_atual.isdigit() else 1, min=1
                )
                if not ok_qtd:
                    return

            # Atualiza a interface
            self.table.setItem(selected_row, col_procedimento, QTableWidgetItem(novo_procedimento))
            self.table.setItem(selected_row, col_quantidade, QTableWidgetItem(str(nova_quantidade)))

            # Atualizar no banco
            conn = connect_db()
            cursor = conn.cursor()

            sanitized_fiscal = fiscal_nome.replace(" ", "_").lower()
            table_name = f"procedimentos_{sanitized_fiscal}"

            cursor.execute(f"""
                SELECT quantidade FROM {table_name}
                WHERE numero_agendamento = ? AND procedimento = ?
            """, (numero_agendamento, procedimento_atual))

            resultado = cursor.fetchone()

            if resultado:
                update_query = f"""
                    UPDATE {table_name}
                    SET procedimento = ?, quantidade = ?
                    WHERE numero_agendamento = ? AND procedimento = ?
                """
                cursor.execute(update_query, (novo_procedimento, nova_quantidade, numero_agendamento, procedimento_atual))
            else:
                insert_query = f"""
                    INSERT INTO {table_name} (numero_agendamento, procedimento, quantidade)
                    VALUES (?, ?, ?)
                """
                cursor.execute(insert_query, (numero_agendamento, novo_procedimento, nova_quantidade))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Sucesso",
                                    f"Procedimento do agendamento '{numero_agendamento}' alterado com sucesso!")
            print(f"[DEBUG] Procedimento alterado para '{novo_procedimento}' na tabela '{table_name}'.")
            detalhes = (
                f"Agendamento: {numero_agendamento}, Procedimento anterior: {procedimento_atual}, "
                f"Novo procedimento: {novo_procedimento}, Quantidade: {quantidade_atual} → {nova_quantidade}"
            )
            registrar_log(self.user_info["username"], "Edição de Procedimento", detalhes)


        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao editar procedimento:\n{str(e)}")


    def add_procedure(self):
        """ Permite incluir um novo procedimento e duplicar a linha selecionada """
        try:
            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Aviso", "Selecione um agendamento para duplicar com um novo procedimento.")
                return
    
            # 🔹 Obtem os procedimentos válidos (excluindo 'cancelado')
            procedimentos = [proc["name"] for proc in get_procedures() if proc["name"].lower() != "cancelado"]
            if not procedimentos:
                QMessageBox.warning(self, "Erro", "Nenhum procedimento disponível para seleção.")
                return
    
            # 🔹 Exibir seleção
            novo_procedimento, ok = QInputDialog.getItem(
                self, "Incluir Procedimento", "Selecione o procedimento:",
                procedimentos, editable=False
            )
            if ok:
                nova_quantidade, qtd_ok = QInputDialog.getInt(self, "Quantidade", "Informe a quantidade:", min=1)
                if qtd_ok:
                    row_count = self.table.rowCount()
                    self.table.insertRow(row_count)
    
                    for col in range(self.table.columnCount()):
                        item = self.table.item(selected_row, col)
                        if item:
                            self.table.setItem(row_count, col, QTableWidgetItem(item.text()))
    
                    # Atualiza as colunas específicas com o novo procedimento e quantidade
                    incluir_fiscal = self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)
                    col_procedimento = 6 if incluir_fiscal else 5
                    col_quantidade = col_procedimento + 1
    
                    self.table.setItem(row_count, col_procedimento, QTableWidgetItem(novo_procedimento))
                    self.table.setItem(row_count, col_quantidade, QTableWidgetItem(str(nova_quantidade)))

                    numero_agendamento = self.table.item(selected_row, 1).text()
                    detalhes = (
                        f"Agendamento: {numero_agendamento}, Novo procedimento adicionado: {novo_procedimento}, "
                        f"Quantidade: {nova_quantidade} (linha duplicada)"
                    )
                    registrar_log(self.user_info["username"], "Inclusão de Procedimento", detalhes)


        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao incluir novo procedimento:\n{str(e)}")

    def delete_scheduling(self):
        """ Exclui a linha do agendamento selecionado e remove do banco de dados """
        try:
            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Aviso", "Selecione um agendamento para excluir.")
                return

            # 🔹 Captura os dados ANTES de remover a linha
            numero_agendamento = self.table.item(selected_row, 1).text()
            procedimento = self.table.item(selected_row, 6 if self.user_info.get("is_admin", False) else 5).text()
            quantidade = self.table.item(selected_row, 7 if self.user_info.get("is_admin", False) else 6).text()

            confirm = QMessageBox.question(
                self, "Confirmar Exclusão",
                f"Tem certeza que deseja excluir o agendamento '{numero_agendamento}' com o procedimento '{procedimento}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                # 🔹 Remover da interface
                self.table.removeRow(selected_row)

                # 🔹 Remover do banco
                try:
                    fiscal_nome = self.user_info["username"]
                    sanitized_fiscal = fiscal_nome.replace(" ", "_").lower()
                    table_name = f"procedimentos_{sanitized_fiscal}"

                    conn = connect_db()
                    cursor = conn.cursor()

                    cursor.execute(f"""
                        DELETE FROM {table_name}
                        WHERE numero_agendamento = ? AND procedimento = ?
                    """, (numero_agendamento, procedimento))

                    conn.commit()
                    conn.close()

                    print(f"[DEBUG] Excluído do banco: {numero_agendamento} - {procedimento}")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao excluir do banco de dados:\n{e}")
                    return

                # 🔹 Log da ação
                detalhes = (
                    f"Agendamento: {numero_agendamento}, Procedimento: {procedimento}, "
                    f"Quantidade: {quantidade} (antes da exclusão)"
                )
                registrar_log(self.user_info["username"], "Exclusão de Agendamento", detalhes)

                # 🔹 Atualiza resultado mensal
                self.atualizar_resultado_mensal.emit()
                self.atualizar_resultados_fiscal.emit()


        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao excluir agendamento:\n{str(e)}")

    def edit_agendamento(self):
        try:
            selected_row = self.table.currentRow()
            if selected_row == -1:
                QMessageBox.warning(self, "Aviso", "Selecione um agendamento para editar.")
                return

            # Define posições das colunas
            incluir_fiscal = self.user_info.get("is_admin", False) or self.user_info.get("is_visitor", False)
            col_data = 0
            col_numero = 1
            col_tipo = 3 if incluir_fiscal else 2
            col_registro = 4 if incluir_fiscal else 3
            col_nome = 5 if incluir_fiscal else 4
            col_procedimento = 6 if incluir_fiscal else 5

            # Pega dados atuais
            data_conclusao = self.table.item(selected_row, col_data).text().strip()
            numero_agendamento = self.table.item(selected_row, col_numero).text().strip()
            tipo_registro = self.table.item(selected_row, col_tipo).text().strip()
            registro = self.table.item(selected_row, col_registro).text().strip()
            nome = self.table.item(selected_row, col_nome).text().strip()
            procedimento = self.table.item(selected_row, col_procedimento).text().strip()

            dialog = EditAgendamentoDialog(
                data_conclusao, numero_agendamento, tipo_registro, registro, nome, parent=self
            )
            if dialog.exec_() == QDialog.Accepted:
                novos_dados = dialog.get_data()

                # Atualiza na interface
                self.table.setItem(selected_row, col_data, QTableWidgetItem(novos_dados["data_conclusao"]))
                self.table.setItem(selected_row, col_numero, QTableWidgetItem(novos_dados["numero_agendamento"]))
                self.table.setItem(selected_row, col_tipo, QTableWidgetItem(novos_dados["tipo_registro"]))
                self.table.setItem(selected_row, col_registro, QTableWidgetItem(novos_dados["registro"]))
                self.table.setItem(selected_row, col_nome, QTableWidgetItem(novos_dados["nome"]))

                # Atualiza no banco de dados
                fiscal_nome = self.user_info["username"]
                sanitized_fiscal = fiscal_nome.replace(" ", "_").lower()
                table_name = f"procedimentos_{sanitized_fiscal}"

                conn = connect_db()
                cursor = conn.cursor()

                cursor.execute(f"""
                    UPDATE {table_name}
                    SET data_conclusao = ?, numero_agendamento = ?, tipo_registro = ?, numero_registro = ?, nome = ?
                    WHERE numero_agendamento = ? AND procedimento = ?
                """, (
                    novos_dados["data_conclusao"],
                    novos_dados["numero_agendamento"],
                    novos_dados["tipo_registro"],
                    novos_dados["registro"],  # Esse campo corresponde à coluna 'numero_registro' no banco
                    novos_dados["nome"],
                    numero_agendamento,  # WHERE antigo numero_agendamento
                    procedimento  # WHERE procedimento
                ))

                conn.commit()
                conn.close()

                # Registrar log
                detalhes = (
                    f"Agendamento: {numero_agendamento} → {novos_dados['numero_agendamento']}, "
                    f"Data: {data_conclusao} → {novos_dados['data_conclusao']}, "
                    f"Tipo: {tipo_registro} → {novos_dados['tipo_registro']}, "
                    f"Registro: {registro} → {novos_dados['registro']}, "
                    f"Nome: {nome} → {novos_dados['nome']}"
                )
                registrar_log(self.user_info["username"], "Edição de Dados do Agendamento", detalhes)

                QMessageBox.information(self, "Sucesso", "Dados do agendamento atualizados com sucesso!")

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao editar dados do agendamento:\n{str(e)}")

    def registrar_fonte(pdf):
        pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf", uni=True)
        pdf.add_font("DejaVu", "I", "fonts/DejaVuSans-Oblique.ttf", uni=True)

    def exportar_pdf_excel(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from fpdf import FPDF
        import pandas as pd

        try:
            caminho, _ = QFileDialog.getSaveFileName(
                self,
                "Exportar Relatório de Atribuições",
                "",
                "Arquivo Excel (*.xlsx);;Arquivo PDF (*.pdf)"
            )

            if not caminho:
                return

            # Extrair dados da tabela
            # Extrair dados da tabela
            dados = []
            for row in range(self.table.rowCount()):
                linha = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    # Remove tabulações e outros caracteres problemáticos
                    texto = item.text() if item else ""
                    texto = texto.replace('\t', ' ').replace('\n', ' ').replace('\r', ' ')
                    linha.append(texto)
                dados.append(linha)

            colunas = [
                self.table.horizontalHeaderItem(i).text()
                for i in range(self.table.columnCount())
            ]

            df = pd.DataFrame(dados, columns=colunas)

            # ===================== EXCEL =====================
            if caminho.endswith(".xlsx"):
                df.to_excel(caminho, index=False)
                QMessageBox.information(self, "Sucesso", "Arquivo Excel exportado com sucesso!")

            # ====================== PDF ======================
            elif caminho.endswith(".pdf"):



                class PDF(FPDF):
                    def __init__(self):
                        super().__init__('L', 'mm', 'A4')
                        self.set_auto_page_break(auto=True, margin=10)
                        # Registrar todas as variações da fonte no __init__
                        self.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)
                        self.add_font("DejaVu", "B", "fonts/DejaVuSans-Bold.ttf", uni=True)
                        self.add_font("DejaVu", "I", "fonts/DejaVuSans-Oblique.ttf", uni=True)

                    def header(self):
                        self.set_font("DejaVu", "B", 12)
                        self.cell(0, 10, "Relatório de Atribuições", 0, 1, "C")
                        self.ln(3)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("DejaVu", "I", 8)
                        self.cell(0, 10, f"Página {self.page_no()}", 0, 0, "C")

                    def get_row_height(self, row, col_widths, line_height=6):
                        max_lines = 1
                        for i, cell in enumerate(row):
                            text = str(cell)
                            lines = self.multi_cell(
                                col_widths[i],
                                line_height,
                                text,
                                split_only=True
                            )
                            max_lines = max(max_lines, len(lines))
                        return max_lines * line_height

                    def render_table(self, colunas, dados, col_widths):
                        # Cabeçalho
                        self.set_font("DejaVu", "B", 8)
                        self.set_fill_color(240, 240, 240)

                        for i, col in enumerate(colunas):
                            self.cell(col_widths[i], 8, col, 1, 0, 'C', True)
                        self.ln()

                        # Dados
                        self.set_font("DejaVu", "", 8)

                        for row in dados:
                            y_start = self.get_y()
                            row_height = self.get_row_height(row, col_widths)

                            # Verifica se precisa quebrar página
                            if y_start + row_height > self.h - 20:
                                self.add_page()
                                y_start = self.get_y()

                            # Desenha cada célula da linha
                            for i, cell in enumerate(row):
                                x_pos = self.l_margin + sum(col_widths[:i])
                                self.set_xy(x_pos, y_start)
                                self.multi_cell(
                                    col_widths[i],
                                    6,
                                    str(cell),
                                    border=1,
                                    align='L'
                                )

                            # Move para a próxima linha
                            self.set_xy(self.l_margin, y_start + row_height)

                def calcular_larguras(colunas, dados):
                    temp_pdf = FPDF()
                    temp_pdf.add_font("DejaVu", "", "fonts/DejaVuSans.ttf", uni=True)  # Registra a fonte primeiro
                    temp_pdf.set_font("DejaVu", size=8)

                    largura_total = 277  # A4 paisagem
                    larguras = []

                    for i, col in enumerate(colunas):
                        largura = temp_pdf.get_string_width(col) + 4
                        for row in dados:
                            largura = max(
                                largura,
                                temp_pdf.get_string_width(str(row[i])) + 4
                            )
                        larguras.append(min(max(largura, 20), 60))

                    proporcao = largura_total / sum(larguras)
                    return [w * proporcao for w in larguras]

                col_widths = calcular_larguras(colunas, dados)

                pdf = PDF()
                pdf.add_page()
                pdf.render_table(colunas, dados, col_widths)
                pdf.output(caminho)

                QMessageBox.information(self, "Sucesso", "Arquivo PDF exportado com sucesso!")

            else:
                QMessageBox.warning(
                    self,
                    "Formato inválido",
                    "Escolha um formato válido: .xlsx ou .pdf"
                )

        except Exception as e:
            import traceback
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao exportar relatório:\n{str(e)}\n\n{traceback.format_exc()}"
            )


class EditAgendamentoDialog(QDialog):
    def __init__(self, data_conclusao, numero_agendamento, tipo_registro, registro, nome, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Dados do Agendamento")
        self.setFixedSize(400, 300)

        layout = QVBoxLayout()

        # Campos
        self.data_input = QLineEdit(data_conclusao)
        self.numero_input = QLineEdit(numero_agendamento)
        self.tipo_input = QLineEdit(tipo_registro)
        self.registro_input = QLineEdit(registro)
        self.nome_input = QLineEdit(nome)

        # Adiciona ao layout
        layout.addWidget(QLabel("Data de Conclusão (dd-mm-aaaa):"))
        layout.addWidget(self.data_input)

        layout.addWidget(QLabel("Número do Agendamento:"))
        layout.addWidget(self.numero_input)

        layout.addWidget(QLabel("Tipo de Registro:"))
        layout.addWidget(self.tipo_input)

        layout.addWidget(QLabel("Registro:"))
        layout.addWidget(self.registro_input)

        layout.addWidget(QLabel("Nome:"))
        layout.addWidget(self.nome_input)

        # Botões
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Salvar")
        self.cancel_button = QPushButton("Cancelar")

        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_data(self):
        return {
            "data_conclusao": self.data_input.text().strip(),
            "numero_agendamento": self.numero_input.text().strip(),
            "tipo_registro": self.tipo_input.text().strip(),
            "registro": self.registro_input.text().strip(),
            "nome": self.nome_input.text().strip()
        }




