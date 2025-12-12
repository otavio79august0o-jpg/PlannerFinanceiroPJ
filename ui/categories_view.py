from __future__ import annotations

from typing import Optional

from PyQt5 import QtWidgets, QtCore

# Import functions from core.models instead of direct models module
# Importa diretamente do módulo de modelos. Se o projeto possuir um pacote
# ``core`` com ``models``, ajuste este import conforme necessário.
from core.models import (
    listar_categorias,
    criar_categoria,
    editar_categoria,
    excluir_categoria,
)


class CategoriaDialog(QtWidgets.QDialog):
    """
    Diálogo para criar/editar uma categoria.
    """

    def __init__(
        self,
        codigoempresa: str,
        parent: Optional[QtWidgets.QWidget] = None,
        categoria: Optional[dict] = None,
    ):
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.categoria = categoria or {}
        self.setWindowTitle(
            "Editar Categoria" if self.categoria else "Nova Categoria"
        )
        self.setModal(True)
        self.resize(400, 250)
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        # Nome
        self.edit_nome = QtWidgets.QLineEdit()
        self.edit_nome.setPlaceholderText("Nome da categoria")
        if self.categoria:
            self.edit_nome.setText(self.categoria.get("nome", ""))
        form.addRow("Nome:", self.edit_nome)

        # Tipo
        self.combo_tipo = QtWidgets.QComboBox()
        self.combo_tipo.addItems([
            "receita",
            "custo",
            "despesa",
            "tributo",
            "pessoal",
            "investimento",
            "estoque",
            "outro",
        ])
        if self.categoria:
            tipo = self.categoria.get("tipo")
            idx = self.combo_tipo.findText(tipo)
            if idx >= 0:
                self.combo_tipo.setCurrentIndex(idx)
        form.addRow("Tipo:", self.combo_tipo)

        # Grupo
        self.edit_grupo = QtWidgets.QLineEdit()
        self.edit_grupo.setPlaceholderText("Grupo (opcional)")
        if self.categoria:
            self.edit_grupo.setText(self.categoria.get("grupo", ""))
        form.addRow("Grupo:", self.edit_grupo)

        # Ordem
        self.spin_ordem = QtWidgets.QSpinBox()
        self.spin_ordem.setMinimum(0)
        self.spin_ordem.setMaximum(1000)
        if self.categoria:
            ordem = self.categoria.get("ordem_exibicao")
            if ordem is not None:
                self.spin_ordem.setValue(ordem)
        form.addRow("Ordem:", self.spin_ordem)

        layout.addLayout(form)

        # Botões
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch()
        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QtWidgets.QPushButton("Salvar")
        btn_save.clicked.connect(self._on_save)
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)

    def _on_save(self):
        nome = self.edit_nome.text().strip()
        tipo = self.combo_tipo.currentText().strip()
        grupo = self.edit_grupo.text().strip() or None
        ordem = self.spin_ordem.value()
        if not nome:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Informe o nome da categoria."
            )
            return
        try:
            if self.categoria:
                editar_categoria(
                    self.categoria["id"], nome, tipo, grupo, ordem
                )
            else:
                criar_categoria(
                    self.codigoempresa, nome, tipo, grupo, ordem
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao salvar categoria:\n{exc}"
            )
            return
        self.accept()


class CategoriesView(QtWidgets.QWidget):
    """
    Página de gerenciamento de categorias e tipos.
    """

    def __init__(self, codigoempresa: str, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Categorias & Tipos")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Tabela
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Nome",
            "Tipo",
            "Grupo",
            "Ordem",
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

        # Botões
        btn_row = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Adicionar")
        btn_edit = QtWidgets.QPushButton("Editar")
        btn_del = QtWidgets.QPushButton("Excluir")
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_edit)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        btn_add.clicked.connect(self._add_categoria)
        btn_edit.clicked.connect(self._edit_categoria)
        btn_del.clicked.connect(self._delete_categoria)

        self._carregar_categorias()

    def _carregar_categorias(self):
        categorias = listar_categorias(self.codigoempresa)
        self.table.setRowCount(len(categorias))
        for row_idx, cat in enumerate(categorias):
            items = [
                str(cat.get("id")),
                cat.get("nome", ""),
                cat.get("tipo", ""),
                cat.get("grupo", "") or "",
                str(cat.get("ordem_exibicao") or 0),
            ]
            for col, val in enumerate(items):
                item = QtWidgets.QTableWidgetItem(val)
                if col == 0:
                    item.setData(QtCore.Qt.UserRole, cat)
                self.table.setItem(row_idx, col, item)

    def _get_selected_categoria(self) -> Optional[dict]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row_idx = rows[0].row()
        item = self.table.item(row_idx, 0)
        cat = item.data(QtCore.Qt.UserRole)
        return cat

    def _add_categoria(self):
        dlg = CategoriaDialog(self.codigoempresa, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_categorias()

    def _edit_categoria(self):
        cat = self._get_selected_categoria()
        if not cat:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione uma categoria para editar."
            )
            return
        dlg = CategoriaDialog(self.codigoempresa, self, categoria=cat)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._carregar_categorias()

    def _delete_categoria(self):
        cat = self._get_selected_categoria()
        if not cat:
            QtWidgets.QMessageBox.warning(
                self, "Atenção", "Selecione uma categoria para excluir."
            )
            return
        resp = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            f"Deseja excluir a categoria '{cat.get('nome')}'?",
        )
        if resp != QtWidgets.QMessageBox.Yes:
            return
        try:
            excluir_categoria(cat["id"])
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self, "Erro", f"Falha ao excluir categoria:\n{exc}"
            )
            return
        self._carregar_categorias()