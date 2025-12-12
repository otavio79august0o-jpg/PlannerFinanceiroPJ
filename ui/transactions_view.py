"""
Transactions view for MF Financier PJ.

This module provides a widget to display and manage financial
transactions.  It includes a table listing recent transactions and
allows the user to edit or delete selected transactions.  An
associated dialog class is provided to edit basic fields such as
description, category, centre of cost and value.  The data is
retrieved and updated through functions defined in ``core.models``.

The view expects a ``codigoempresa`` identifying the current
company.  All operations are scoped to this company.  The view
communicates with the rest of the application via the models module
and does not directly interact with the database.
"""

from __future__ import annotations

from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui

try:
    # Tenta importar de pacote "core" se existir
    from core import models  # type: ignore
except ImportError:
    # Caso contrário, importa diretamente o módulo models do projeto
    import models  # type: ignore


class TransacaoDialog(QtWidgets.QDialog):
    """Dialog to edit a single transaction.

    Parameters
    ----------
    codigoempresa: str
        The company code to which the transaction belongs.
    transacao: dict | None
        The transaction to edit.  If None, the dialog behaves as a
        placeholder and does nothing on accept.
    parent: QWidget | None
        Parent widget.
    """

    def __init__(self, codigoempresa: str, transacao: Optional[dict], parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.transacao = transacao or {}
        self.setWindowTitle("Editar Transação")
        self.setModal(True)

        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Descrição tratada
        self.edit_descricao = QtWidgets.QLineEdit()
        layout.addRow("Descrição:", self.edit_descricao)

        # Categoria
        self.combo_categoria = QtWidgets.QComboBox()
        self.combo_categoria.setEditable(False)
        # Populate categories
        categorias = models.listar_categorias(self.codigoempresa)
        self.combo_categoria.addItem("-- Nenhuma --", None)
        for cat in categorias:
            self.combo_categoria.addItem(cat["nome"], cat["id"])
        layout.addRow("Categoria:", self.combo_categoria)

        # Centro de custo
        self.combo_centro = QtWidgets.QComboBox()
        self.combo_centro.setEditable(False)
        centros = models.listar_centros_custo(self.codigoempresa)
        self.combo_centro.addItem("-- Nenhum --", None)
        for cc in centros:
            self.combo_centro.addItem(cc["nome"], cc["id"])
        layout.addRow("Centro de Custo:", self.combo_centro)

        # Valor
        self.edit_valor = QtWidgets.QLineEdit()
        layout.addRow("Valor:", self.edit_valor)

        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self,
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addRow(btn_box)

    def _populate_fields(self) -> None:
        """Populate widgets with existing transaction data."""
        if not self.transacao:
            return
        self.edit_descricao.setText(self.transacao.get("descricao_tratada") or "")
        # set category
        cat_id = self.transacao.get("categoria_id")
        if cat_id:
            index = self.combo_categoria.findData(cat_id)
            if index >= 0:
                self.combo_categoria.setCurrentIndex(index)
        # set centre
        cc_id = self.transacao.get("centro_custo_id")
        if cc_id:
            index = self.combo_centro.findData(cc_id)
            if index >= 0:
                self.combo_centro.setCurrentIndex(index)
        # set value
        valor = self.transacao.get("valor")
        if valor is not None:
            self.edit_valor.setText(f"{valor:.2f}")

    def _on_accept(self) -> None:
        """Handle OK click: update the transaction and close dialog."""
        descricao = self.edit_descricao.text().strip()
        categoria_id = self.combo_categoria.currentData()
        centro_id = self.combo_centro.currentData()
        valor_txt = self.edit_valor.text().replace(",", ".").strip()
        try:
            valor = float(valor_txt) if valor_txt else None
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Valor inválido", "Informe um valor numérico.")
            return
        try:
            if self.transacao:
                # Update existing transaction
                models.editar_transacao(
                    self.transacao["id"],
                    descricao if descricao else None,
                    categoria_id,
                    centro_id,
                    valor,
                    None,
                    None,
                )
            else:
                # Create a new transaction. We'll need a conta; ask the user to select one.
                contas = models.listar_contas(self.codigoempresa)
                if not contas:
                    QtWidgets.QMessageBox.warning(self, "Nenhuma conta", "Crie uma conta antes de adicionar transações.")
                    return
                # If only one account, use it; otherwise prompt user to select one
                if len(contas) == 1:
                    conta_id = contas[0]["id"]
                else:
                    names = [c.get("nome_conta") or str(c.get("id")) for c in contas]
                    item, ok = QtWidgets.QInputDialog.getItem(
                        self,
                        "Selecionar Conta",
                        "Escolha a conta para a transação:",
                        names,
                        0,
                        False,
                    )
                    if not ok:
                        return
                    idx = names.index(item)
                    conta_id = contas[idx]["id"]
                # Data de lançamento: hoje
                data_lanc = QtCore.QDate.currentDate().toString("yyyy-MM-dd")
                models.criar_transacao(
                    self.codigoempresa,
                    conta_id,
                    data_lanc,
                    self.edit_descricao.text().strip() or "",
                    descricao if descricao else None,
                    valor,
                    categoria_id,
                    centro_id,
                    None,
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", str(exc))
            return
        self.accept()


class TransactionsView(QtWidgets.QWidget):
    """Widget to display and manage financial transactions."""

    def __init__(self, codigoempresa: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        # Keep track of current theme to adjust styles on the fly
        self.current_theme: str = "dark"
        self._build_ui()
        self._load_data()

    def set_theme(self, theme: str) -> None:
        """Update the current theme and reload data for styling."""
        if theme not in ("dark", "light"):
            return
        self.current_theme = theme
        # Update title color based on theme
        if hasattr(self, "title"):
            self.title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: {}".format(
                    "#e5e7eb" if theme == "dark" else "#111827"
                )
            )
        # Reload data to rebuild cards with appropriate styles
        self._load_data()

        # Atualiza a cor do resumo
        if hasattr(self, "lbl_summary"):
            sum_color = "#9ca3af" if theme == "dark" else "#6b7280"
            self.lbl_summary.setStyleSheet(f"font-size: 12px; color: {sum_color};")

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Título
        self.title = QtWidgets.QLabel("Transações")
        # O estilo do título será definido em set_theme; aplica valor padrão aqui
        self.title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e5e7eb;")
        layout.addWidget(self.title)

        # Área de filtros
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.setSpacing(8)
        # Campo de busca
        self.search_edit = QtWidgets.QLineEdit()
        self.search_edit.setPlaceholderText("Pesquisar descrição...")
        filter_layout.addWidget(self.search_edit, 2)
        # Data início
        self.start_date_edit = QtWidgets.QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("dd/MM/yyyy")
        filter_layout.addWidget(self.start_date_edit, 1)
        # Data fim
        self.end_date_edit = QtWidgets.QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd/MM/yyyy")
        filter_layout.addWidget(self.end_date_edit, 1)
        # Botão filtrar
        self.btn_filter = QtWidgets.QPushButton("Filtrar")
        filter_layout.addWidget(self.btn_filter)
        layout.addLayout(filter_layout)

        # Área de cartões em um scroll
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

        # Área de botões
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setAlignment(QtCore.Qt.AlignRight)
        self.btn_add = QtWidgets.QPushButton("Adicionar")
        self.btn_refresh = QtWidgets.QPushButton("Atualizar")
        # Botões Editar/Excluir gerais são desabilitados pois cada cartão possui seus próprios botões
        self.btn_edit = QtWidgets.QPushButton("Editar")
        self.btn_edit.setEnabled(False)
        self.btn_delete = QtWidgets.QPushButton("Excluir")
        self.btn_delete.setEnabled(False)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        layout.addLayout(btn_layout)

        # Resumo de receitas/despesas
        self.lbl_summary = QtWidgets.QLabel("")
        self.lbl_summary.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(self.lbl_summary)

        # Conexões
        self.btn_filter.clicked.connect(self._load_data)
        self.btn_refresh.clicked.connect(self._load_data)
        # Para cartões, edição/exclusão serão tratadas individualmente em cada card
        self.btn_edit.clicked.connect(self._edit_selected)
        self.btn_delete.clicked.connect(self._delete_selected)
        self.btn_add.clicked.connect(self._add_transaction)

    def _load_data(self) -> None:
        """
        Load transactions into the table, applying optional filters from
        the search text and date fields. Also updates the summary label.
        """
        # Build filter parameters
        busca = self.search_edit.text().strip() or None
        data_inicio = None
        # Only use start date if the QDate is valid and not null
        qd_start = self.start_date_edit.date()
        if qd_start.isValid() and not qd_start.isNull():
            data_inicio = qd_start.toString("yyyy-MM-dd")
        data_fim = None
        qd_end = self.end_date_edit.date()
        if qd_end.isValid() and not qd_end.isNull():
            data_fim = qd_end.toString("yyyy-MM-dd")

        try:
            transacoes = models.listar_transacoes_filtradas(
                self.codigoempresa,
                busca=busca,
                data_inicio=data_inicio,
                data_fim=data_fim,
                limite=500,
            )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao carregar transações:\n{exc}",
            )
            return

        # Atualiza resumo de receitas e despesas
        total_receitas = sum(t.get("valor", 0) for t in transacoes if t.get("valor", 0) > 0)
        total_despesas = sum(-t.get("valor", 0) for t in transacoes if t.get("valor", 0) < 0)
        self.lbl_summary.setText(
            f"Receitas: {total_receitas:.2f} | Despesas: {total_despesas:.2f}"
        )

        # Remove cartões existentes
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for t in transacoes:
            # Determine base colors based on theme
            if self.current_theme == "light":
                card_bg = "#ffffff"
                header_color = "#111827"
                info_color = "#6b7280"
            else:
                card_bg = "#0f172a"
                header_color = "#e5e7eb"
                info_color = "#9ca3af"
            # Create a card with coloured side bar
            outer_frame = QtWidgets.QFrame()
            outer_layout = QtWidgets.QHBoxLayout(outer_frame)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            outer_layout.setSpacing(0)
            # Color bar
            valor = t.get("valor")
            bar = QtWidgets.QFrame()
            bar.setFixedWidth(6)
            if valor is not None:
                if valor > 0:
                    bar_color = "#22c55e"
                elif valor < 0:
                    bar_color = "#ef4444"
                else:
                    bar_color = "#6b7280"
            else:
                bar_color = "#6b7280"
            bar.setStyleSheet(
                f"background-color: {bar_color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px;"
            )
            outer_layout.addWidget(bar)
            # Card content
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                f"background-color: {card_bg}; border-radius: 8px; padding: 8px;"
            )
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(4)
            # Linha principal: descrição e valor
            header_layout = QtWidgets.QHBoxLayout()
            lbl_desc = QtWidgets.QLabel(t.get("descricao_tratada") or t.get("descricao_extrato") or "")
            lbl_desc.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {header_color};"
            )
            header_layout.addWidget(lbl_desc)
            header_layout.addStretch()
            lbl_valor = QtWidgets.QLabel(
                f"{valor:.2f}" if valor is not None else ""
            )
            # Color value text
            if valor is not None:
                if valor > 0:
                    val_color = "#22c55e"
                elif valor < 0:
                    val_color = "#ef4444"
                else:
                    val_color = header_color
            else:
                val_color = header_color
            lbl_valor.setStyleSheet(
                f"color: {val_color}; font-size: 14px; font-weight: bold;"
            )
            header_layout.addWidget(lbl_valor)
            card_layout.addLayout(header_layout)
            # Linha secundária: Data, Conta, Categoria, Centro
            info_parts = []
            data = t.get("data_lancamento") or ""
            if data:
                info_parts.append(f"{data}")
            conta = t.get("nome_conta") or ""
            if conta:
                info_parts.append(f"Conta: {conta}")
            categoria = t.get("categoria_nome") or ""
            if categoria:
                info_parts.append(f"Categoria: {categoria}")
            centro = t.get("centro_nome") or ""
            if centro:
                info_parts.append(f"Centro: {centro}")
            forma = t.get("forma_pagamento") or ""
            if forma:
                info_parts.append(f"Forma: {forma}")
            tipo_str = "Crédito" if (valor is not None and valor > 0) else "Débito"
            info_parts.append(tipo_str)
            lbl_info = QtWidgets.QLabel("  |  ".join(info_parts))
            lbl_info.setStyleSheet(
                f"font-size: 11px; color: {info_color};"
            )
            card_layout.addWidget(lbl_info)
            # Botões de ação
            btn_layout = QtWidgets.QHBoxLayout()
            btn_edit = QtWidgets.QPushButton("Editar")
            btn_edit.setFixedWidth(60)
            btn_delete = QtWidgets.QPushButton("Excluir")
            btn_delete.setFixedWidth(60)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)
            btn_layout.addStretch()
            card_layout.addLayout(btn_layout)
            # Armazena a transação no botão
            btn_edit.clicked.connect(lambda _=False, d=t: self._edit_card(d))
            btn_delete.clicked.connect(lambda _=False, d=t: self._delete_card(d))
            # Add card content to outer layout
            outer_layout.addWidget(card)
            # Add outer frame to container
            self.cards_layout.addWidget(outer_frame)
        # Adiciona um espaçador para empurrar cartões para cima
        self.cards_layout.addStretch()

    def _add_transaction(self) -> None:
        """Open a dialog to create a new transaction."""
        # Create an empty dialog (transacao=None)
        dlg = TransacaoDialog(self.codigoempresa, None, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._load_data()

    # ------------------------------------------------------------------
    # Card-based actions
    # ------------------------------------------------------------------
    def _edit_card(self, transacao: dict) -> None:
        """Edit a specific transaction represented by a card."""
        dlg = TransacaoDialog(self.codigoempresa, transacao, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._load_data()

    def _delete_card(self, transacao: dict) -> None:
        """Delete a specific transaction represented by a card."""
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            "Deseja realmente excluir esta transação?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return
        try:
            models.excluir_transacao(transacao["id"])
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao excluir transação:\n{exc}")
            return
        self._load_data()

    def _edit_selected(self) -> None:
        """Override base method. Not used in card mode."""
        QtWidgets.QMessageBox.information(self, "Editar", "Selecione uma transação usando os botões de cada cartão.")

    def _delete_selected(self) -> None:
        """Override base method. Not used in card mode."""
        QtWidgets.QMessageBox.information(self, "Excluir", "Use o botão Excluir em cada cartão.")
