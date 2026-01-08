# -------------------- IMPORTAÇÕES --------------------
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QPushButton, QDialog, QLineEdit, QListWidget, QDialogButtonBox,
    QListWidgetItem, QMessageBox, QMenu, QApplication, QAbstractItemView,
    QShortcut,QHBoxLayout,QComboBox
)
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtCore import Qt, pyqtSignal
# -----------------------------------------------------
from db import connect_db
from unidecode import unidecode
import re

from db import registrar_log
import re
from PyQt5.QtCore import pyqtSignal

class ResultadosFiscalTab(QWidget):
    metas_atualizadas = pyqtSignal()
    def __init__(self, user_info, parent=None):
        super().__init__(parent)
        self.user_info = user_info
        self.fiscais = self.get_fiscais()
        self.grupos = {}
        self.grupo_linhas = {}
        self.bloquear_sinal = False
        self.initUI()


    def initUI(self):
        layout = QVBoxLayout()

        self.title_label = QLabel("📊Resultados do Fiscal")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(self.title_label)
        # 🔹 ADICIONE - Seletor de Ano
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("Ano:"))
        self.year_combo = QComboBox()
        self.year_combo.addItems(["2026", "2025", "2024", "2023"])
        self.year_combo.setCurrentText("2026")
        self.year_combo.currentTextChanged.connect(self.load_data)
        year_layout.addWidget(self.year_combo)
        year_layout.addStretch()
        layout.addLayout(year_layout)

        self.table = GrupoTableWidget(toggle_callback=self.toggle_expand)

        # ---- habilita seleção/foco/atalhos para copiar ----
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if self.user_info.get("is_admin", False):
            # permite editar (mas só as células que você marcar como Editable)
            self.table.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked |
                QAbstractItemView.EditTrigger.SelectedClicked |
                QAbstractItemView.EditTrigger.EditKeyPressed
            )
        else:
            self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # recebe foco de teclado
        QShortcut(QKeySequence("Ctrl+C"), self.table, self.copiar_tabela_para_clipboard)
        # ---------------------------------------------------

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.custom_context_menu)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        if self.user_info.get("is_admin", False):
            self.table.cellChanged.connect(self.verificar_alteracao_meta)

        layout.addWidget(self.table)
        self.setLayout(layout)
        self.load_data()

    def abrir_agrupador(self):
        dialog = AgrupadorDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_data()
    def verifica_toggle_expand(self, row, column):
        item = self.table.item(row, 0)  # Sempre verifica a primeira coluna
        if item and (item.text().startswith("🔽") or item.text().startswith("🔼")):
            self.toggle_expand(row)


    def get_fiscais(self):
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE is_admin = 0 AND is_fiscal = 1")
            fiscais = [row[0].upper() for row in cursor.fetchall()]
            conn.close()
            return fiscais
        except Exception as e:
            print(f"[ERROR] Erro ao buscar fiscais: {e}")
            return []

    def custom_context_menu(self, position):
        if not self.user_info.get("is_admin", False):
            return  # Não mostra o menu para usuários não-admin

        row = self.table.rowAt(position.y())
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return

        nome_grupo = re.sub(r"^[🔽🔼]\s*", "", item.text().strip())
        menu = QMenu(self)

        if nome_grupo in self.grupos:
            toggle_action = menu.addAction("Expandir Grupo" if nome_grupo not in self.grupo_linhas else "Recolher Grupo")
            action_agrupador = menu.addAction("Agrupar Procedimentos")
            action_desfazer = menu.addAction("Desfazer Grupo")

            action = menu.exec_(self.table.viewport().mapToGlobal(position))

            if action == toggle_action:
                self.toggle_expand(row)
            elif action == action_agrupador:
                self.abrir_agrupador()
            elif action == action_desfazer:
                self.desfazer_grupo(nome_grupo)
        else:
            action_agrupador = menu.addAction("Agrupar Procedimentos")
            action = menu.exec_(self.table.viewport().mapToGlobal(position))
            if action == action_agrupador:
                self.abrir_agrupador()



    def desfazer_grupo(self, nome_grupo):
        confirmar = QMessageBox.question(
            self,
            "Desfazer Grupo",
            f"Tem certeza que deseja desfazer o grupo '{nome_grupo}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmar != QMessageBox.Yes:
            return

        try:
            conn = connect_db()
            cursor = conn.cursor()
            # Obtém o ID do grupo
            cursor.execute("SELECT id FROM grupos_procedimentos WHERE nome_grupo = ?", (nome_grupo,))
            resultado = cursor.fetchone()
            if not resultado:
                QMessageBox.warning(self, "Aviso", "Grupo não encontrado no banco de dados.")
                return

            grupo_id = resultado[0]

            # Remove os vínculos com procedimentos
            cursor.execute("DELETE FROM grupo_itens WHERE grupo_id = ?", (grupo_id,))

            # Remove o grupo
            cursor.execute("DELETE FROM grupos_procedimentos WHERE id = ?", (grupo_id,))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Sucesso", f"Grupo '{nome_grupo}' desfeito com sucesso.")
            self.load_data()

        except Exception as e:
            print(f"[ERRO] Falha ao desfazer grupo: {e}")
            QMessageBox.critical(self, "Erro", f"Erro ao desfazer o grupo:\n{e}")

    def toggle_expand(self, row):
        self.bloquear_sinal = True
        item = self.table.item(row, 0)
        if not item:
            self.bloquear_sinal = False
            return

        # 🔹 ADICIONE logo no início
        ano_selecionado = self.year_combo.currentText()

        grupo_nome = re.sub(r"^[🔽🔼]\s*", "", item.text().strip())

        if self.grupo_linhas.get(grupo_nome):
            count = self.grupo_linhas.pop(grupo_nome)
            for _ in range(count):
                self.table.removeRow(row + 1)
            item.setText("🔽 " + grupo_nome)
        else:
            procedimentos = self.grupos.get(grupo_nome, [])
            self.grupo_linhas[grupo_nome] = len(procedimentos)

            conn = connect_db()
            cursor = conn.cursor()

            cursor.execute("SELECT procedure_id, weight FROM weights")
            pesos = {pid: peso for pid, peso in cursor.fetchall()}

            cursor.execute("SELECT id, name FROM procedures")
            id_map = {name.strip().upper(): pid for pid, name in cursor.fetchall()}

            col_realizado = self.table.columnCount() - 3
            col_cfc = self.table.columnCount() - 2
            col_crcdf = self.table.columnCount() - 1

            total_realizado_ponderado = 0

            for i, proc in enumerate(procedimentos):
                self.table.insertRow(row + i + 1)
                item_proc = QTableWidgetItem(f"   ↳ {proc}")
                item_proc.setFlags(Qt.ItemIsEnabled)
                item_proc.setForeground(Qt.gray)
                self.table.setItem(row + i + 1, 0, item_proc)

                for c in range(1, self.table.columnCount()):
                    col_header = self.table.horizontalHeaderItem(c).text()
                    item_cell = QTableWidgetItem()
                    item_cell.setTextAlignment(Qt.AlignCenter)

                    if col_header in ("Meta Anual", "Meta+%CRCDF", "A Realizar CFC", "A Realizar CRCDF"):
                        item_cell.setText("–")
                        item_cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)


                    elif col_header == "Realizado":
                        total_proc = 0
                        for fiscal in self.fiscais:
                            tabela = f"procedimentos_{fiscal.lower()}"
                            try:
                                cursor.execute(f"""
                                    SELECT quantidade, data_conclusao FROM '{tabela}'
                                    WHERE UPPER(TRIM(procedimento)) = ?
                                """, (proc.strip().upper(),))
                                resultado = cursor.fetchall()
                                for qnt, data in resultado:
                                    if qnt is None:
                                        continue
                                    if data and ano_selecionado in str(data):  # (dd-mm-aaaa)
                                        total_proc += int(qnt)

                            except Exception as e:
                                print(f"[ERRO SQL] {e}")
                        proc_id = id_map.get(proc.strip().upper())
                        peso = pesos.get(proc_id, 1)
                        realizado_pond = total_proc * peso

                        total_realizado_ponderado += realizado_pond
                        item_cell.setText(str(realizado_pond))
                        item_cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)



                    elif col_header in self.fiscais:

                        fiscal = col_header

                        tabela = f"procedimentos_{fiscal.lower()}"

                        total_proc = 0  # ✅ zera aqui (evita contaminar outros fiscais)

                        try:

                            cursor.execute(f"""

                                SELECT quantidade, data_conclusao FROM '{tabela}'

                                WHERE UPPER(TRIM(procedimento)) = ?

                            """, (proc.strip().upper(),))

                            resultado = cursor.fetchall()

                            for qnt, data in resultado:

                                if qnt is None:
                                    continue

                                if data and ano_selecionado in str(data):
                                    total_proc += int(qnt)  # ✅ soma só deste fiscal

                            item_cell.setText(str(total_proc))


                        except Exception as e:

                            print(f"[ERRO FISCAL] {e}")

                        item_cell.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)


                    else:
                        item_cell.setFlags(Qt.NoItemFlags)

                    self.table.setItem(row + i + 1, c, item_cell)

            conn.close()

            # Atualiza os totais do grupo (linha principal)
            try:
                meta_cfc_val = int(self.table.item(row, 1).text())
                meta_crcdf_val = int(self.table.item(row, 2).text())
            except:
                meta_cfc_val = meta_crcdf_val = 0

            # Realizado total
            item_realizado = QTableWidgetItem(str(total_realizado_ponderado))
            item_realizado.setTextAlignment(Qt.AlignCenter)
            item_realizado.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, col_realizado, item_realizado)

            # A Realizar CFC
            a_realizar_cfc = meta_cfc_val - total_realizado_ponderado
            if a_realizar_cfc < 0:
                texto = f"{total_realizado_ponderado} (Concluído {abs(a_realizar_cfc)} a mais)"
                item_cfc = QTableWidgetItem(texto)
                item_cfc.setForeground(QColor("#004080"))  # Azul escuro
            else:
                texto = str(a_realizar_cfc)
                item_cfc = QTableWidgetItem(texto)
                if a_realizar_cfc > 0:
                    item_cfc.setForeground(QColor("#ea3737"))  # Vermelho
                else:
                    item_cfc.setForeground(QColor("green"))  # Verde se exatamente 0

            item_cfc.setTextAlignment(Qt.AlignCenter)
            item_cfc.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, col_cfc, item_cfc)

            # A Realizar CRCDF
            a_realizar_crcdf = meta_crcdf_val - total_realizado_ponderado
            if a_realizar_crcdf < 0:
                texto = f"{total_realizado_ponderado} (Concluído {abs(a_realizar_crcdf)} a mais)"
                item_crcdf = QTableWidgetItem(texto)
                item_crcdf.setForeground(QColor("#004080"))
            else:
                texto = str(a_realizar_crcdf)
                item_crcdf = QTableWidgetItem(texto)
                if a_realizar_crcdf > 0:
                    item_crcdf.setForeground(QColor("#ea3737"))
                else:
                    item_crcdf.setForeground(QColor("green"))

            item_crcdf.setTextAlignment(Qt.AlignCenter)
            item_crcdf.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, col_crcdf, item_crcdf)

            # Atualiza o nome do grupo com o ícone de recolher
            item.setText("🔼 " + grupo_nome)
            self.table.setItem(row, 0, item)

        self.bloquear_sinal = False

    def verificar_alteracao_meta(self, row, column):
        if self.bloquear_sinal:
            return

        # só permite editar metas
        if column not in (1, 2):
            return

        try:
            ano_selecionado = int(self.year_combo.currentText())

            item_nome = self.table.item(row, 0)
            item_valor = self.table.item(row, column)

            if not item_nome or not item_valor:
                return

            nome_exibido = item_nome.text().strip()
            nome_proc = re.sub(r"^[🔽🔼]\s*", "", nome_exibido).strip()

            # ignora linha total
            if nome_proc.upper() == "TOTAL":
                return

            nova_meta_txt = item_valor.text().strip()
            if not nova_meta_txt.isdigit():
                QMessageBox.warning(self, "Valor inválido", "Digite um valor numérico inteiro.")
                self.table.blockSignals(True)
                self.load_data()
                self.table.blockSignals(False)
                return

            nova_meta_valor = int(nova_meta_txt)
            tipo_meta = "Meta Anual" if column == 1 else "Meta+%CRCDF"

            confirmacao = QMessageBox.question(
                self,
                "Confirmar alteração",
                f"Deseja realmente alterar a {tipo_meta} de '{nome_proc}' para {nova_meta_valor} no ano {ano_selecionado}?",
                QMessageBox.Yes | QMessageBox.No
            )

            if confirmacao != QMessageBox.Yes:
                self.table.blockSignals(True)
                self.load_data()
                self.table.blockSignals(False)
                return

            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")

            def upsert_meta(procedure_id: int, ano: int, meta_cfc=None, meta_crcdf=None):
                # Atualiza apenas a coluna que mudou, mantendo a outra
                if meta_cfc is not None:
                    cursor.execute("""
                        INSERT INTO metas_anuais (procedure_id, ano, meta_cfc)
                        VALUES (?, ?, ?)
                        ON CONFLICT(procedure_id, ano)
                        DO UPDATE SET meta_cfc = excluded.meta_cfc
                    """, (procedure_id, ano, meta_cfc))
                if meta_crcdf is not None:
                    cursor.execute("""
                        INSERT INTO metas_anuais (procedure_id, ano, meta_crcdf)
                        VALUES (?, ?, ?)
                        ON CONFLICT(procedure_id, ano)
                        DO UPDATE SET meta_crcdf = excluded.meta_crcdf
                    """, (procedure_id, ano, meta_crcdf))

            if nome_proc in self.grupos:
                procedimentos = self.grupos[nome_proc]
                qtd = len(procedimentos)
                if qtd == 0:
                    raise ValueError("Grupo sem procedimentos.")

                base = nova_meta_valor // qtd
                resto = nova_meta_valor % qtd

                for i, proc_name in enumerate(procedimentos):
                    meta_individual = base + (1 if i < resto else 0)

                    cursor.execute("SELECT id FROM procedures WHERE name = ?", (proc_name,))
                    r = cursor.fetchone()
                    if not r:
                        continue
                    proc_id = r[0]

                    if column == 1:
                        upsert_meta(proc_id, ano_selecionado, meta_cfc=meta_individual)
                    else:
                        upsert_meta(proc_id, ano_selecionado, meta_crcdf=meta_individual)

            else:
                cursor.execute("SELECT id FROM procedures WHERE name = ?", (nome_proc,))
                r = cursor.fetchone()
                if not r:
                    raise ValueError(f"Procedimento não encontrado: {nome_proc}")
                proc_id = r[0]

                if column == 1:
                    upsert_meta(proc_id, ano_selecionado, meta_cfc=nova_meta_valor)
                else:
                    upsert_meta(proc_id, ano_selecionado, meta_crcdf=nova_meta_valor)

            conn.commit()
            conn.close()

            self.table.blockSignals(True)
            self.load_data()
            self.table.blockSignals(False)
            self.metas_atualizadas.emit()

        except Exception as e:
            import traceback
            print("[ERRO AO ATUALIZAR META]", traceback.format_exc())
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro ao atualizar a meta:\n{e}")

    def load_data(self):
        self.bloquear_sinal = True
        try:
            self.grupo_linhas.clear()
            conn = connect_db()
            cursor = conn.cursor()
            # 🔹 Obtém o ano selecionado
            ano_selecionado = self.year_combo.currentText()

            # Procedimentos e metas
            cursor.execute("""
                SELECT 
                    p.id,
                    p.name,
                    COALESCE(ma.meta_cfc, p.meta_cfc, 0) AS meta_cfc,
                    COALESCE(ma.meta_crcdf, p.meta_crcdf, 0) AS meta_crcdf
                FROM procedures p
                LEFT JOIN metas_anuais ma
                    ON ma.procedure_id = p.id
                    AND ma.ano = ?
                WHERE p.name != 'CANCELADO'
            """, (int(ano_selecionado),))

            procedimentos_raw = cursor.fetchall()
            procedimento_ids = {row[1].strip().upper(): row[0] for row in procedimentos_raw}
            metas_cfc = {row[1].strip().upper(): row[2] for row in procedimentos_raw}
            metas_crcdf = {row[1].strip().upper(): row[3] for row in procedimentos_raw}

            # Pesos
            cursor.execute("SELECT procedure_id, weight FROM weights")
            pesos = {proc_id: weight for proc_id, weight in cursor.fetchall()}

            # Grupos
            cursor.execute('''
                SELECT gp.nome_grupo, gi.grupo_id, gi.procedimento_id
                FROM grupos_procedimentos gp
                JOIN grupo_itens gi ON gp.id = gi.grupo_id
            ''')
            grupo_procedimentos = {}
            for nome_grupo, grupo_id, procedimento_id in cursor.fetchall():
                nome_grupo = nome_grupo.strip()
                grupo_procedimentos.setdefault(nome_grupo, []).append(procedimento_id)

            nomes_procedimentos = {row[0]: row[1].strip().upper() for row in procedimentos_raw}
            grupos = {
                nome_grupo: [nomes_procedimentos[pid] for pid in ids if pid in nomes_procedimentos]
                for nome_grupo, ids in grupo_procedimentos.items()
            }
            self.grupos = grupos

            procedimentos_agrupados = set(proc for lista in grupos.values() for proc in lista)
            procedimentos_individuais = [row[1].strip().upper() for row in procedimentos_raw if
                                         row[1].strip().upper() not in procedimentos_agrupados]
            linhas = list(grupos.keys()) + procedimentos_individuais

            # Cabeçalhos
            is_admin = self.user_info.get("is_admin", False)
            nome_fiscal_logado = self.user_info.get("username", "").upper()
            col_fiscais = self.fiscais if is_admin else [nome_fiscal_logado]

            headers = ["Procedimento", "Meta Anual", "Meta+%CRCDF"] + col_fiscais + ["Realizado", "A Realizar CFC",
                                                                                     "A Realizar CRCDF"]
            self.table.setColumnCount(len(headers))
            self.table.setRowCount(len(linhas))
            self.table.setHorizontalHeaderLabels(headers)

            def tabela_existe(nome_tabela):
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (nome_tabela,))
                return cursor.fetchone() is not None

            for row, nome in enumerate(linhas):
                is_grupo = nome in grupos
                nome_exibido = f"🔽 {nome}" if is_grupo else nome
                item_nome = QTableWidgetItem(nome_exibido)
                item_nome.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                if is_grupo:
                    item_nome.setForeground(Qt.darkBlue)
                    item_nome.setFont(QFont("Arial", weight=QFont.Bold))

                self.table.setItem(row, 0, item_nome)

                procedimentos = grupos[nome] if is_grupo else [nome]
                meta_cfc = sum(metas_cfc.get(p.upper(), 0) for p in procedimentos)
                meta_crcdf = sum(metas_crcdf.get(p.upper(), 0) for p in procedimentos)

                # Meta CFC - 🔹 CORRIGIDO: Permite edição para admin
                item_cfc = QTableWidgetItem(str(meta_cfc))
                item_cfc.setTextAlignment(Qt.AlignCenter)
                if is_admin:
                    item_cfc.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                else:
                    item_cfc.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, 1, item_cfc)

                # Meta CRCDF - 🔹 CORRIGIDO: Permite edição para admin
                item_crcdf = QTableWidgetItem(str(meta_crcdf))
                item_crcdf.setTextAlignment(Qt.AlignCenter)
                if is_admin:
                    item_crcdf.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                else:
                    item_crcdf.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, 2, item_crcdf)

                # Resultados por fiscal
                totais_fiscais = {}
                for i, fiscal in enumerate(col_fiscais):
                    total_fiscal = 0
                    tabela_nome = f"procedimentos_{fiscal.lower()}"
                    if tabela_existe(tabela_nome):
                        for proc in procedimentos:
                            # 🔹 CORRIGIDO: Agora busca também a data_conclusao para filtrar por ano
                            cursor.execute(f"""
                                SELECT quantidade, data_conclusao FROM {tabela_nome}
                                WHERE UPPER(TRIM(procedimento)) = ?
                            """, (proc.upper(),))
                            resultado = cursor.fetchall()
                            peso = pesos.get(procedimento_ids.get(proc.upper(), -1), 1)

                            # 🔹 Filtra por ano selecionado
                            for r in resultado:
                                if r[0] is not None and len(r) > 1:
                                    data_conclusao = r[1]
                                    # Verifica se a data termina com o ano selecionado (formato dd-mm-yyyy)
                                    if ano_selecionado in str(data_conclusao):
                                        total_fiscal += r[0] * peso

                    totais_fiscais[fiscal] = total_fiscal

                    item_fiscal = QTableWidgetItem(str(total_fiscal))
                    item_fiscal.setTextAlignment(Qt.AlignCenter)
                    item_fiscal.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.table.setItem(row, 3 + i, item_fiscal)

                # Total Realizado
                total_realizado = 0
                if is_grupo:
                    for proc in procedimentos:
                        total_proc = 0
                        for fiscal in self.fiscais:
                            tabela = f"procedimentos_{fiscal.lower()}"
                            if not tabela_existe(tabela):
                                continue
                            try:
                                # 🔹 CORRIGIDO: Busca data_conclusao
                                cursor.execute(f"""
                                    SELECT quantidade, data_conclusao FROM '{tabela}'
                                    WHERE UPPER(TRIM(procedimento)) = ?
                                """, (proc.strip().upper(),))
                                resultado = cursor.fetchall()

                                # 🔹 Filtra por ano
                                for r in resultado:
                                    if r[0] is not None and len(r) > 1 and ano_selecionado in str(r[1]):
                                        total_proc += r[0]
                            except Exception as e:
                                print(f"[ERRO SQL] {e}")

                        proc_id = procedimento_ids.get(proc.strip().upper())
                        peso = pesos.get(proc_id, 1)
                        total_realizado += total_proc * peso
                else:
                    for fiscal in self.fiscais:
                        tabela = f"procedimentos_{fiscal.lower()}"
                        if not tabela_existe(tabela):
                            continue

                        try:
                            for proc in procedimentos:
                                # 🔹 CORRIGIDO: Busca data_conclusao
                                cursor.execute(f"""
                                    SELECT quantidade, data_conclusao FROM '{tabela}'
                                    WHERE UPPER(TRIM(procedimento)) = ?
                                """, (proc.strip().upper(),))
                                resultado = cursor.fetchall()
                                proc_id = procedimento_ids.get(proc.strip().upper())
                                peso = pesos.get(proc_id, 1)

                                # 🔹 Filtra por ano
                                for q in resultado:
                                    if q[0] is not None and len(q) > 1 and ano_selecionado in str(q[1]):
                                        total_realizado += q[0] * peso
                        except Exception as e:
                            print(f"[ERRO SQL - procedimento '{proc}'] na tabela '{tabela}': {e}")

                item_realizado = QTableWidgetItem(str(total_realizado))
                item_realizado.setTextAlignment(Qt.AlignCenter)
                item_realizado.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, len(headers) - 3, item_realizado)

                # A Realizar CFC
                a_realizar_cfc = meta_cfc - total_realizado
                if a_realizar_cfc < 0:
                    texto = f"{total_realizado} (Concluído {abs(a_realizar_cfc)} a mais)"
                    item_cfc_ar = QTableWidgetItem(texto)
                    item_cfc_ar.setForeground(QColor("#004080"))
                else:
                    texto = str(a_realizar_cfc)
                    item_cfc_ar = QTableWidgetItem(texto)
                    if a_realizar_cfc > 0:
                        item_cfc_ar.setForeground(QColor("#ea3737"))
                    else:
                        item_cfc_ar.setForeground(QColor("green"))

                item_cfc_ar.setTextAlignment(Qt.AlignCenter)
                item_cfc_ar.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, len(headers) - 2, item_cfc_ar)

                # A Realizar CRCDF
                a_realizar_crcdf = meta_crcdf - total_realizado
                if a_realizar_crcdf < 0:
                    texto = f"{total_realizado} (Concluído {abs(a_realizar_crcdf)} a mais)"
                    item_crcdf_ar = QTableWidgetItem(texto)
                    item_crcdf_ar.setForeground(QColor("#004080"))
                else:
                    texto = str(a_realizar_crcdf)
                    item_crcdf_ar = QTableWidgetItem(texto)
                    if a_realizar_crcdf > 0:
                        item_crcdf_ar.setForeground(QColor("#ea3737"))
                    else:
                        item_crcdf_ar.setForeground(QColor("green"))

                item_crcdf_ar.setTextAlignment(Qt.AlignCenter)
                item_crcdf_ar.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(row, len(headers) - 1, item_crcdf_ar)

            # Adicionando a linha de totais
            total_row = self.table.rowCount()
            self.table.insertRow(total_row)

            item_total = QTableWidgetItem("TOTAL")
            item_total.setFont(QFont("Arial", weight=QFont.Bold, pointSize=10))
            item_total.setTextAlignment(Qt.AlignCenter)
            item_total.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(total_row, 0, item_total)

            for col in range(1, self.table.columnCount()):
                total = 0.0
                for row in range(self.table.rowCount() - 1):  # Exclui linha TOTAL
                    item = self.table.item(row, col)
                    if item:
                        try:
                            # Remove texto extra como "(Concluído X a mais)"
                            texto = item.text().split("(")[0].strip()
                            total += float(texto.replace(",", "."))
                        except ValueError:
                            pass

                item_total_col = QTableWidgetItem(str(int(total) if total.is_integer() else f"{total:.1f}"))
                item_total_col.setTextAlignment(Qt.AlignCenter)
                item_total_col.setFont(QFont("Arial", weight=QFont.Bold))
                item_total_col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.table.setItem(total_row, col, item_total_col)

            conn.close()
            self.format_table()
            for row, nome in enumerate(linhas):
                self.table.setRowHeight(row, 31)

        except Exception as e:
            print(f"[ERROR] Erro ao carregar dados: {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.bloquear_sinal = False

    def salvar_metas(self):
        if not self.user_info.get("is_admin", False):
            print("[ACESSO NEGADO] Apenas administradores podem salvar metas.")
            return

        try:
            conn = connect_db()
            cursor = conn.cursor()

            ano_selecionado = int(self.year_combo.currentText())

            # Garante FK no SQLite (boa prática)
            cursor.execute("PRAGMA foreign_keys = ON;")

            for row in range(self.table.rowCount()):
                item_nome = self.table.item(row, 0)
                if not item_nome:
                    continue

                nome_exibido = item_nome.text().strip()

                # Ignora linha TOTAL
                if nome_exibido.upper() == "TOTAL":
                    continue

                # Remove o prefixo do grupo "🔽 "
                nome_proc = nome_exibido.replace("🔽", "").strip()

                try:
                    meta_cfc = int(self.table.item(row, 1).text())
                    meta_crcdf = int(self.table.item(row, 2).text())
                except (ValueError, AttributeError):
                    print(f"[AVISO] Valores inválidos ou ausentes para: {nome_proc}")
                    continue

                # Se é grupo, divide meta entre os procedimentos do grupo
                if nome_proc in self.grupos:
                    procedimentos = self.grupos[nome_proc]
                    qtd = len(procedimentos)
                    if qtd == 0:
                        continue

                    base_cfc = meta_cfc // qtd
                    resto_cfc = meta_cfc % qtd

                    base_crcdf = meta_crcdf // qtd
                    resto_crcdf = meta_crcdf % qtd

                    for i, procedimento in enumerate(procedimentos):
                        # distribui o "resto" 1 a 1 nos primeiros
                        meta_cfc_ind = base_cfc + (1 if i < resto_cfc else 0)
                        meta_crcdf_ind = base_crcdf + (1 if i < resto_crcdf else 0)

                        cursor.execute("SELECT id FROM procedures WHERE name = ?", (procedimento,))
                        row_id = cursor.fetchone()
                        if not row_id:
                            print(f"[AVISO] Procedimento não encontrado no banco: {procedimento}")
                            continue
                        procedure_id = row_id[0]

                        cursor.execute("""
                            INSERT INTO metas_anuais (procedure_id, ano, meta_cfc, meta_crcdf)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(procedure_id, ano)
                            DO UPDATE SET
                                meta_cfc = excluded.meta_cfc,
                                meta_crcdf = excluded.meta_crcdf
                        """, (procedure_id, ano_selecionado, meta_cfc_ind, meta_crcdf_ind))

                else:
                    # Procedimento individual
                    cursor.execute("SELECT id FROM procedures WHERE name = ?", (nome_proc,))
                    row_id = cursor.fetchone()
                    if not row_id:
                        print(f"[AVISO] Procedimento não encontrado no banco: {nome_proc}")
                        continue
                    procedure_id = row_id[0]

                    cursor.execute("""
                        INSERT INTO metas_anuais (procedure_id, ano, meta_cfc, meta_crcdf)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(procedure_id, ano)
                        DO UPDATE SET
                            meta_cfc = excluded.meta_cfc,
                            meta_crcdf = excluded.meta_crcdf
                    """, (procedure_id, ano_selecionado, meta_cfc, meta_crcdf))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Sucesso", f"Metas do ano {ano_selecionado} salvas com sucesso!")
            print("[SUCESSO] Metas anuais atualizadas com sucesso.")
            self.metas_atualizadas.emit()

            # Recarrega para refletir COALESCE/ano
            self.load_data()

        except Exception as e:
            print(f"[ERRO] Falha ao salvar metas anuais: {e}")
            import traceback
            print(traceback.format_exc())
            QMessageBox.critical(self, "Erro", f"Falha ao salvar metas anuais:\n{e}")

    def copiar_tabela_para_clipboard(self):
        """Copia a seleção atual da tabela para a área de transferência em formato tabulado."""
        ranges = self.table.selectedRanges()
        if not ranges:
            return

        linhas_texto = []
        for r in ranges:
            for row in range(r.topRow(), r.bottomRow() + 1):
                col_texto = []
                for col in range(r.leftColumn(), r.rightColumn() + 1):
                    item = self.table.item(row, col)
                    col_texto.append(item.text() if item else "")
                linhas_texto.append("\t".join(col_texto))
        QApplication.clipboard().setText("\n".join(linhas_texto).strip())

    def format_table(self):
        self.table.setAlternatingRowColors(True)

        # Estilo das células
        self.table.setStyleSheet("""
            alternate-background-color: #f5f5f5; 
            background-color: white;
            QTableWidget::item {
                padding: 1px;
                margin: 0px;
                border: none;
            }
        """)

        header = self.table.horizontalHeader()
        header.setMinimumSectionSize(40)  # permite colunas estreitas se necessário

        # Coluna 0 (Procedimento): usa o espaço que sobra
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # Demais colunas: se ajustam ao conteúdo com um limite máximo de largura
        for col in range(1, self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            self.table.setColumnWidth(col, min(self.table.columnWidth(col), 100))  # limite máximo opcional

        # Estilo do cabeçalho
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #002060;
                color: white;
                font-weight: bold;
                padding: 3px;
                border: 1px solid white;
                text-align: center;
            }
        """)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(24)
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)

    def sanitize_text(texto):
        return unidecode(texto)

    def exportar_pdf_excel(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        from fpdf import FPDF
        import os
        import re

        def sanitize_text(texto):
            texto = re.sub(r"[^\x00-\x7F]+", "", texto)  # Remove emojis/símbolos
            try:
                return texto.encode("latin-1").decode("latin-1")
            except:
                return texto.encode("latin-1", errors="replace").decode("latin-1")

        try:
            # Expande os grupos recolhidos
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.text().startswith("🔽"):
                    self.toggle_expand(row)

            caminho, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Resultados do Fiscal",
                "",
                "Arquivo Excel (*.xlsx);;Arquivo PDF (*.pdf)"
            )
            if not caminho:
                return

            # Coleta dados
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
                import pandas as pd
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
                        self.cell(0, 10, "Relatório - Resultados do Fiscal", ln=True, align='C')
                        self.ln(2)

                    def footer(self):
                        self.set_y(-15)
                        self.set_font("Helvetica", style='I', size=8)
                        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

                pdf = PDF()

                # Larguras proporcionais
                largura_total = 277
                pdf.set_font("Helvetica", size=7)
                larguras = []
                for i, col in enumerate(colunas):
                    largura = pdf.get_string_width(col) + 4
                    for linha in dados:
                        if i < len(linha):
                            largura = max(largura, pdf.get_string_width(linha[i]) + 4)
                    larguras.append(min(largura, 90))
                fator = largura_total / sum(larguras)
                larguras = [w * fator for w in larguras]

                # Cabeçalho
                pdf.set_fill_color(230, 230, 230)
                pdf.set_font("Helvetica", style='B', size=7)
                for i, titulo in enumerate(colunas):
                    pdf.cell(larguras[i], 7, titulo, border=1, align="C", fill=True)
                pdf.ln()

                # Dados com altura uniforme
                pdf.set_font("Helvetica", size=7)
                for linha in dados:
                    x = pdf.get_x()
                    y = pdf.get_y()

                    # Mede altura da primeira célula com multi_cell
                    linhas_proced = pdf.multi_cell(larguras[0], 4, linha[0], border=0, align='L', split_only=True)
                    altura_linha = 4 * len(linhas_proced)

                    # Primeira célula com multi_cell
                    pdf.set_xy(x, y)
                    pdf.multi_cell(larguras[0], 4, linha[0], border=1, align='L')
                    pdf.set_xy(x + larguras[0], y)

                    # Outras células com altura padronizada
                    for i in range(1, len(linha)):
                        pdf.cell(larguras[i], altura_linha, linha[i], border=1, align='L')

                    pdf.set_y(y + altura_linha)

                pdf.output(caminho)
                QMessageBox.information(self, "Sucesso", "Exportação para PDF concluída!")

            else:
                QMessageBox.warning(self, "Formato inválido", "Escolha um formato .xlsx ou .pdf")

        except Exception as e:
            import traceback
            erro = traceback.format_exc()
            QMessageBox.critical(self, "Erro", f"Falha ao exportar:\n{str(e)}\n\n{erro}")


class AgrupadorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Criar Grupo de Procedimentos")
        self.setMinimumWidth(400)
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Nome do Grupo:"))
        self.nome_input = QLineEdit()
        self.layout.addWidget(self.nome_input)
        self.procedimentos_list = QListWidget()
        self.layout.addWidget(self.procedimentos_list)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.salvar_grupo)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)
        self.carregar_procedimentos()

    def carregar_procedimentos(self):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.name FROM procedures p
            WHERE p.name != 'CANCELADO'
              AND p.id NOT IN (SELECT procedimento_id FROM grupo_itens)
            ORDER BY p.name ASC
        """)
        for proc in cursor.fetchall():
            item = QListWidgetItem(proc[0])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.procedimentos_list.addItem(item)
        conn.close()

    def salvar_grupo(self):
        nome_grupo = self.nome_input.text().strip()
        if not nome_grupo:
            QMessageBox.warning(self, "Atenção", "Digite um nome para o grupo.")
            return

        selecionados = [
            self.procedimentos_list.item(i).text()
            for i in range(self.procedimentos_list.count())
            if self.procedimentos_list.item(i).checkState() == Qt.Checked
        ]

        if not selecionados:
            QMessageBox.warning(self, "Atenção", "Selecione ao menos um procedimento.")
            return

        try:
            conn = connect_db()
            cursor = conn.cursor()

            # Cria o grupo
            cursor.execute("INSERT INTO grupos_procedimentos (nome_grupo) VALUES (?)", (nome_grupo,))
            grupo_id = cursor.lastrowid

            # Mapeia nome → ID dos procedimentos
            cursor.execute("SELECT id, name FROM procedures")
            proc_map = {name: id_ for id_, name in cursor.fetchall()}

            # Lista para armazenar os IDs usados no grupo
            ids_usados = []

            for nome in selecionados:
                proc_id = proc_map.get(nome)
                if proc_id:
                    ids_usados.append(proc_id)
                    cursor.execute(
                        "INSERT INTO grupo_itens (grupo_id, procedimento_id) VALUES (?, ?)",
                        (grupo_id, proc_id)
                    )

            conn.commit()
            conn.close()

            print(f"[DEBUG] IDs agrupados para '{nome_grupo}': {ids_usados}")
            QMessageBox.information(self, "Sucesso", "Grupo criado com sucesso!")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar grupo: {e}")
            self.reject()


class GrupoTableWidget(QTableWidget):
    def __init__(self, parent=None, toggle_callback=None):
        super().__init__(parent)
        self.toggle_callback = toggle_callback

    def mouseReleaseEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            row = index.row()
            column = index.column()
            item = self.item(row, 0)
            if item:
                texto = item.text()
                if texto.startswith("🔽") or texto.startswith("🔼"):
                    print(f"[DEBUG] Clique no grupo: {texto}, linha: {row}")
                    if self.toggle_callback:
                        self.toggle_callback(row)
        super().mouseReleaseEvent(event)
