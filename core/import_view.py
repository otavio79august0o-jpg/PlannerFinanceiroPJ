
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDialog,
)

try:
    from core import importacao, models  # type: ignore
    from core.db import get_connection  # type: ignore
    from core.ia_client import classificar_transacoes_em_lote  # type: ignore
except ImportError:
    # Fallback se o pacote core não existir
    import importacao  # type: ignore
    import models  # type: ignore
    from db import get_connection  # type: ignore
    from ia_client import classificar_transacoes_em_lote  # type: ignore


class ImportView(QWidget):
    def __init__(self, codigoempresa: str, usuario: dict, parent=None):
        super().__init__(parent)
        self.codigoempresa = codigoempresa
        self.usuario = usuario
        self.contas = models.listar_contas(codigoempresa)
        self.importacao_id = None

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)

        lbl_conta = QLabel("Conta:")
        self.combo_conta = QComboBox()
        for c in self.contas:
            self.combo_conta.addItem(f"{c['id']} - {c['nome_conta']}", c["id"])

        btn_arquivo = QPushButton("Selecionar extrato (OFX/CSV)")
        btn_arquivo.clicked.connect(self._selecionar_arquivo)

        top.addWidget(lbl_conta)
        top.addWidget(self.combo_conta, 1)
        top.addWidget(btn_arquivo)

        layout.addLayout(top)

        info = QLabel(
            "Antes de tentar categorizar manualmente, lembre-se que na janela de transações\n"
            "existe a configuração de auto-categorização via IA."
        )
        info.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(info)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Data", "Descrição", "Favorecido", "Valor", "Forma pagamento", "Categoria", "Origem"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        btn_ia = QPushButton("Sugerir categorias via IA (desconhecidos)")
        btn_ia.clicked.connect(self._usar_ia)

        btn_confirmar = QPushButton("Confirmar importação")
        btn_confirmar.clicked.connect(self._confirmar_importacao)

        bottom.addWidget(btn_ia)
        bottom.addStretch()
        bottom.addWidget(btn_confirmar)

        layout.addLayout(bottom)

    def _selecionar_arquivo(self):
        if not self.contas:
            QMessageBox.warning(self, "Atenção", "Cadastre ao menos uma conta antes de importar.")
            return

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o extrato",
            "",
            "Extratos (*.ofx *.csv *.pdf);;Todos os arquivos (*.*)",
        )
        if not filename:
            return

        conta_id = self.combo_conta.currentData()
        if conta_id is None:
            QMessageBox.warning(self, "Atenção", "Selecione uma conta.")
            return

        try:
            self.importacao_id = importacao.importar_arquivo_e_criar_staging(
                codigoempresa=self.codigoempresa,
                conta_id=int(conta_id),
                usuario_id=self.usuario.get("id"),
                arquivo=Path(filename),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Falha ao importar arquivo:\n{exc}")
            return

        self._carregar_staging()

    def _carregar_staging(self):
        self.table.setRowCount(0)

        if not self.importacao_id:
            return

        conn = get_connection()
        try:
            cur = conn.execute(
                """
                SELECT s.*, c.nome AS categoria_nome
                FROM staging_transacoes_import s
                LEFT JOIN categories c ON c.id = s.categoria_sugerida_id
                WHERE s.codigoempresa = ? AND s.importacao_id = ?
                ORDER BY s.id
                """,
                (self.codigoempresa, self.importacao_id),
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            values = [
                row["id"],
                row["data_lancamento"],
                row["descricao_extrato"],
                row["favorecido_texto"],
                f"{row['valor']:.2f}",
                row["forma_pagamento_detectada"] or "",
                row["categoria_nome"] or "desconhecido",
                row["origem_sugestao"] or "",
            ]
            for col_idx, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                if col_idx == 4:  # valor
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()

    def _usar_ia(self):
        if not self.importacao_id:
            QMessageBox.warning(self, "Atenção", "Nenhuma importação carregada.")
            return

        conn = get_connection()
        try:
            cur = conn.execute(
                """
                SELECT id, descricao_extrato, favorecido_texto, valor
                FROM staging_transacoes_import
                WHERE codigoempresa = ?
                  AND importacao_id = ?
                  AND (status_classificacao = 'desconhecido' OR categoria_sugerida_id IS NULL)
                LIMIT 50
                """,
                (self.codigoempresa, self.importacao_id),
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        itens = [
            {
                "id_staging": row["id"],
                "descricao_extrato": row["descricao_extrato"],
                "favorecido_texto": row["favorecido_texto"],
                "valor": row["valor"],
            }
            for row in rows
        ]

        if not itens:
            QMessageBox.information(self, "Informação", "Não há transações desconhecidas para enviar à IA.")
            return

        sugestoes = classificar_transacoes_em_lote(self.codigoempresa, itens)

        dlg = QDialog(self)
        dlg.setWindowTitle("Sugestões da IA - Conferência")
        dlg.resize(900, 500)
        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(12, 12, 12, 12)
        vbox.setSpacing(8)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(
            ["ID", "Descrição", "Valor", "Categoria sugerida", "Descrição tratada"]
        )
        table.horizontalHeader().setStretchLastSection(True)
        vbox.addWidget(table, 1)

        # primeiro sem sugestão
        for item in itens:
            if item["id_staging"] not in sugestoes:
                row_idx = table.rowCount()
                table.insertRow(row_idx)
                valores = [
                    item["id_staging"],
                    item["descricao_extrato"] or "",
                    f"{item['valor']:.2f}",
                    "desconhecido",
                    "",
                ]
                for col_idx, val in enumerate(valores):
                    it = QTableWidgetItem(str(val))
                    if col_idx == 2:
                        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    table.setItem(row_idx, col_idx, it)

        # depois com sugestão
        for item in itens:
            sug = sugestoes.get(item["id_staging"])
            if not sug:
                continue
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            valores = [
                item["id_staging"],
                item["descricao_extrato"] or "",
                f"{item['valor']:.2f}",
                sug.get("categoria_nome") or "",
                sug.get("descricao_tratada") or "",
            ]
            for col_idx, val in enumerate(valores):
                it = QTableWidgetItem(str(val))
                if col_idx == 2:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setItem(row_idx, col_idx, it)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_aplicar)
        vbox.addLayout(btn_box)

        if dlg.exec_() == QDialog.Accepted:
            conn2 = get_connection()
            try:
                for item_id in sugestoes.keys():
                    conn2.execute(
                        """
                        UPDATE staging_transacoes_import
                        SET origem_sugestao = 'ia', status_classificacao = 'sugerido'
                        WHERE id = ?
                        """,
                        (item_id,),
                    )
                conn2.commit()
            finally:
                conn2.close()
            self._carregar_staging()

    def _confirmar_importacao(self):
        if not self.importacao_id:
            QMessageBox.warning(self, "Atenção", "Nenhuma importação carregada.")
            return

        resp = QMessageBox.question(
            self,
            "Confirmar",
            "Deseja gravar as transações desta importação no banco?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        conn = get_connection()
        try:
            cur = conn.execute(
                """
                SELECT * FROM staging_transacoes_import
                WHERE codigoempresa = ? AND importacao_id = ?
                """,
                (self.codigoempresa, self.importacao_id),
            )
            rows = cur.fetchall()

            total_importados = 0
            for row in rows:
                data = row["data_lancamento"]
                descricao = row["descricao_extrato"]
                valor = row["valor"]
                conta_id = row["conta_id"]

                conn.execute(
                    """
                    INSERT INTO transactions
                        (codigoempresa, conta_id, data_lancamento, data_competencia,
                         descricao_extrato, descricao_tratada, tipo_movimento,
                         valor, categoria_id, centro_custo_id, forma_pagamento,
                         id_importacao, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """,
                    (
                        self.codigoempresa,
                        conta_id,
                        data,
                        data,
                        descricao,
                        descricao,
                        "credito" if valor > 0 else "debito",
                        row["categoria_sugerida_id"],
                        row["centro_custo_sugerido_id"],
                        row["forma_pagamento_detectada"],
                        self.importacao_id,
                    ),
                )
                total_importados += 1

            conn.execute(
                """
                UPDATE importacoes_extrato
                SET total_importados = ?
                WHERE id = ?
                """,
                (total_importados, self.importacao_id),
            )
            conn.commit()
        finally:
            conn.close()

        QMessageBox.information(self, "Sucesso", "Importação confirmada.")
        self.importacao_id = None
        self._carregar_staging()
