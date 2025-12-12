from __future__ import annotations

"""
UI module for managing accounts.  This view presents a table of all active
bank accounts for the current company and allows the user to create,
edit and delete accounts.  Accounts include bank accounts, credit cards,
investment accounts and cash.  The dialog captures all fields defined
in the database schema.

Each account record includes:
  - nome_conta: user friendly name
  - tipo_conta: type (corrente, poupanca, cartao_credito, investimento,
                 conta_garantida, caixa, etc.)
  - banco: bank name
  - agencia: agency/branch
  - numero: account number
  - moeda: currency code (BRL by default)
  - limite_cheque_especial: overdraft limit
  - limite_cartao: credit card limit
  - dia_vencimento_fatura: day of the month the credit card bill is due
  - ativa: whether the account is active

The view uses functions from `models.py` to retrieve and persist data.
"""

from typing import Optional

from PyQt5 import QtWidgets, QtCore

# Importa as funções de conta diretamente do módulo de modelos.
from core.models import (
    listar_contas,
    criar_conta,
    editar_conta,
    excluir_conta,
)


class ContaDialog(QtWidgets.QDialog):
    """Dialog for creating or editing a bank account."""

    def __init__(
        self,
        codigoempresa: str,
        parent: Optional[QtWidgets.QWidget] = None,
        conta: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.conta = conta or {}
        self.setWindowTitle(
            "Editar Conta" if self.conta else "Nova Conta"
        )
        self.setModal(True)
        self.resize(500, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        # Nome da conta
        self.edit_nome = QtWidgets.QLineEdit()
        self.edit_nome.setPlaceholderText("Nome da conta")
        if self.conta:
            self.edit_nome.setText(self.conta.get("nome_conta", ""))
        form.addRow("Nome:", self.edit_nome)

        # Tipo de conta
        self.combo_tipo = QtWidgets.QComboBox()
        # Tipos conforme definido no schema
        tipos = [
            "corrente",
            "poupanca",
            "cartao_credito",
            "investimento",
            "caixa",
            "conta_garantida",
        ]
        self.combo_tipo.addItems(tipos)
        if self.conta:
            tipo = self.conta.get("tipo_conta")
            idx = self.combo_tipo.findText(tipo)
            if idx >= 0:
                self.combo_tipo.setCurrentIndex(idx)
        form.addRow("Tipo:", self.combo_tipo)

        # Banco
        self.edit_banco = QtWidgets.QLineEdit()
        self.edit_banco.setPlaceholderText("Banco")
        if self.conta:
            self.edit_banco.setText(self.conta.get("banco", ""))
        form.addRow("Banco:", self.edit_banco)

        # Agência
        self.edit_agencia = QtWidgets.QLineEdit()
        self.edit_agencia.setPlaceholderText("Agência")
        if self.conta:
            self.edit_agencia.setText(self.conta.get("agencia", ""))
        form.addRow("Agência:", self.edit_agencia)

        # Número
        self.edit_numero = QtWidgets.QLineEdit()
        self.edit_numero.setPlaceholderText("Número da conta")
        if self.conta:
            self.edit_numero.setText(self.conta.get("numero", ""))
        form.addRow("Número:", self.edit_numero)

        # Moeda
        self.edit_moeda = QtWidgets.QLineEdit()
        self.edit_moeda.setPlaceholderText("Moeda (BRL)")
        if self.conta:
            self.edit_moeda.setText(self.conta.get("moeda", "BRL"))
        else:
            self.edit_moeda.setText("BRL")
        form.addRow("Moeda:", self.edit_moeda)

        # Limite de cheque especial
        self.spin_limite_especial = QtWidgets.QDoubleSpinBox()
        self.spin_limite_especial.setDecimals(2)
        self.spin_limite_especial.setMaximum(1e12)
        self.spin_limite_especial.setPrefix("R$ ")
        if self.conta:
            self.spin_limite_especial.setValue(
                self.conta.get("limite_cheque_especial", 0) or 0
            )
        form.addRow("Limite cheque especial:", self.spin_limite_especial)

        # Limite do cartão (para contas tipo cartao_credito)
        self.spin_limite_cartao = QtWidgets.QDoubleSpinBox()
        self.spin_limite_cartao.setDecimals(2)
        self.spin_limite_cartao.setMaximum(1e12)
        self.spin_limite_cartao.setPrefix("R$ ")
        if self.conta:
            self.spin_limite_cartao.setValue(
                self.conta.get("limite_cartao", 0) or 0
            )
        form.addRow("Limite cartão:", self.spin_limite_cartao)

        # Dia de vencimento da fatura
        self.spin_dia_fatura = QtWidgets.QSpinBox()
        self.spin_dia_fatura.setMinimum(1)
        self.spin_dia_fatura.setMaximum(31)
        if self.conta and self.conta.get("dia_vencimento_fatura"):
            self.spin_dia_fatura.setValue(
                self.conta.get("dia_vencimento_fatura")
            )
        form.addRow("Dia vencimento fatura:", self.spin_dia_fatura)

        layout.addLayout(form)

        # Botões
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QtWidgets.QPushButton("Salvar")
        btn_save.clicked.connect(self._on_save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def _on_save(self) -> None:
        # Gather data
        nome = self.edit_nome.text().strip()
        tipo = self.combo_tipo.currentText().strip()
        banco = self.edit_banco.text().strip() or None
        agencia = self.edit_agencia.text().strip() or None
        numero = self.edit_numero.text().strip() or None
        moeda = self.edit_moeda.text().strip() or "BRL"
        limite_especial = self.spin_limite_especial.value()
        limite_cartao = self.spin_limite_cartao.value()
        dia_fatura = self.spin_dia_fatura.value() or None
        if not nome:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Informe o nome da conta."
            )
            return
        try:
            if self.conta:
                # Edit
                editar_conta(
                    self.conta["id"],
                    nome,
                    tipo,
                    banco,
                    agencia,
                    numero,
                    moeda,
                    limite_especial,
                    limite_cartao,
                    dia_fatura,
                )
            else:
                # Create
                criar_conta(
                    self.codigoempresa,
                    nome,
                    tipo,
                    banco,
                    agencia,
                    numero,
                    moeda,
                    limite_especial,
                    limite_cartao,
                    dia_fatura,
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao salvar conta:\n{exc}"
            )
            return
        self.accept()


class AccountsView(QtWidgets.QWidget):
    """View for listing and managing bank accounts."""

    def __init__(self, codigoempresa: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Contas")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Table
        self.table = QtWidgets.QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Nome",
            "Tipo",
            "Banco",
            "Número",
            "Limite cheque",
            "Limite cartão",
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        layout.addWidget(self.table, 1)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar")
        btn_edit = QtWidgets.QPushButton("Editar")
        btn_del = QtWidgets.QPushButton("Excluir")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btn_add.clicked.connect(self._add_conta)
        btn_edit.clicked.connect(self._edit_conta)
        btn_del.clicked.connect(self._delete_conta)

        self._carregar_contas()

    def _carregar_contas(self) -> None:
        contas = listar_contas(self.codigoempresa)
        self.table.setRowCount(len(contas))
        for row_idx, conta in enumerate(contas):
            items = [
                str(conta.get("id")),
                conta.get("nome_conta", ""),
                conta.get("tipo_conta", ""),
                conta.get("banco", "") or "",
                conta.get("numero", "") or "",
                f"{conta.get('limite_cheque_especial') or 0:.2f}",
                f"{conta.get('limite_cartao') or 0:.2f}",
            ]
            for col, val in enumerate(items):
                item = QtWidgets.QTableWidgetItem(val)
                if col == 0:
                    item.setData(QtCore.Qt.UserRole, conta)
                self.table.setItem(row_idx, col, item)

    def _get_selected_conta(self) -> Optional[dict]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row_idx = rows[0].row()
        item = self.table.item(row_idx, 0)
        return item.data(QtCore.Qt.UserRole)

    def _add_conta(self) -> None:
        dlg = ContaDialog(self.codigoempresa, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_contas()

    def _edit_conta(self) -> None:
        conta = self._get_selected_conta()
        if not conta:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione uma conta para editar."
            )
            return
        dlg = ContaDialog(self.codigoempresa, self, conta=conta)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_contas()

    def _delete_conta(self) -> None:
        conta = self._get_selected_conta()
        if not conta:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione uma conta para excluir."
            )
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            f"Deseja excluir a conta '{conta.get('nome_conta')}'?",
        )
        if resp != QtWidgets.QMessageBox.Yes:
            return
        try:
            excluir_conta(conta["id"])
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao excluir conta:\n{exc}"
            )
            return
        self._carregar_contas()