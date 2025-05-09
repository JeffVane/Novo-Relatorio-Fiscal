from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton,
                             QLabel, QHBoxLayout, QSpinBox, QWidget, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from db import get_procedures, assign_procedure

class ProceduresWindow(QDialog):
    def __init__(self, agendamento_data, parent=None):
        super().__init__(parent)
        self.agendamento_data = agendamento_data  # Dados do agendamento selecionado
        self.selected_procedures = []
        self.setWindowTitle('Selecionar Procedimentos')
        self.setWindowIcon(QIcon('procedimento.png'))
        self.setFixedSize(1200, 600)
        try:
            self.initUI()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Inicialização", f"Falha ao inicializar a interface: {e}")
            self.close()

    def initUI(self):
        self.layout = QVBoxLayout()
        self.procedureList = QListWidget()
        self.procedureList.setSortingEnabled(True)

        try:
            procedures = get_procedures()
            if not procedures:
                QMessageBox.information(self, "Informação", "Nenhum procedimento disponível.")
                self.close()
                return

            for procedure_id, procedure_name in procedures:
                item = QListWidgetItem(procedure_name)
                item.setData(Qt.UserRole, procedure_id)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.procedureList.addItem(item)

            self.okButton = QPushButton('Confirmar Seleção')
            self.okButton.setIcon(QIcon("atribuir.png"))
            self.okButton.clicked.connect(self.handle_selection)
            self.layout.addWidget(self.procedureList)
            self.layout.addWidget(self.okButton)
            self.setLayout(self.layout)
        except Exception as e:
            QMessageBox.critical(self, "Erro de Configuração", f"Não foi possível configurar a interface: {e}")

    def handle_selection(self):
        try:
            self.selected_procedures.clear()
            for i in range(self.procedureList.count()):
                item = self.procedureList.item(i)
                if item.checkState() == Qt.Checked:
                    procedure_id = item.data(Qt.UserRole)
                    self.selected_procedures.append((procedure_id, item.text()))

            if not self.selected_procedures:
                QMessageBox.warning(self, "Seleção", "Por favor, selecione ao menos um procedimento.")
                return

            self.show_quantities_interface()
        except Exception as e:
            QMessageBox.critical(self, "Erro de Seleção", f"Erro durante a seleção: {e}")

    def show_quantities_interface(self):
        try:
            # Remover o botão "Confirmar Seleção" da seleção de procedimentos
            self.layout.removeWidget(self.okButton)
            self.okButton.deleteLater()

            # Limpar a lista de procedimentos
            self.procedureList.clear()

            # Iterar pelos procedimentos selecionados
            for procedure_id, procedure_name in self.selected_procedures:
                # Criar o widget que contém o nome do procedimento e o campo de quantidade
                widget = QWidget()
                widgetLayout = QHBoxLayout()

                # Rótulo com o nome do procedimento
                label = QLabel(procedure_name)
                widgetLayout.addWidget(label)

                # Campo para selecionar a quantidade
                spinBox = QSpinBox()
                spinBox.setMinimum(1)  # Quantidade mínima
                spinBox.setMaximum(100)  # Quantidade máxima
                spinBox.setFixedWidth(60)  # Define o tamanho do campo de quantidade
                widgetLayout.addWidget(spinBox)

                # Configurar o layout do widget
                widget.setLayout(widgetLayout)

                # Criar o item na lista e associar os dados
                listItem = QListWidgetItem()
                self.procedureList.addItem(listItem)
                self.procedureList.setItemWidget(listItem, widget)
                listItem.setSizeHint(widget.sizeHint())

                # Associar os dados (id do procedimento e nome do procedimento) ao item
                listItem.setData(Qt.UserRole, (procedure_id, procedure_name))  # ✅ Associando dados corretamente

            # Criar um layout para os botões "Cancelar" e "Confirmar Seleção"
            buttonLayout = QHBoxLayout()

            # Botão "Cancelar"
            self.cancelButton = QPushButton("Cancelar")
            self.cancelButton.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 8px; 
                    padding: 8px; 
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #c9302c;
                }
            """)
            self.cancelButton.clicked.connect(self.reject)  # Fecha a janela sem salvar

            # Botão "Confirmar Seleção"
            self.confirmButton = QPushButton("Confirmar Seleção")
            self.confirmButton.setStyleSheet("""
                QPushButton {
                    background-color: #5cb85c; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 8px; 
                    padding: 8px; 
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4cae4c;
                }
            """)

            # Conectar diretamente à função assign_procedure
            self.confirmButton.clicked.connect(self.collect_and_assign_procedures)

            # Adicionar os botões ao layout
            buttonLayout.addWidget(self.cancelButton)
            buttonLayout.addWidget(self.confirmButton)

            # Adicionar o layout dos botões ao layout principal
            self.layout.addLayout(buttonLayout)

        except Exception as e:
            QMessageBox.critical(self, "Erro de Interface",
                                 f"Não foi possível configurar a interface de quantidades: {e}")

    def collect_and_assign_procedures(self):
        """
        Coleta as quantidades inseridas e chama assign_procedure diretamente.
        """
        try:
            # Desativar botão para evitar cliques repetidos
            self.confirmButton.setEnabled(False)

            procedures_quantities = []

            for i in range(self.procedureList.count()):
                listItem = self.procedureList.item(i)
                widget = self.procedureList.itemWidget(listItem)
                spinBox = widget.findChild(QSpinBox)

                if spinBox and spinBox.value() > 0:
                    procedure_data = listItem.data(Qt.UserRole)
                    if not isinstance(procedure_data, tuple) or len(procedure_data) < 2:
                        print(f"[ERRO] Dados inválidos em procedure_data: {procedure_data}")
                        continue

                    procedure_name = procedure_data[1]
                    quantity = spinBox.value()
                    procedures_quantities.append((procedure_name, quantity))

            if not procedures_quantities:
                QMessageBox.warning(self, "Aviso", "Por favor, insira quantidades válidas.")
                self.confirmButton.setEnabled(True)  # Reativar botão se houver erro
                return

            # Chama a função assign_procedure diretamente
            assign_procedure(self.agendamento_data, procedures_quantities)

            QMessageBox.information(self, "Sucesso", "Procedimentos atribuídos com sucesso.")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao atribuir procedimentos: {e}")
            self.confirmButton.setEnabled(True)  # Reativar botão em caso de erro

    def get_selected_procedures(self):
        return self.selected_procedures
