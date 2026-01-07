from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QMessageBox, QFileDialog, QApplication, QShortcut, QAbstractItemView,QHBoxLayout,QComboBox
)
from PyQt5.QtGui import QColor, QKeySequence, QFont
from PyQt5.QtCore import Qt

from db import connect_db
import pandas as pd
import calendar

class ResultadoMensalCRCDFTab(QWidget):
    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.username = user_info.get("username", "").replace(" ", "_").lower()
        self.is_admin = user_info.get("is_admin", False)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.title = QLabel("📈Resultado Mensal - CRCDF")
        self.title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(self.title)

        # 🔹 ADICIONE ISSO AQUI - Seletor de Ano
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Ano:"))
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2026", "2025", "2024", "2023"])
        self.year_combo.setCurrentText("2026")
        self.year_combo.currentTextChanged.connect(self.load_resultado_mensal)
        year_layout.addWidget(self.year_combo)
        year_layout.addStretch()
        layout.addLayout(year_layout)
        # 🔹 FIM DA ADIÇÃO

        self.table = QTableWidget()
        self.table.setColumnCount(16)
        self.table.setHorizontalHeaderLabels(
            ["Procedimento"] +['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'] + ["Meta+%CRCDF", "Total Realizado", "% Cumprido"]
        )

        # Estilo do cabeçalho
        self.table.setStyleSheet("""
                    QHeaderView::section {
                        background-color: #002060;
                        color: white;
                        font-weight: bold;
                        padding: 3px;
                        border: 1px solid white;
                        text-align: center;
                    }
                """)

        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for col in range(1, 13):
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(13, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(14, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(15, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)
        self.table.cellClicked.connect(self.on_cell_clicked)

        # --- habilita seleção/foco e atalho Ctrl+C -----------------
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.StrongFocus)
        QShortcut(QKeySequence("Ctrl+C"), self.table, self.copiar_tabela_para_clipboard)
        # -----------------------------------------------------------

        self.setLayout(layout)
        self.load_resultado_mensal()

    def load_resultado_mensal(self):
        try:
            conn = connect_db()
            cursor = conn.cursor()
            # 🔹 ADICIONE ISSO - Pega o ano selecionado
            ano_selecionado = self.year_combo.currentText()

            # Carrega metas CRCDF
            cursor.execute("SELECT name, COALESCE(meta_crcdf, 0) FROM procedures WHERE LOWER(name) != 'cancelado'")
            procedures_data = cursor.fetchall()
            procedimentos = {name.upper(): int(meta) for name, meta in procedures_data}

            # Carrega pesos
            cursor.execute('''
                SELECT p.name, COALESCE(w.weight, 1)
                FROM procedures p
                LEFT JOIN weights w ON p.id = w.procedure_id
            ''')
            pesos = {row[0].strip().upper(): int(row[1]) for row in cursor.fetchall()}

            # Carrega grupos
            cursor.execute("""
                SELECT gp.nome_grupo, p.name
                FROM grupos_procedimentos gp
                JOIN grupo_itens gi ON gp.id = gi.grupo_id
                JOIN procedures p ON gi.procedimento_id = p.id
            """)
            grupos_raw = cursor.fetchall()
            grupos = {}
            for grupo, proc in grupos_raw:
                grupos.setdefault(grupo.upper(), []).append(proc.upper())

            # Tabelas dos fiscais
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [t[0] for t in cursor.fetchall()]
            self.fiscal_tables = [t for t in all_tables if t.startswith("procedimentos_")]

            # Inicializa contadores
            contagem = {proc: [0] * 12 for proc in procedimentos}
            totais_mensais = [0] * 12

            total_metas = 0

            # Preenche contagem com quantidade * peso
            for table in self.fiscal_tables:
                for proc in procedimentos:
                    cursor.execute(f"""
                        SELECT quantidade, data_conclusao FROM {table}
                        WHERE UPPER(procedimento) = ? AND data_conclusao IS NOT NULL
                    """, (proc,))
                    for quantidade, data in cursor.fetchall():
                        try:

                            # 🔹 ADICIONE ESTE FILTRO
                            if not data.endswith(ano_selecionado):
                                continue
                            mes = int(data.split("-")[1]) - 1
                            qnt = int(quantidade)
                            peso = pesos.get(proc, 1)
                            ponderado = qnt * peso
                            contagem[proc][mes] += ponderado
                            totais_mensais[mes] += ponderado
                        except Exception as e:
                            print(f"[AVISO] Erro ao interpretar data '{data}': {e}")

            linhas_resultado = []

            # Grupos
            for grupo_nome, membros in grupos.items():
                soma_mensal = [sum(contagem.get(proc, [0] * 12)[i] for proc in membros) for i in range(12)]
                meta_total = sum(procedimentos.get(proc, 0) for proc in membros)
                total_realizado = sum(soma_mensal)
                perc = round((total_realizado / meta_total) * 100, 2) if meta_total > 0 else 0
                perc = min(perc, 100)
                linhas_resultado.append((f"🔽GRUPO: {grupo_nome}", soma_mensal, meta_total, total_realizado, perc))
                total_metas += meta_total

            # Procedimentos isolados
            agrupados = {p for membros in grupos.values() for p in membros}
            for proc, meta in procedimentos.items():
                if proc not in agrupados:
                    soma_mensal = contagem[proc]
                    total_realizado = sum(soma_mensal)
                    perc = round((total_realizado / meta) * 100, 2) if meta > 0 else 0
                    perc = min(perc, 100)
                    linhas_resultado.append((proc, soma_mensal, meta, total_realizado, perc))
                    total_metas += meta

            self.table.setRowCount(len(linhas_resultado) + 1)

            total_geral = 0
            totais_por_mes = [0] * 12

            for row_idx, (nome, meses, meta, total, perc) in enumerate(linhas_resultado):
                item_nome = QTableWidgetItem(nome)
                item_nome.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(row_idx, 0, item_nome)

                for i, val in enumerate(meses):
                    totais_por_mes[i] += val
                    item = QTableWidgetItem(str(val))
                    item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.table.setItem(row_idx, i + 1, item)

                meta_item = QTableWidgetItem(str(meta))
                meta_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 13, meta_item)

                total_item = QTableWidgetItem(str(total))
                total_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_idx, 14, total_item)

                perc_item = QTableWidgetItem(f"{perc}%")
                perc_item.setTextAlignment(Qt.AlignCenter)
                if perc >= 100:
                    perc_item.setForeground(QColor("green"))
                elif perc >= 50:
                    perc_item.setForeground(QColor("blue"))
                else:
                    perc_item.setForeground(QColor("red"))
                self.table.setItem(row_idx, 15, perc_item)

                total_geral += total

            # Linha TOTAL
            total_item = self._bold_item("TOTAL", center=True)
            total_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(len(linhas_resultado), 0, total_item)

            for i, val in enumerate(totais_por_mes):
                item = self._bold_item(str(val), center=True)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(len(linhas_resultado), i + 1, item)

            meta_total_item = self._bold_item(str(total_metas), center=True)
            meta_total_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(len(linhas_resultado), 13, meta_total_item)

            total_final_item = self._bold_item(str(total_geral), center=True)
            total_final_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(len(linhas_resultado), 14, total_final_item)

            perc_total = round((total_geral / total_metas) * 100, 2) if total_metas > 0 else 0
            perc_total = min(perc_total, 100)

            perc_total_item = self._bold_item(f"{perc_total}%", center=True)
            perc_total_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            if perc_total >= 100:
                perc_total_item.setForeground(QColor("green"))
            elif perc_total >= 50:
                perc_total_item.setForeground(QColor("blue"))
            else:
                perc_total_item.setForeground(QColor("red"))
            self.table.setItem(len(linhas_resultado), 15, perc_total_item)

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            conn.close()

        except Exception as e:
            print(f"[ERRO] Falha ao carregar resultado mensal CRCDF: {e}")

    def copiar_tabela_para_clipboard(self):
        """Copia seleção da tabela para o clipboard em formato tabulado (Excel-friendly)."""
        ranges = self.table.selectedRanges()
        if not ranges:
            return

        linhas = []
        for sel in ranges:
            for row in range(sel.topRow(), sel.bottomRow() + 1):
                linha_texto = []
                for col in range(sel.leftColumn(), sel.rightColumn() + 1):
                    item = self.table.item(row, col)
                    linha_texto.append(item.text() if item else "")
                linhas.append("\t".join(linha_texto))

        QApplication.clipboard().setText("\n".join(linhas).strip())

    def toggle_expand_group(self, group_name, row_index):
        from PyQt5.QtGui import QColor

        conn = connect_db()
        cursor = conn.cursor()

        if not hasattr(self, "expanded_groups"):
            # 🔹 ADICIONE ISSO logo após: if not hasattr(self, "expanded_groups"):
            ano_selecionado = self.year_combo.currentText()
            self.expanded_groups = {}

        # Carrega pesos dos procedimentos
        cursor.execute('''
            SELECT p.name, COALESCE(w.weight, 1)
            FROM procedures p
            LEFT JOIN weights w ON p.id = w.procedure_id
        ''')
        pesos = {row[0].strip().upper(): int(row[1]) for row in cursor.fetchall()}

        if group_name in self.expanded_groups:
            # 🔼 Recolher grupo
            expanded_rows = self.expanded_groups[group_name]
            for _ in expanded_rows:
                self.table.removeRow(row_index + 1)
            del self.expanded_groups[group_name]
            self.table.item(row_index, 0).setText(f"🔽GRUPO: {group_name}")
            conn.close()
            return

        # 🔽 Expandir grupo
        cursor.execute("""
            SELECT p.name
            FROM grupos_procedimentos gp
            JOIN grupo_itens gi ON gp.id = gi.grupo_id
            JOIN procedures p ON gi.procedimento_id = p.id
            WHERE UPPER(gp.nome_grupo) = ?
        """, (group_name.upper(),))
        procedimentos = [row[0] for row in cursor.fetchall()]

        expanded_rows = []

        for idx, proc in enumerate(procedimentos):
            proc_upper = proc.strip().upper()
            cursor.execute("SELECT COALESCE(meta_crcdf, 0) FROM procedures WHERE name = ?", (proc,))
            meta = cursor.fetchone()
            meta = meta[0] if meta else 0

            mensal = [0] * 12
            total = 0
            for table in self.fiscal_tables:
                cursor.execute(f"""
                    SELECT quantidade, data_conclusao FROM {table}
                    WHERE procedimento = ? AND data_conclusao IS NOT NULL
                """, (proc,))
                for qnt, data in cursor.fetchall():
                    try:
                        # 🔹 ADICIONE ESTE FILTRO
                        if not data.endswith(ano_selecionado):
                            continue
                        mes = int(data.split("-")[1]) - 1
                        qnt = int(qnt)
                        peso = pesos.get(proc_upper, 1)
                        ponderado = qnt * peso
                        mensal[mes] += ponderado
                        total += ponderado
                    except:
                        continue

            # Inserir nova linha expandida
            insert_pos = row_index + 1 + idx
            self.table.insertRow(insert_pos)
            item_nome = QTableWidgetItem(f"↳ {proc}")
            item_nome.setForeground(QColor("gray"))
            item_nome.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(insert_pos, 0, item_nome)

            for mes in range(12):
                mes_item = QTableWidgetItem(str(mensal[mes]))
                mes_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(insert_pos, mes + 1, mes_item)

            for col in range(13, 16):
                dash_item = QTableWidgetItem("-")
                dash_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(insert_pos, col, dash_item)

            expanded_rows.append(insert_pos)

        self.expanded_groups[group_name] = expanded_rows
        self.table.item(row_index, 0).setText(f"🔼 GRUPO: {group_name}")
        conn.close()

    def on_cell_clicked(self, row, column):
        item = self.table.item(row, 0)
        if not item:
            return

        texto = item.text().strip()
        if texto.startswith("🔽GRUPO:") or texto.startswith("🔽 GRUPO:") or texto.startswith("🔼 GRUPO:"):
            group_name = texto.replace("🔽", "").replace("🔼", "").strip().replace("GRUPO:", "").strip()
            self.toggle_expand_group(group_name, row)

    def _bold_item(self, text, center=False):
        item = QTableWidgetItem(text)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        if center:
            item.setTextAlignment(Qt.AlignCenter)
        return item

    def exportar_pdf_excel(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from fpdf import FPDF
        import pandas as pd
        import re

        def sanitize_text(texto):
            texto = re.sub(r"[^\x00-\x7F]+", "", texto)  # Remove emojis/símbolos
            try:
                return texto.encode("latin-1").decode("latin-1")
            except:
                return texto.encode("latin-1", errors="replace").decode("latin-1")

        try:
            # 🔹 Expande todos os grupos se ainda estiverem recolhidos
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.text().startswith("GRUPO:"):
                    nome_grupo = item.text().replace("GRUPO:", "").strip()
                    self.toggle_expand_group(nome_grupo, row)

            caminho, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Resultado Mensal - CRCDF",
                "",
                "Arquivo Excel (*.xlsx);;Arquivo PDF (*.pdf)"
            )
            if not caminho:
                return

            # 🔹 Coleta os dados
            dados = []
            for row in range(self.table.rowCount()):
                linha = []
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    texto = item.text() if item else ""
                    linha.append(sanitize_text(texto))
                dados.append(linha)

            colunas = [sanitize_text(self.table.horizontalHeaderItem(i).text()) for i in
                       range(self.table.columnCount())]

            if caminho.endswith(".xlsx"):
                df = pd.DataFrame(dados, columns=colunas)
                df.to_excel(caminho, index=False)
                QMessageBox.information(self, "Sucesso", "Exportação para Excel concluída!")

            elif caminho.endswith(".pdf"):
                class PDF(FPDF):
                    def __init__(self):
                        super().__init__(orientation='L', unit='mm', format='A4')
                        self.set_auto_page_break(auto=True, margin=10)
                        self.add_page()
                        self.set_font("Helvetica", size=7)

                    def header(self):
                        self.set_font("Helvetica", style='B', size=10)
                        self.cell(0, 10, "Relatório - Resultado Mensal CRCDF", ln=True, align='C')
                        self.ln(2)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica", style='I', size=8)
                        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

                pdf = PDF()

                # 🔹 Cálculo da largura proporcional
                largura_total = 277
                pdf.set_font("Helvetica", size=7)
                larguras = []
                for i, col in enumerate(colunas):
                    largura = pdf.get_string_width(col) + 4
                    for linha in dados:
                        if i < len(linha):
                            largura = max(largura, pdf.get_string_width(linha[i]) + 4)
                    larguras.append(min(largura, 90))  # limite máximo
                fator = largura_total / sum(larguras)
                larguras = [w * fator for w in larguras]

                # 🔹 Cabeçalho
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Helvetica", style='B', size=7)
                for i, titulo in enumerate(colunas):
                    pdf.cell(larguras[i], 7, titulo, border=1, align="C", fill=True)
                pdf.ln()

                # 🔹 Dados com altura uniforme e sem espaçamento
                pdf.set_font("Helvetica", size=7)
                for linha in dados:
                    x = pdf.get_x()
                    y = pdf.get_y()

                    # Mede altura necessária da primeira célula (multi_cell oculta)
                    linhas_proced = pdf.multi_cell(larguras[0], 4, linha[0], border=0, align='L', split_only=True)
                    altura_linha = 4 * len(linhas_proced)

                    # Primeira célula com multi_cell real
                    pdf.set_xy(x, y)
                    pdf.multi_cell(larguras[0], 4, linha[0], border=1, align='L')
                    pdf.set_xy(x + larguras[0], y)

                    # Demais células com altura igual
                    for i in range(1, len(linha)):
                        pdf.cell(larguras[i], altura_linha, linha[i], border=1, align='C')

                    pdf.set_y(y + altura_linha)

                pdf.output(caminho)
                QMessageBox.information(self, "Sucesso", "Exportação para PDF concluída!")

            else:
                QMessageBox.warning(self, "Formato inválido", "Escolha um formato .xlsx ou .pdf")

        except Exception as e:
            import traceback
            erro = traceback.format_exc()
            QMessageBox.critical(self, "Erro", f"Falha ao exportar:\n{str(e)}\n\n{erro}")










