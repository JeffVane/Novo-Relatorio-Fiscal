import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QComboBox,
                             QFileDialog, QMessageBox, QTableView, QHeaderView)
from PyQt6.QtCore import Qt, QAbstractTableModel
import sqlite3
from configparser import ConfigParser

# Tenta importar o módulo MySQL, mas continua mesmo se falhar
try:
    import mysql.connector

    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False


class DatabaseConnection:
    """Classe para gerenciar conexões com diferentes tipos de bancos de dados"""

    def __init__(self, db_type, connection_params):
        self.db_type = db_type
        self.connection_params = connection_params
        self.connection = None
        self.cursor = None

    def connect(self):
        """Estabelece conexão com o banco de dados"""
        try:
            if self.db_type == "SQLite":
                self.connection = sqlite3.connect(self.connection_params["database"])
            elif self.db_type == "MySQL":
                if not MYSQL_AVAILABLE:
                    raise ImportError(
                        "O módulo mysql.connector não está instalado. Execute 'pip install mysql-connector-python' para habilitar o suporte a MySQL.")
                self.connection = mysql.connector.connect(
                    host=self.connection_params["host"],
                    user=self.connection_params["user"],
                    password=self.connection_params["password"],
                    database=self.connection_params["database"]
                )
            self.cursor = self.connection.cursor()
            return True
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            return False

    def disconnect(self):
        """Fecha a conexão com o banco de dados"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def get_tables(self):
        """Retorna a lista de tabelas do banco de dados"""
        if not self.connection:
            return []

        tables = []
        try:
            if self.db_type == "SQLite":
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in self.cursor.fetchall()]
            elif self.db_type == "MySQL":
                self.cursor.execute("SHOW TABLES")
                tables = [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Erro ao obter tabelas: {e}")

        return tables

    def get_columns(self, table_name):
        """Retorna a lista de colunas de uma tabela específica"""
        if not self.connection:
            return []

        columns = []
        try:
            if self.db_type == "SQLite":
                self.cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [row[1] for row in self.cursor.fetchall()]
            elif self.db_type == "MySQL":
                self.cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                columns = [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Erro ao obter colunas: {e}")

        return columns

    def get_column_data(self, table_name, column_name):
        """Retorna os dados de uma coluna específica"""
        if not self.connection:
            return []

        data = []
        try:
            self.cursor.execute(f"SELECT {column_name} FROM {table_name}")
            data = [row[0] for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Erro ao obter dados da coluna: {e}")

        return data

    def insert_data(self, table_name, column_name, data):
        """Insere dados em uma coluna específica sem alterar as outras colunas"""
        if not self.connection:
            return False

        try:
            # Verifica se a tabela está vazia ou tem linhas insuficientes
            self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = self.cursor.fetchone()[0]

            # Três modos de operação: atualização, inserção, ou modo misto
            if count == 0:
                # MODO INSERÇÃO: Tabela vazia - inserir novas linhas
                # Primeiro, obtém a estrutura da tabela
                if self.db_type == "SQLite":
                    self.cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [row[1] for row in self.cursor.fetchall()]
                elif self.db_type == "MySQL":
                    self.cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                    columns = [row[0] for row in self.cursor.fetchall()]

                # Prepara a inserção - coluna especificada tem valores, outras são NULL
                for value in data:
                    # Cria um dicionário onde todas as colunas são NULL exceto a especificada
                    values_dict = {col: "NULL" for col in columns}

                    if isinstance(value, str):
                        value = value.replace("'", "''")  # Escape de aspas simples
                        values_dict[column_name] = f"'{value}'"
                    else:
                        values_dict[column_name] = str(value)

                    # Constrói a consulta de inserção
                    columns_str = ", ".join(columns)
                    values_str = ", ".join([values_dict[col] for col in columns])
                    insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"
                    self.cursor.execute(insert_query)

            elif count < len(data):
                # MODO MISTO: Atualiza registros existentes e insere novos
                # Primeiro obtém IDs existentes
                self.cursor.execute(f"SELECT id FROM {table_name}")
                ids = [row[0] for row in self.cursor.fetchall()]

                # Atualiza registros existentes
                for i, row_id in enumerate(ids):
                    value = data[i]
                    if isinstance(value, str):
                        value = value.replace("'", "''")  # Escape de aspas simples
                        self.cursor.execute(f"UPDATE {table_name} SET {column_name} = '{value}' WHERE id = {row_id}")
                    else:
                        self.cursor.execute(f"UPDATE {table_name} SET {column_name} = {value} WHERE id = {row_id}")

                # Obtém estrutura da tabela para inserir novos registros
                if self.db_type == "SQLite":
                    self.cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [row[1] for row in self.cursor.fetchall()]
                elif self.db_type == "MySQL":
                    self.cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                    columns = [row[0] for row in self.cursor.fetchall()]

                # Insere registros adicionais
                for i in range(count, len(data)):
                    value = data[i]
                    values_dict = {col: "NULL" for col in columns}

                    if isinstance(value, str):
                        value = value.replace("'", "''")
                        values_dict[column_name] = f"'{value}'"
                    else:
                        values_dict[column_name] = str(value)

                    columns_str = ", ".join(columns)
                    values_str = ", ".join([values_dict[col] for col in columns])
                    insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str})"
                    self.cursor.execute(insert_query)

            else:
                # MODO ATUALIZAÇÃO: Atualiza registros existentes
                # Obtém IDs de todas as linhas na tabela de destino
                self.cursor.execute(f"SELECT id FROM {table_name}")
                ids = [row[0] for row in self.cursor.fetchall()]

                # Atualiza apenas os registros que têm correspondência
                for i, row_id in enumerate(ids):
                    if i >= len(data):
                        break  # Não temos dados suficientes para atualizar todas as linhas

                    value = data[i]
                    if isinstance(value, str):
                        value = value.replace("'", "''")  # Escape de aspas simples
                        self.cursor.execute(f"UPDATE {table_name} SET {column_name} = '{value}' WHERE id = {row_id}")
                    else:
                        self.cursor.execute(f"UPDATE {table_name} SET {column_name} = {value} WHERE id = {row_id}")

            self.connection.commit()
            return True
        except Exception as e:
            print(f"Erro ao inserir dados: {e}")
            return False


class DataModel(QAbstractTableModel):
    """Modelo para visualização de dados em tabelas"""

    def __init__(self, data=None):
        super().__init__()
        self._data = data if data else []
        self._header = ["Valor"] if data else []

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return 1

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(self._data[index.row()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._header[section]
        return None


class DatabaseTransferApp(QMainWindow):
    """Aplicativo principal para transferência de dados entre bancos de dados"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Transferência de Dados entre Bancos de Dados")
        self.setGeometry(100, 100, 1000, 700)

        self.source_connection = None
        self.target_connection = None
        self.source_data = []

        self.init_ui()

    def init_ui(self):
        """Inicializa a interface do usuário"""
        central_widget = QWidget()
        main_layout = QVBoxLayout()

        # Layout para conexão de origem
        source_group_layout = QVBoxLayout()
        source_group_layout.addWidget(QLabel("<b>Banco de Dados de Origem</b>"))

        # Seleção do tipo de banco de dados de origem
        source_type_layout = QHBoxLayout()
        source_type_layout.addWidget(QLabel("Tipo de Banco:"))
        self.source_type_combo = QComboBox()

        # Adiciona os tipos de banco de dados disponíveis
        db_types = ["SQLite"]
        if MYSQL_AVAILABLE:
            db_types.append("MySQL")
        self.source_type_combo.addItems(db_types)
        source_type_layout.addWidget(self.source_type_combo)

        # Seleção do arquivo SQLite de origem
        self.source_sqlite_button = QPushButton("Selecionar Arquivo SQLite")
        self.source_sqlite_button.clicked.connect(self.select_source_sqlite)
        source_type_layout.addWidget(self.source_sqlite_button)

        # Botão de conexão MySQL de origem
        self.source_mysql_button = QPushButton("Configurar MySQL")
        self.source_mysql_button.clicked.connect(lambda: self.configure_mysql("source"))
        source_type_layout.addWidget(self.source_mysql_button)
        self.source_mysql_button.setVisible(False)

        # Botão de conexão
        self.source_connect_button = QPushButton("Conectar")
        self.source_connect_button.clicked.connect(self.connect_source)
        source_type_layout.addWidget(self.source_connect_button)

        source_group_layout.addLayout(source_type_layout)

        # Seleção de tabela de origem
        source_table_layout = QHBoxLayout()
        source_table_layout.addWidget(QLabel("Tabela:"))
        self.source_table_combo = QComboBox()
        self.source_table_combo.currentIndexChanged.connect(self.load_source_columns)
        source_table_layout.addWidget(self.source_table_combo)
        source_group_layout.addLayout(source_table_layout)

        # Seleção de coluna de origem
        source_column_layout = QHBoxLayout()
        source_column_layout.addWidget(QLabel("Coluna:"))
        self.source_column_combo = QComboBox()
        self.source_column_combo.currentIndexChanged.connect(self.load_source_data)
        source_column_layout.addWidget(self.source_column_combo)
        source_group_layout.addLayout(source_column_layout)

        main_layout.addLayout(source_group_layout)

        # Visualização de dados da coluna de origem
        main_layout.addWidget(QLabel("<b>Dados da Coluna de Origem</b>"))
        self.source_table_view = QTableView()
        self.source_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.source_table_view)

        # Layout para conexão de destino
        target_group_layout = QVBoxLayout()
        target_group_layout.addWidget(QLabel("<b>Banco de Dados de Destino</b>"))

        # Seleção do tipo de banco de dados de destino
        target_type_layout = QHBoxLayout()
        target_type_layout.addWidget(QLabel("Tipo de Banco:"))
        self.target_type_combo = QComboBox()

        # Adiciona os tipos de banco de dados disponíveis
        db_types = ["SQLite"]
        if MYSQL_AVAILABLE:
            db_types.append("MySQL")
        self.target_type_combo.addItems(db_types)
        target_type_layout.addWidget(self.target_type_combo)

        # Seleção do arquivo SQLite de destino
        self.target_sqlite_button = QPushButton("Selecionar Arquivo SQLite")
        self.target_sqlite_button.clicked.connect(self.select_target_sqlite)
        target_type_layout.addWidget(self.target_sqlite_button)

        # Botão de conexão MySQL de destino
        self.target_mysql_button = QPushButton("Configurar MySQL")
        self.target_mysql_button.clicked.connect(lambda: self.configure_mysql("target"))
        target_type_layout.addWidget(self.target_mysql_button)
        self.target_mysql_button.setVisible(False)

        # Botão de conexão
        self.target_connect_button = QPushButton("Conectar")
        self.target_connect_button.clicked.connect(self.connect_target)
        target_type_layout.addWidget(self.target_connect_button)

        target_group_layout.addLayout(target_type_layout)

        # Seleção de tabela de destino
        target_table_layout = QHBoxLayout()
        target_table_layout.addWidget(QLabel("Tabela:"))
        self.target_table_combo = QComboBox()
        self.target_table_combo.currentIndexChanged.connect(self.load_target_columns)
        target_table_layout.addWidget(self.target_table_combo)
        target_group_layout.addLayout(target_table_layout)

        # Seleção de coluna de destino
        target_column_layout = QHBoxLayout()
        target_column_layout.addWidget(QLabel("Coluna:"))
        self.target_column_combo = QComboBox()
        target_column_layout.addWidget(self.target_column_combo)
        target_group_layout.addLayout(target_column_layout)

        main_layout.addLayout(target_group_layout)

        # Botão para transferir dados
        transfer_layout = QHBoxLayout()
        self.transfer_button = QPushButton("Transferir Dados")
        self.transfer_button.clicked.connect(self.transfer_data)
        transfer_layout.addWidget(self.transfer_button)
        main_layout.addLayout(transfer_layout)

        # Configuração da interface gráfica
        self.source_type_combo.currentIndexChanged.connect(self.update_source_buttons)
        self.target_type_combo.currentIndexChanged.connect(self.update_target_buttons)

        # Atualize os botões visíveis para o estado inicial
        self.update_source_buttons()
        self.update_target_buttons()

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def update_source_buttons(self):
        """Atualiza os botões visíveis baseado no tipo de banco de dados selecionado"""
        is_sqlite = self.source_type_combo.currentText() == "SQLite"
        self.source_sqlite_button.setVisible(is_sqlite)
        self.source_mysql_button.setVisible(not is_sqlite)

    def update_target_buttons(self):
        """Atualiza os botões visíveis baseado no tipo de banco de dados selecionado"""
        is_sqlite = self.target_type_combo.currentText() == "SQLite"
        self.target_sqlite_button.setVisible(is_sqlite)
        self.target_mysql_button.setVisible(not is_sqlite)

    def select_source_sqlite(self):
        """Seleciona o arquivo SQLite de origem"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados SQLite", "",
                                                   "SQLite Files (*.db *.sqlite *.db3);;All Files (*)")
        if file_name:
            self.source_sqlite_path = file_name
            self.source_sqlite_button.setText(os.path.basename(file_name))

    def select_target_sqlite(self):
        """Seleciona o arquivo SQLite de destino"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados SQLite", "",
                                                   "SQLite Files (*.db *.sqlite *.db3);;All Files (*)")
        if file_name:
            self.target_sqlite_path = file_name
            self.target_sqlite_button.setText(os.path.basename(file_name))

    def configure_mysql(self, connection_type):
        """Configura a conexão MySQL"""
        # Em uma aplicação real, você pode implementar um diálogo de configuração
        # Para simplificar, usaremos valores padrão
        if connection_type == "source":
            self.source_mysql_config = {
                "host": "localhost",
                "user": "root",
                "password": "",
                "database": "source_db"
            }
            QMessageBox.information(self, "MySQL Configurado", "Configuração MySQL de origem definida!")
        else:
            self.target_mysql_config = {
                "host": "localhost",
                "user": "root",
                "password": "",
                "database": "target_db"
            }
            QMessageBox.information(self, "MySQL Configurado", "Configuração MySQL de destino definida!")

    def connect_source(self):
        """Estabelece a conexão com o banco de dados de origem"""
        try:
            db_type = self.source_type_combo.currentText()

            if db_type == "SQLite":
                if not hasattr(self, 'source_sqlite_path'):
                    QMessageBox.warning(self, "Erro", "Selecione um arquivo SQLite primeiro.")
                    return
                connection_params = {"database": self.source_sqlite_path}
            else:  # MySQL
                if not hasattr(self, 'source_mysql_config'):
                    QMessageBox.warning(self, "Erro", "Configure a conexão MySQL primeiro.")
                    return
                connection_params = self.source_mysql_config

            # Fecha a conexão anterior se existir
            if self.source_connection:
                self.source_connection.disconnect()

            # Cria uma nova conexão
            self.source_connection = DatabaseConnection(db_type, connection_params)
            if self.source_connection.connect():
                self.load_source_tables()
                QMessageBox.information(self, "Sucesso",
                                        "Conexão com o banco de dados de origem estabelecida com sucesso!")
            else:
                QMessageBox.critical(self, "Erro", "Falha ao conectar ao banco de dados de origem.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao conectar: {str(e)}")

    def connect_target(self):
        """Estabelece a conexão com o banco de dados de destino"""
        try:
            db_type = self.target_type_combo.currentText()

            if db_type == "SQLite":
                if not hasattr(self, 'target_sqlite_path'):
                    QMessageBox.warning(self, "Erro", "Selecione um arquivo SQLite primeiro.")
                    return
                connection_params = {"database": self.target_sqlite_path}
            else:  # MySQL
                if not hasattr(self, 'target_mysql_config'):
                    QMessageBox.warning(self, "Erro", "Configure a conexão MySQL primeiro.")
                    return
                connection_params = self.target_mysql_config

            # Fecha a conexão anterior se existir
            if self.target_connection:
                self.target_connection.disconnect()

            # Cria uma nova conexão
            self.target_connection = DatabaseConnection(db_type, connection_params)
            if self.target_connection.connect():
                self.load_target_tables()
                QMessageBox.information(self, "Sucesso",
                                        "Conexão com o banco de dados de destino estabelecida com sucesso!")
            else:
                QMessageBox.critical(self, "Erro", "Falha ao conectar ao banco de dados de destino.")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao conectar: {str(e)}")

    def load_source_tables(self):
        """Carrega as tabelas do banco de dados de origem"""
        if not self.source_connection:
            return

        self.source_table_combo.clear()
        tables = self.source_connection.get_tables()
        self.source_table_combo.addItems(tables)

    def load_target_tables(self):
        """Carrega as tabelas do banco de dados de destino"""
        if not self.target_connection:
            return

        self.target_table_combo.clear()
        tables = self.target_connection.get_tables()
        self.target_table_combo.addItems(tables)

    def load_source_columns(self):
        """Carrega as colunas da tabela de origem selecionada"""
        if not self.source_connection:
            return

        self.source_column_combo.clear()
        table_name = self.source_table_combo.currentText()
        if table_name:
            columns = self.source_connection.get_columns(table_name)
            self.source_column_combo.addItems(columns)

    def load_target_columns(self):
        """Carrega as colunas da tabela de destino selecionada"""
        if not self.target_connection:
            return

        self.target_column_combo.clear()
        table_name = self.target_table_combo.currentText()
        if table_name:
            columns = self.target_connection.get_columns(table_name)
            self.target_column_combo.addItems(columns)

    def load_source_data(self):
        """Carrega os dados da coluna de origem selecionada"""
        if not self.source_connection:
            return

        table_name = self.source_table_combo.currentText()
        column_name = self.source_column_combo.currentText()

        if table_name and column_name:
            self.source_data = self.source_connection.get_column_data(table_name, column_name)
            model = DataModel(self.source_data)
            self.source_table_view.setModel(model)

    def transfer_data(self):
        """Transfere os dados da coluna de origem para a coluna de destino"""
        if not self.source_connection or not self.target_connection:
            QMessageBox.warning(self, "Erro",
                                "Estabeleça conexões com os bancos de dados de origem e destino primeiro.")
            return

        if not self.source_data:
            QMessageBox.warning(self, "Erro", "Não há dados para transferir.")
            return

        target_table = self.target_table_combo.currentText()
        target_column = self.target_column_combo.currentText()

        if not target_table or not target_column:
            QMessageBox.warning(self, "Erro", "Selecione a tabela e coluna de destino.")
            return

        # Verifica a quantidade de dados a serem transferidos
        num_records = len(self.source_data)

        # Verifica a quantidade de registros na tabela de destino
        self.target_connection.cursor.execute(f"SELECT COUNT(*) FROM {target_table}")
        dest_records = self.target_connection.cursor.fetchone()[0]

        # Solicita confirmação se for inserir novos registros
        if dest_records == 0:
            msg = f"A tabela de destino está vazia. Serão inseridos {num_records} novos registros com valores apenas na coluna '{target_column}'."
            confirm = QMessageBox.question(self, "Confirmação", msg,
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
        elif dest_records < num_records:
            msg = f"A tabela de destino tem {dest_records} registros, mas você está tentando transferir {num_records} valores.\n"
            msg += f"Os primeiros {dest_records} registros serão atualizados e {num_records - dest_records} novos registros serão inseridos."
            confirm = QMessageBox.question(self, "Confirmação", msg,
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return

        success = self.target_connection.insert_data(target_table, target_column, self.source_data)

        if success:
            QMessageBox.information(self, "Sucesso", "Dados transferidos com sucesso!")
        else:
            QMessageBox.critical(self, "Erro", "Falha ao transferir dados.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DatabaseTransferApp()

    # Exibe uma mensagem sobre o suporte ao MySQL
    if not MYSQL_AVAILABLE:
        QMessageBox.information(window, "Informação",
                                "O suporte a MySQL não está disponível.\n"
                                "Para habilitar, instale o pacote 'mysql-connector-python':\n"
                                "pip install mysql-connector-python")

    window.show()
    sys.exit(app.exec())