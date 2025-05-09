from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from db import connect_db
from datetime import datetime
from textwrap import wrap

class LogAcoesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.title = QLabel("📃 Histórico De Ações")
        self.title.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
        """)
        layout.addWidget(self.title)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Usuário", "Ação", "Detalhes", "Data/Hora"])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-size: 14px;
                selection-background-color: #d0ebff;
            }
            QHeaderView::section {
                background-color: #0e3b63;
                color: white;
                font-weight: bold;
                padding: 6px;
                border: 1px solid #dee2e6;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(60)  # espaço para 3 linhas

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.carregar_logs()

    def carregar_logs(self):
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT usuario, acao, detalhes, data_hora FROM logs ORDER BY data_hora DESC")
            logs = cursor.fetchall()
            conn.close()

            self.table.setRowCount(len(logs))

            for row_idx, (usuario, acao, detalhes, data_hora) in enumerate(logs):
                usuario_item = QTableWidgetItem(usuario)
                acao_item = QTableWidgetItem(acao)

                # Aplica wrap com limite de até 3 linhas
                wrapped_lines = wrap(detalhes, width=60)[:3]
                texto_limitado = "\n".join(wrapped_lines)
                detalhes_item = QTableWidgetItem(texto_limitado)
                detalhes_item.setToolTip(texto_limitado)

                try:
                    dt_formatado = datetime.strptime(data_hora, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    dt_formatado = data_hora
                data_hora_item = QTableWidgetItem(dt_formatado)

                for item in [usuario_item, acao_item, detalhes_item, data_hora_item]:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item.setFont(QFont("Segoe UI", 11))

                self.table.setItem(row_idx, 0, usuario_item)
                self.table.setItem(row_idx, 1, acao_item)
                self.table.setItem(row_idx, 2, detalhes_item)
                self.table.setItem(row_idx, 3, data_hora_item)

            self.table.resizeColumnsToContents()
            self.table.horizontalHeader().setStretchLastSection(False)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.table.resizeRowsToContents()

        except Exception as e:
            print(f"[ERRO] Falha ao carregar logs: {e}")
