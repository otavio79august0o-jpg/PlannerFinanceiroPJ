from __future__ import annotations

"""
UI module for managing budgets (orçamentos) for the company. Each budget
entry corresponds to a category and a specific month/year, storing the planned
amount for that period. The view allows users to list, create, edit and delete
budgets. It relies on functions defined in ``models.py`` and uses the
categories list to populate selections.

Fields per budget record:
  - categoria_id: reference to ``categories`` table
  - mes_ano: string in the format YYYY-MM
  - valor: numeric value representing the planned amount

"""

from typing import Optional

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QDate

# Import budget and category functions from core.models instead of direct models module
from core.models import (
    listar_orcamentos,
    criar_orcamento,
    editar_orcamento,
    excluir_orcamento,
    listar_categorias,
)


class OrcamentoDialog(QtWidgets.QDialog):
    """Dialog for creating or editing a budget entry."""

    def __init__(
        self,
        codigoempresa: str,
        parent: Optional[QtWidgets.QWidget] = None,
        orcamento: Optional[dict] = None,
    ) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.orcamento = orcamento or {}
        self.setWindowTitle(
            "Editar Orçamento" if self.orcamento else "Novo Orçamento"
        )
        self.setModal(True)
        self.resize(420, 260)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        # Categoria
        self.combo_categoria = QtWidgets.QComboBox()
        self.categorias = listar_categorias(self.codigoempresa)
        for cat in self.categorias:
            self.combo_categoria.addItem(cat.get("nome", ""), cat)
        if self.orcamento:
            # Set current category
            cat_id = self.orcamento.get("categoria_id")
            for idx, cat in enumerate(self.categorias):
                if cat.get("id") == cat_id:
                    self.combo_categoria.setCurrentIndex(idx)
                    break
        form.addRow("Categoria:", self.combo_categoria)

        # Mês/Ano
        self.date_edit = QtWidgets.QDateEdit()
        self.date_edit.setDisplayFormat("MM/yyyy")
        self.date_edit.setCalendarPopup(True)
        # When editing existing budget, set to corresponding month/year
        if self.orcamento:
            mes_ano = self.orcamento.get("mes_ano")
            try:
                # Expect format YYYY-MM
                year_str, month_str = mes_ano.split("-")
                year, month = int(year_str), int(month_str)
                self.date_edit.setDate(QDate(year, month, 1))
            except Exception:
                self.date_edit.setDate(QDate.currentDate())
        else:
            # Default to current month
            today = QDate.currentDate()
            self.date_edit.setDate(QDate(today.year(), today.month(), 1))
        form.addRow("Mês/Ano:", self.date_edit)

        # Valor
        self.spin_valor = QtWidgets.QDoubleSpinBox()
        self.spin_valor.setDecimals(2)
        self.spin_valor.setMaximum(1e12)
        self.spin_valor.setPrefix("R$ ")
        if self.orcamento:
            self.spin_valor.setValue(self.orcamento.get("valor") or 0)
        form.addRow("Valor:", self.spin_valor)

        layout.addLayout(form)

        # Buttons
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
        # Collect values
        cat_idx = self.combo_categoria.currentIndex()
        cat = self.combo_categoria.itemData(cat_idx)
        categoria_id = cat.get("id") if cat else None
        date = self.date_edit.date()
        mes_ano = date.toString("yyyy-MM")
        valor = self.spin_valor.value()
        if categoria_id is None:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione uma categoria para o orçamento."
            )
            return
        try:
            if self.orcamento:
                # Edit existing
                editar_orcamento(
                    self.orcamento["id"], categoria_id, mes_ano, valor
                )
            else:
                # Create new
                criar_orcamento(self.codigoempresa, categoria_id, mes_ano, valor)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao salvar orçamento:\n{exc}"
            )
            return
        self.accept()


class OrcamentosView(QtWidgets.QWidget):
    """
    Página para gerenciamento de orçamentos. Exibe todos os orçamentos
    cadastrados para a empresa e permite criar, editar e excluir registros.
    """

    def __init__(self, codigoempresa: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Orçamentos")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Table: ID, Categoria, Mês/Ano, Valor
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            "ID", "Categoria", "Mês/Ano", "Valor",
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

        btn_add.clicked.connect(self._add_orcamento)
        btn_edit.clicked.connect(self._edit_orcamento)
        btn_del.clicked.connect(self._delete_orcamento)

        self._carregar_orcamentos()

    def _carregar_orcamentos(self) -> None:
        orcamentos = listar_orcamentos(self.codigoempresa)
        self.table.setRowCount(len(orcamentos))
        for row_idx, orc in enumerate(orcamentos):
            items = [
                str(orc.get("id")),
                orc.get("categoria_nome") or "",
                orc.get("mes_ano") or "",
                f"{orc.get('valor') or 0:.2f}",
            ]
            for col, val in enumerate(items):
                item = QtWidgets.QTableWidgetItem(val)
                if col == 0:
                    item.setData(QtCore.Qt.UserRole, orc)
                self.table.setItem(row_idx, col, item)

    def _get_selected_orcamento(self) -> Optional[dict]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row_idx = rows[0].row()
        item = self.table.item(row_idx, 0)
        return item.data(QtCore.Qt.UserRole)

    def _add_orcamento(self) -> None:
        dlg = OrcamentoDialog(self.codigoempresa, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_orcamentos()

    def _edit_orcamento(self) -> None:
        orc = self._get_selected_orcamento()
        if not orc:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione um orçamento para editar."
            )
            return
        dlg = OrcamentoDialog(self.codigoempresa, self, orcamento=orc)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_orcamentos()

    def _delete_orcamento(self) -> None:
        orc = self._get_selected_orcamento()
        if not orc:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione um orçamento para excluir."
            )
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            f"Deseja excluir o orçamento da categoria '{orc.get('categoria_nome')}' referente a {orc.get('mes_ano')}?",
        )
        if resp != QtWidgets.QMessageBox.Yes:
            return
        try:
            excluir_orcamento(orc["id"])
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao excluir orçamento:\n{exc}"
            )
            return
        self._carregar_orcamentos()