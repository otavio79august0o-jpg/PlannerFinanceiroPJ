"""
Recorrentes view for MF Financier PJ.

This module provides a widget and dialog to manage recurring
transactions (despesas ou receitas recorrentes).  The list of
recorrentes is displayed in a table with the ability to add, edit
and delete entries.  Each recurring transaction includes basic
fields such as description, category, centre of cost, value,
frequency (e.g., mensal, semanal), next occurrence date and end
date, as well as a payment method and active flag.

The view communicates with the models layer (``core.models``) to
create, update and delete recurring transactions.  All operations
are scoped to the given ``codigoempresa``.
"""

from __future__ import annotations

from typing import Optional

from PyQt5 import QtWidgets, QtCore, QtGui

try:
    from core import models  # type: ignore
except ImportError:
    import models  # type: ignore


class RecorrenteDialog(QtWidgets.QDialog):
    """Dialog to create or edit a recurring transaction."""

    def __init__(
        self,
        codigoempresa: str,
        recorrente: Optional[dict] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.recorrente = recorrente or {}
        self.setWindowTitle("Recorrente")
        self.setModal(True)

        self._build_ui()
        self._populate_fields()

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Descrição
        self.edit_descricao = QtWidgets.QLineEdit()
        layout.addRow("Descrição:", self.edit_descricao)

        # Categoria
        self.combo_categoria = QtWidgets.QComboBox()
        self.combo_categoria.setEditable(False)
        self.combo_categoria.addItem("-- Selecione --", None)
        for cat in models.listar_categorias(self.codigoempresa):
            self.combo_categoria.addItem(cat["nome"], cat["id"])
        layout.addRow("Categoria:", self.combo_categoria)

        # Centro de custo
        self.combo_centro = QtWidgets.QComboBox()
        self.combo_centro.setEditable(False)
        self.combo_centro.addItem("-- Nenhum --", None)
        for cc in models.listar_centros_custo(self.codigoempresa):
            self.combo_centro.addItem(cc["nome"], cc["id"])
        layout.addRow("Centro de Custo:", self.combo_centro)

        # Valor
        self.edit_valor = QtWidgets.QLineEdit()
        layout.addRow("Valor:", self.edit_valor)

        # Frequência
        self.combo_frequencia = QtWidgets.QComboBox()
        self.combo_frequencia.addItems(["Diário", "Semanal", "Quinzenal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"])
        layout.addRow("Frequência:", self.combo_frequencia)

        # Próxima data
        self.date_proxima = QtWidgets.QDateEdit()
        self.date_proxima.setDisplayFormat("dd/MM/yyyy")
        self.date_proxima.setCalendarPopup(True)
        layout.addRow("Próxima data:", self.date_proxima)

        # Data fim
        self.date_fim = QtWidgets.QDateEdit()
        self.date_fim.setDisplayFormat("dd/MM/yyyy")
        self.date_fim.setCalendarPopup(True)
        self.date_fim.setSpecialValueText("Nunca")
        self.date_fim.setDate(QtCore.QDate())
        layout.addRow("Data fim:", self.date_fim)

        # Forma de pagamento
        self.edit_forma = QtWidgets.QLineEdit()
        layout.addRow("Forma de pagamento:", self.edit_forma)

        # Ativo
        self.checkbox_ativo = QtWidgets.QCheckBox("Ativo")
        layout.addRow("Ativo:", self.checkbox_ativo)

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
        r = self.recorrente
        if not r:
            self.checkbox_ativo.setChecked(True)
            return
        self.edit_descricao.setText(r.get("descricao") or "")
        # categoria
        cat_id = r.get("categoria_id")
        if cat_id:
            idx = self.combo_categoria.findData(cat_id)
            if idx >= 0:
                self.combo_categoria.setCurrentIndex(idx)
        # centro
        cc_id = r.get("centro_custo_id")
        if cc_id:
            idx = self.combo_centro.findData(cc_id)
            if idx >= 0:
                self.combo_centro.setCurrentIndex(idx)
        # valor
        val = r.get("valor")
        if val is not None:
            self.edit_valor.setText(f"{val:.2f}")
        # frequência
        freq = r.get("frequencia")
        if freq:
            i = self.combo_frequencia.findText(freq, QtCore.Qt.MatchFlag.MatchFixedString)
            if i >= 0:
                self.combo_frequencia.setCurrentIndex(i)
        # proxima_data
        data_str = r.get("proxima_data")
        if data_str:
            try:
                date = QtCore.QDate.fromString(data_str, "yyyy-MM-dd")
                if date.isValid():
                    self.date_proxima.setDate(date)
            except Exception:
                pass
        # data_fim
        fim_str = r.get("data_fim")
        if fim_str:
            date = QtCore.QDate.fromString(fim_str, "yyyy-MM-dd")
            if date.isValid():
                self.date_fim.setDate(date)
        # forma
        self.edit_forma.setText(r.get("forma_pagamento") or "")
        # ativo
        self.checkbox_ativo.setChecked(bool(r.get("ativo", 1)))

    def _on_accept(self) -> None:
        descricao = self.edit_descricao.text().strip()
        if not descricao:
            QtWidgets.QMessageBox.warning(self, "Erro", "Informe a descrição.")
            return
        cat_id = self.combo_categoria.currentData()
        if cat_id is None:
            QtWidgets.QMessageBox.warning(self, "Erro", "Selecione a categoria.")
            return
        cc_id = self.combo_centro.currentData()
        valor_txt = self.edit_valor.text().replace(",", ".").strip()
        try:
            valor = float(valor_txt)
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Erro", "Valor inválido.")
            return
        frequencia = self.combo_frequencia.currentText()
        proxima_data = self.date_proxima.date().toString("yyyy-MM-dd")
        # Data fim: if no date or invalid (date=0001-01-01), set None
        fim_date = self.date_fim.date()
        data_fim = fim_date.toString("yyyy-MM-dd") if fim_date.isValid() and fim_date != QtCore.QDate() else None
        forma = self.edit_forma.text().strip() or None
        ativo = self.checkbox_ativo.isChecked()
        try:
            if self.recorrente:
                models.editar_recorrente(
                    self.recorrente["id"],
                    descricao,
                    cat_id,
                    cc_id,
                    valor,
                    frequencia,
                    proxima_data,
                    data_fim,
                    forma,
                    ativo,
                )
            else:
                models.criar_recorrente(
                    self.codigoempresa,
                    descricao,
                    cat_id,
                    cc_id,
                    valor,
                    frequencia,
                    proxima_data,
                    data_fim,
                    forma,
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao salvar recorrente:\n{exc}")
            return
        self.accept()


class RecorrentesView(QtWidgets.QWidget):
    """Widget to list and manage recurring transactions."""

    def __init__(self, codigoempresa: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.current_theme: str = "dark"
        self._build_ui()
        self._load_data()

    def set_theme(self, theme: str) -> None:
        """Atualiza o tema atual e recarrega os cartões."""
        if theme not in ("dark", "light"):
            return
        self.current_theme = theme
        # Atualiza cores de título e resumo
        if hasattr(self, "title"):
            self.title.setStyleSheet(
                "font-size: 16px; font-weight: bold; color: {}".format(
                    "#e5e7eb" if theme == "dark" else "#111827"
                )
            )
        if hasattr(self, "lbl_summary"):
            sum_color = "#9ca3af" if theme == "dark" else "#6b7280"
            self.lbl_summary.setStyleSheet(
                f"font-size: 12px; color: {sum_color};"
            )
        self._load_data()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Title
        self.title = QtWidgets.QLabel("Transações Recorrentes")
        self.title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e5e7eb;")
        layout.addWidget(self.title)

        # Summary label for income/expense totals
        self.lbl_summary = QtWidgets.QLabel("")
        self.lbl_summary.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(self.lbl_summary)

        # Área de cartões em scroll
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.scroll_area.setWidget(self.cards_container)
        layout.addWidget(self.scroll_area)

        # Botão global para adicionar recorrente
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setAlignment(QtCore.Qt.AlignRight)
        self.btn_add = QtWidgets.QPushButton("Adicionar")
        btn_layout.addWidget(self.btn_add)
        layout.addLayout(btn_layout)

        # Connect signals
        self.btn_add.clicked.connect(self._on_add)

    def _load_data(self) -> None:
        """Carrega todas as transações recorrentes e exibe como cartões."""
        try:
            recs = models.listar_recorrentes(self.codigoempresa)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao carregar recorrentes:\n{exc}",
            )
            return
        # Totais de receitas e despesas (valores positivos e negativos)
        total_receitas = sum(r.get("valor", 0) for r in recs if r.get("valor", 0) > 0)
        total_despesas = sum(-r.get("valor", 0) for r in recs if r.get("valor", 0) < 0)
        self.lbl_summary.setText(
            f"Receitas: {total_receitas:.2f} | Despesas: {total_despesas:.2f}"
        )
        # Remove cartões existentes
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for r in recs:
            # Definir cores base conforme tema
            if self.current_theme == "light":
                card_bg = "#ffffff"
                header_color = "#111827"
                info_color = "#6b7280"
            else:
                card_bg = "#0f172a"
                header_color = "#e5e7eb"
                info_color = "#9ca3af"
            val = r.get("valor")
            # Outer frame with coloured bar
            outer_frame = QtWidgets.QFrame()
            outer_layout = QtWidgets.QHBoxLayout(outer_frame)
            outer_layout.setContentsMargins(0, 0, 0, 0)
            outer_layout.setSpacing(0)
            bar = QtWidgets.QFrame()
            bar.setFixedWidth(6)
            if val is not None:
                if val > 0:
                    bar_color = "#22c55e"
                elif val < 0:
                    bar_color = "#ef4444"
                else:
                    bar_color = "#6b7280"
            else:
                bar_color = "#6b7280"
            bar.setStyleSheet(
                f"background-color: {bar_color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px;"
            )
            outer_layout.addWidget(bar)
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                f"background-color: {card_bg}; border-radius: 8px; padding: 8px;"
            )
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(4)
            # Cabeçalho: descrição e valor
            header_layout = QtWidgets.QHBoxLayout()
            lbl_desc = QtWidgets.QLabel(r.get("descricao") or "")
            lbl_desc.setStyleSheet(
                f"font-size: 14px; font-weight: bold; color: {header_color};"
            )
            header_layout.addWidget(lbl_desc)
            header_layout.addStretch()
            lbl_val = QtWidgets.QLabel(f"{val:.2f}" if val is not None else "")
            if val is not None:
                if val > 0:
                    val_color = "#22c55e"
                elif val < 0:
                    val_color = "#ef4444"
                else:
                    val_color = header_color
            else:
                val_color = header_color
            lbl_val.setStyleSheet(
                f"color: {val_color}; font-size: 14px; font-weight: bold;"
            )
            header_layout.addWidget(lbl_val)
            card_layout.addLayout(header_layout)
            # Linha info
            info_parts = []
            # categoria
            cat_nome = ""
            if r.get("categoria_id"):
                try:
                    cat = models.buscar_categoria_por_id(r.get("categoria_id"))
                    cat_nome = cat.get("nome") if cat else ""
                except Exception:
                    cat_nome = ""
            if cat_nome:
                info_parts.append(f"Categoria: {cat_nome}")
            # centro de custo
            centro_nome = ""
            if r.get("centro_custo_id"):
                try:
                    centros = models.listar_centros_custo(self.codigoempresa)
                    centro = next((cc for cc in centros if cc["id"] == r.get("centro_custo_id")), None)
                    centro_nome = centro.get("nome") if centro else ""
                except Exception:
                    centro_nome = ""
            if centro_nome:
                info_parts.append(f"Centro: {centro_nome}")
            # frequência
            freq = r.get("frequencia") or ""
            if freq:
                info_parts.append(f"Freq: {freq}")
            # próxima
            prox = r.get("proxima_data") or ""
            if prox:
                info_parts.append(f"Próx: {prox}")
            # fim
            fim = r.get("data_final") or r.get("data_fim") or ""
            if fim:
                info_parts.append(f"Fim: {fim}")
            # forma
            forma = r.get("forma_pagamento") or ""
            if forma:
                info_parts.append(f"Forma: {forma}")
            # ativo
            ativo = r.get("ativo")
            info_parts.append("Ativo" if ativo else "Inativo")
            lbl_info = QtWidgets.QLabel("  |  ".join(info_parts))
            lbl_info.setStyleSheet(
                f"font-size: 11px; color: {info_color};"
            )
            card_layout.addWidget(lbl_info)
            # Botões de ação: Editar e Excluir
            btn_layout = QtWidgets.QHBoxLayout()
            btn_edit = QtWidgets.QPushButton("Editar")
            btn_edit.setFixedWidth(60)
            btn_delete = QtWidgets.QPushButton("Excluir")
            btn_delete.setFixedWidth(60)
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_delete)
            btn_layout.addStretch()
            card_layout.addLayout(btn_layout)
            # Conecta ações
            btn_edit.clicked.connect(lambda _=False, d=r: self._edit_card(d))
            btn_delete.clicked.connect(lambda _=False, d=r: self._delete_card(d))
            # Finaliza outer layout
            outer_layout.addWidget(card)
            # Adiciona cartão
            self.cards_layout.addWidget(outer_frame)
        # Spacer
        self.cards_layout.addStretch()

    def _on_add(self) -> None:
        """Abre a caixa de diálogo para criar uma nova recorrência e recarrega os dados."""
        dlg = RecorrenteDialog(self.codigoempresa, None, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._load_data()

    # ------------------------------------------------------------------
    # Card-based actions
    # ------------------------------------------------------------------
    def _edit_card(self, rec: dict) -> None:
        """Abre a caixa de diálogo para editar uma recorrência específica."""
        dlg = RecorrenteDialog(self.codigoempresa, rec, self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            self._load_data()

    def _delete_card(self, rec: dict) -> None:
        """Solicita confirmação e exclui a recorrência especificada."""
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirmação",
            "Deseja realmente excluir esta transação recorrente?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return
        try:
            models.excluir_recorrente(rec.get("id"))
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Erro ao excluir recorrente:\n{exc}")
            return
        self._load_data()
