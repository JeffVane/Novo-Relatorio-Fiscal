from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,QFileDialog,QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import pandas as pd
from fpdf import FPDF
from db import connect_db
import calendar

class ResultadoMensalTab(QWidget):
    def __init__(self, user_info):
        super().__init__()
        self.user_info = user_info
        self.username = user_info.get("username", "").replace(" ", "_").lower()
        self.is_admin = user_info.get("is_admin", False)
        self.init_ui()
        self.expanded_groups = {}



    def init_ui(self):
        layout = QVBoxLayout(self)

        self.title = QLabel("📈Resultado Mensal - CFC")
        self.title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(self.title)

        self.table = QTableWidget()
        self.table.setColumnCount(14)  # 12 meses + Procedimento + Total
        self.table.setHorizontalHeaderLabels(["Procedimento"] +['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'] + ["Meta+%CRCDF", "Total Realizado", "% Cumprido"])

        # 🔹 Ajuste de tamanho das colunas
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Procedimento
        for col in range(1, 13):  # Jan a Dez
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(13, QHeaderView.ResizeToContents)  # Total

        # 🔹 Ocupa todo o espaço disponível
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.load_resultado_mensal()
        self.table.cellClicked.connect(self.on_cell_clicked)

    from PyQt5.QtGui import QColor

    def load_resultado_mensal(self):
        try:
            conn = connect_db()
            cursor = conn.cursor()

            # Metas CFC
            cursor.execute("SELECT name, COALESCE(meta_cfc, 0) FROM procedures WHERE LOWER(name) != 'cancelado'")
            procedures_data = cursor.fetchall()
            procedimentos = {name.upper(): int(meta) for name, meta in procedures_data}

            # Pesos
            cursor.execute("""
                SELECT p.name, COALESCE(w.weight, 1)
                FROM procedures p
                LEFT JOIN weights w ON p.id = w.procedure_id
            """)
            pesos = {row[0].strip().upper(): int(row[1]) for row in cursor.fetchall()}

            # Grupos
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

            # Tabelas de fiscais
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            all_tables = [t[0] for t in cursor.fetchall()]
            self.fiscal_tables = [t for t in all_tables if t.startswith("procedimentos_")]

            # Inicialização
            contagem = {proc: [0] * 12 for proc in procedimentos}
            totais_mensais = [0] * 12
            total_meta_geral = 0
            total_realizado_geral = 0

            # Acúmulo ponderado
            for table in self.fiscal_tables:
                for proc in procedimentos:
                    cursor.execute(f"""
                        SELECT quantidade, data_conclusao FROM {table}
                        WHERE UPPER(procedimento) = ? AND data_conclusao IS NOT NULL
                    """, (proc,))
                    for quantidade, data in cursor.fetchall():
                        try:
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
                total_meta_geral += meta_total
                total_realizado_geral += total_realizado

            # Procedimentos isolados
            agrupados = {p for membros in grupos.values() for p in membros}
            for proc, meta in procedimentos.items():
                if proc not in agrupados:
                    soma_mensal = contagem[proc]
                    total_realizado = sum(soma_mensal)
                    perc = round((total_realizado / meta) * 100, 2) if meta > 0 else 0
                    perc = min(perc, 100)
                    linhas_resultado.append((proc, soma_mensal, meta, total_realizado, perc))
                    total_meta_geral += meta
                    total_realizado_geral += total_realizado

            # Exibição
            self.table.setColumnCount(16)
            self.table.setHorizontalHeaderLabels(
                ["Procedimento"] +['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'] + ["Meta+%CRCDF", "Total Realizado", "% Cumprido"]
            )
            self.table.setRowCount(len(linhas_resultado) + 1)

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

            for row_idx, (nome, meses, meta, total, perc) in enumerate(linhas_resultado):
                item_nome = QTableWidgetItem(nome)
                item_nome.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(row_idx, 0, item_nome)

                for i, val in enumerate(meses):
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

            # Linha TOTAL
            total_item = QTableWidgetItem("TOTAL")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setFont(self._bold_font())
            total_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(len(linhas_resultado), 0, total_item)

            for i, val in enumerate(totais_mensais):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                item.setFont(self._bold_font())
                self.table.setItem(len(linhas_resultado), i + 1, item)

            meta_total_item = QTableWidgetItem(str(total_meta_geral))
            meta_total_item.setTextAlignment(Qt.AlignCenter)
            meta_total_item.setFont(self._bold_font())
            self.table.setItem(len(linhas_resultado), 13, meta_total_item)

            total_final_item = QTableWidgetItem(str(total_realizado_geral))
            total_final_item.setTextAlignment(Qt.AlignCenter)
            total_final_item.setFont(self._bold_font())
            self.table.setItem(len(linhas_resultado), 14, total_final_item)

            perc_geral = round((total_realizado_geral / total_meta_geral) * 100, 2) if total_meta_geral > 0 else 0
            perc_geral = min(perc_geral, 100)

            perc_total_item = QTableWidgetItem(f"{perc_geral}%")
            perc_total_item.setTextAlignment(Qt.AlignCenter)
            perc_total_item.setFont(self._bold_font())
            if perc_geral >= 100:
                perc_total_item.setForeground(QColor("green"))
            elif perc_geral >= 50:
                perc_total_item.setForeground(QColor("blue"))
            else:
                perc_total_item.setForeground(QColor("red"))
            self.table.setItem(len(linhas_resultado), 15, perc_total_item)

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            conn.close()

        except Exception as e:
            print(f"[ERRO] Falha ao carregar resultado mensal com grupos: {e}")

    def _bold_font(self):
        font = self.font()
        font.setBold(True)
        return font

    def toggle_expand_group(self, group_name, row_index):
        """
        Expande ou recolhe os procedimentos de um grupo específico na tabela Resultado Mensal (CFC),
        ponderando os resultados pelo peso de cada procedimento.
        """
        conn = connect_db()
        cursor = conn.cursor()

        if not hasattr(self, "expanded_groups"):
            self.expanded_groups = {}

        # 🔹 Carregar pesos
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
            cursor.execute("SELECT COALESCE(meta_cfc, 0) FROM procedures WHERE name = ?", (proc,))
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
                "Salvar Resultado Mensal - CFC",
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
                        self.cell(0, 10, "Relatório - Resultado Mensal CFC", ln=True, align='C')
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



