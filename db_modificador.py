import sys
import sqlite3
from PyQt5 import QtWidgets, QtGui, QtCore


class DBEditor(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Editor de Banco de Dados SQLite")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
                font-family: Arial;
                font-size: 14px;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #005A9E;
            }
            QPushButton:hover {
                background-color: #005A9E;
            }
            QComboBox, QTableWidget {
                background-color: #3b3b3b;
                color: white;
                font-size: 14px;
                border-radius: 5px;
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #0078D7;
                color: white;
                padding: 5px;
                font-size: 14px;
                border: none;
            }
            QTableWidget {
                gridline-color: #444;
                selection-background-color: #005A9E;
            }
        """)

        layout = QtWidgets.QVBoxLayout()

        # Seção de seleção do banco de dados
        db_layout = QtWidgets.QHBoxLayout()
        self.btn_select_db = QtWidgets.QPushButton("📂 Selecionar Banco de Dados")
        self.btn_select_db.clicked.connect(self.load_db)
        db_layout.addWidget(self.btn_select_db)

        self.table_select = QtWidgets.QComboBox()
        self.table_select.setMinimumWidth(200)
        self.table_select.currentIndexChanged.connect(self.load_table_data)
        db_layout.addWidget(self.table_select)
        layout.addLayout(db_layout)

        # Tabela de visualização dos dados
        self.table_view = QtWidgets.QTableWidget()
        self.table_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        layout.addWidget(self.table_view)

        # Botões de ação
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_save = QtWidgets.QPushButton("💾 Salvar Alterações")
        self.btn_save.clicked.connect(self.save_changes)
        btn_layout.addWidget(self.btn_save)

        self.btn_delete = QtWidgets.QPushButton("❌ Excluir Linha")
        self.btn_delete.clicked.connect(self.delete_selected_row)
        btn_layout.addWidget(self.btn_delete)

        self.btn_delete_table = QtWidgets.QPushButton("🗑 Excluir Tabela")
        self.btn_delete_table.clicked.connect(self.delete_selected_table)
        btn_layout.addWidget(self.btn_delete_table)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.db_path = ""
        self.connection = None

    def load_db(self):
        options = QtWidgets.QFileDialog.Options()
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecionar Banco de Dados", "",
                                                             "SQLite Files (*.db);;All Files (*)", options=options)
        if file_path:
            self.db_path = file_path
            self.connection = sqlite3.connect(self.db_path)
            self.load_tables()

    def load_tables(self):
        if self.connection:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            self.table_select.clear()
            self.table_select.addItems([table[0] for table in tables])

    def load_table_data(self):
        if self.connection and self.table_select.currentText():
            table_name = self.table_select.currentText()
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT rowid, * FROM {table_name}")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            self.table_view.setColumnCount(len(columns))
            self.table_view.setRowCount(len(rows))
            self.table_view.setHorizontalHeaderLabels(columns)

            for row_idx, row in enumerate(rows):
                for col_idx, cell in enumerate(row):
                    self.table_view.setItem(row_idx, col_idx, QtWidgets.QTableWidgetItem(str(cell)))

    def save_changes(self):
        if self.connection and self.table_select.currentText():
            table_name = self.table_select.currentText()
            cursor = self.connection.cursor()

            for row_idx in range(self.table_view.rowCount()):
                values = []
                for col_idx in range(self.table_view.columnCount()):
                    item = self.table_view.item(row_idx, col_idx)
                    values.append(item.text() if item else "NULL")

                set_clause = ", ".join(
                    [f"{self.table_view.horizontalHeaderItem(i).text()}=?" for i in range(1, len(values))])
                cursor.execute(f"UPDATE {table_name} SET {set_clause} WHERE rowid=?", values[1:] + [values[0]])

            self.connection.commit()
            QtWidgets.QMessageBox.information(self, "✅ Sucesso", "Alterações salvas com sucesso!")

    def delete_selected_row(self):
        selected_row = self.table_view.currentRow()
        if selected_row != -1:
            rowid_item = self.table_view.item(selected_row, 0)
            if rowid_item:
                rowid = rowid_item.text()
                table_name = self.table_select.currentText()

                confirm = QtWidgets.QMessageBox.question(
                    self, "⚠ Confirmação", "Tem certeza que deseja excluir esta linha?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

                if confirm == QtWidgets.QMessageBox.Yes:
                    cursor = self.connection.cursor()
                    cursor.execute(f"DELETE FROM {table_name} WHERE rowid=?", (rowid,))
                    self.connection.commit()
                    self.load_table_data()
                    QtWidgets.QMessageBox.information(self, "✅ Sucesso", "Linha excluída com sucesso!")

    def delete_selected_table(self):
        table_name = self.table_select.currentText()
        if table_name:
            confirm = QtWidgets.QMessageBox.question(
                self, "⚠ Confirmação", f"Tem certeza que deseja excluir a tabela '{table_name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)

            if confirm == QtWidgets.QMessageBox.Yes:
                cursor = self.connection.cursor()
                cursor.execute(f"DROP TABLE {table_name}")
                self.connection.commit()
                self.load_tables()
                self.table_view.setRowCount(0)
                self.table_view.setColumnCount(0)
                QtWidgets.QMessageBox.information(self, "✅ Sucesso", f"Tabela '{table_name}' excluída com sucesso!")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = DBEditor()
    window.show()
    sys.exit(app.exec_())
