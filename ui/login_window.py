import hashlib
import re
import unicodedata
from typing import Optional, List, Dict

import requests
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QFormLayout,
    QSpacerItem,
    QSizePolicy,
    QShortcut,
    QComboBox,
)

from core import db, models


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def gerar_codigoempresa_slug(texto: str, fallback: str) -> str:
    """
    Gera um código interno sem espaços, sem acentos e só com [A-Z0-9_].
    Ex.: 'Alfa Transportes & Logística' -> 'ALFA_TRANSPORTES_LOGISTICA'
    """
    base = (texto or "").strip() or (fallback or "").strip()
    if not base:
        return ""

    base = base.upper()

    # remover acentos
    base = unicodedata.normalize("NFKD", base)
    base = "".join(c for c in base if not unicodedata.combining(c))

    # qualquer coisa que não seja A-Z ou 0-9 vira "_"
    base = re.sub(r"[^A-Z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")

    if len(base) > 20:
        base = base[:20]

    return base or fallback


class EmpresaEscolhaDialog(QDialog):
    """Dialog para escolher uma empresa quando o usuário tem acesso a várias."""

    def __init__(self, empresas: List[Dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecione a empresa")
        self.setModal(True)
        self.resize(460, 180)
        self.setMinimumSize(460, 180)

        self._codigoempresa: Optional[str] = None
        self.empresas = empresas

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        label = QLabel("Esse usuário possui acesso a mais de uma empresa.\n"
                       "Selecione em qual empresa deseja entrar:")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.combo = QComboBox()
        for emp in self.empresas:
            cod = emp.get("codigoempresa") or ""
            razao = emp.get("razao_social") or ""
            fantasia = emp.get("nome_fantasia") or ""
            if fantasia and razao:
                texto = f"{fantasia} ({razao}) — [{cod}]"
            elif fantasia:
                texto = f"{fantasia} — [{cod}]"
            elif razao:
                texto = f"{razao} — [{cod}]"
            else:
                texto = cod
            self.combo.addItem(texto, cod)
        layout.addWidget(self.combo)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton("Entrar")

        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        layout.addLayout(btn_row)

    def _on_ok(self):
        idx = self.combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Atenção", "Selecione uma empresa.")
            return
        self._codigoempresa = self.combo.itemData(idx)
        self.accept()

    def get_codigoempresa(self) -> Optional[str]:
        return self._codigoempresa


class NovaEmpresaDialog(QDialog):
    """Dialog único para cadastrar empresa + usuário, com consulta na API publica.cnpj.ws."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nova empresa e usuário")
        self.setModal(True)

        # janela maior e redimensionável
        self.resize(680, 440)
        self.setMinimumSize(680, 440)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Cadastro de empresa")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 13pt; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Informe o CNPJ bruto (apenas números). "
            "Os dados podem ser buscados na API pública."
        )
        subtitle.setProperty("secondary", True)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignJustify)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.edit_codigoempresa = QLineEdit()
        self.edit_codigoempresa.setPlaceholderText("Identificador interno (ex.: ALFA_TRANSPORTES)")
        form.addRow("Código da empresa:", self.edit_codigoempresa)

        cnpj_row = QHBoxLayout()
        self.edit_cnpj = QLineEdit()
        self.edit_cnpj.setPlaceholderText("00.000.000/0000-00")
        self.edit_cnpj.setInputMask("##.###.###/####-##")
        btn_buscar = QPushButton("Buscar CNPJ na API")
        btn_buscar.clicked.connect(self._on_buscar_cnpj)
        cnpj_row.addWidget(self.edit_cnpj, 1)
        cnpj_row.addWidget(btn_buscar)
        form.addRow("CNPJ:", cnpj_row)

        self.edit_razao = QLineEdit()
        self.edit_razao.setPlaceholderText("Razão social")
        form.addRow("Razão social:", self.edit_razao)

        self.edit_fantasia = QLineEdit()
        self.edit_fantasia.setPlaceholderText("Nome fantasia")
        form.addRow("Nome fantasia:", self.edit_fantasia)

        self.edit_regime = QLineEdit()
        self.edit_regime.setPlaceholderText("Simples Nacional, Presumido, Real, MEI...")
        form.addRow("Regime tributário:", self.edit_regime)

        self.edit_area = QLineEdit()
        self.edit_area.setPlaceholderText("Ex.: Transporte rodoviário de cargas, Clínica médica...")
        form.addRow("Área de atuação:", self.edit_area)

        layout.addLayout(form)

        # Usuário de acesso
        user_form = QFormLayout()
        user_form.setLabelAlignment(Qt.AlignLeft)
        user_form.setHorizontalSpacing(10)
        user_form.setVerticalSpacing(8)

        self.edit_usuario = QLineEdit()
        self.edit_usuario.setPlaceholderText("Usuário de acesso")
        user_form.addRow("Usuário:", self.edit_usuario)

        self.edit_senha = QLineEdit()
        self.edit_senha.setPlaceholderText("Senha de acesso")
        self.edit_senha.setEchoMode(QLineEdit.Password)
        user_form.addRow("Senha:", self.edit_senha)

        layout.addLayout(user_form)

        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self._on_salvar)

        btn_row.addWidget(btn_cancelar)
        btn_row.addWidget(btn_salvar)

        layout.addLayout(btn_row)

    def _cnpj_digits(self) -> str:
        texto = self.edit_cnpj.text()
        return re.sub(r"\D", "", texto or "")

    def _on_buscar_cnpj(self):
        cnpj_digits = self._cnpj_digits()
        if len(cnpj_digits) != 14:
            QMessageBox.warning(self, "Atenção", "Informe um CNPJ válido (14 dígitos).")
            return

        url = f"https://publica.cnpj.ws/cnpj/{cnpj_digits}"
        try:
            resp = requests.get(url, timeout=10)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro",
                f"Falha ao consultar a API publica.cnpj.ws:\n{exc}",
            )
            return

        if resp.status_code != 200:
            QMessageBox.warning(
                self,
                "Atenção",
                f"CNPJ não encontrado ou erro na API (status {resp.status_code}).",
            )
            return

        try:
            data = resp.json()
        except Exception:
            QMessageBox.warning(self, "Atenção", "Resposta da API em formato inesperado.")
            return

        razao = data.get("razao_social") or ""
        estab = data.get("estabelecimento") or {}
        fantasia = estab.get("nome_fantasia") or ""

        if razao and not self.edit_razao.text().strip():
            self.edit_razao.setText(razao)
        if fantasia and not self.edit_fantasia.text().strip():
            self.edit_fantasia.setText(fantasia)

        # Área de atuação pela atividade principal, se existir
        atividade_principal = estab.get("atividade_principal") or {}
        descricao_atividade = atividade_principal.get("descricao") or ""
        if descricao_atividade and not self.edit_area.text().strip():
            self.edit_area.setText(descricao_atividade)

        # Sugerir códigoempresa se vazio (slug sem espaços)
        if not self.edit_codigoempresa.text().strip():
            sugestao = gerar_codigoempresa_slug(
                fantasia or razao,
                fallback=cnpj_digits,
            )
            self.edit_codigoempresa.setText(sugestao)

    def _on_salvar(self):
        if not self.edit_codigoempresa.text().strip():
            QMessageBox.warning(self, "Atenção", "Informe o código interno da empresa.")
            return
        if len(self._cnpj_digits()) != 14:
            QMessageBox.warning(self, "Atenção", "Informe um CNPJ válido (14 dígitos).")
            return
        if not self.edit_razao.text().strip():
            QMessageBox.warning(self, "Atenção", "Informe a razão social.")
            return
        if not self.edit_usuario.text().strip():
            QMessageBox.warning(self, "Atenção", "Informe o usuário de acesso.")
            return
        if not self.edit_senha.text():
            QMessageBox.warning(self, "Atenção", "Informe a senha de acesso.")
            return

        self.accept()

    def get_dados(self) -> dict:
        return {
            "codigoempresa": self.edit_codigoempresa.text().strip(),
            "cnpj": self._cnpj_digits(),
            "razao_social": self.edit_razao.text().strip(),
            "nome_fantasia": self.edit_fantasia.text().strip(),
            "regime_tributario": self.edit_regime.text().strip(),
            "area_atuacao": self.edit_area.text().strip(),
            "username": self.edit_usuario.text().strip(),
            "senha": self.edit_senha.text(),
        }


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login - Planner Empresarial PJ")
        self.setModal(True)

        self.resize(520, 320)
        self.setMinimumSize(520, 320)

        self._codigoempresa: Optional[str] = None
        self._usuario: Optional[dict] = None

        db.init_db()
        self._build_ui()
        self._setup_shortcuts()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Planner Empresarial PJ")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16pt; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Informe usuário e senha. O código da empresa é opcional.\n"
            "Se não for informado, serão listadas as empresas vinculadas a esse login."
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setProperty("secondary", True)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignJustify)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.edit_empresa = QLineEdit()
        self.edit_empresa.setPlaceholderText("Ex.: ALFA_TRANSPORTES (opcional)")
        form.addRow("Código da empresa:", self.edit_empresa)

        self.edit_usuario = QLineEdit()
        self.edit_usuario.setPlaceholderText("Usuário")
        form.addRow("Usuário:", self.edit_usuario)

        self.edit_senha = QLineEdit()
        self.edit_senha.setPlaceholderText("Senha")
        self.edit_senha.setEchoMode(QLineEdit.Password)
        form.addRow("Senha:", self.edit_senha)

        layout.addLayout(form)

        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_criar = QPushButton("Criar empresa/usuário (Shift+Enter)")
        self.btn_criar.clicked.connect(self._on_criar)

        self.btn_login = QPushButton("Entrar (Enter)")
        self.btn_login.clicked.connect(self._on_login)
        self.btn_login.setDefault(True)
        self.btn_login.setAutoDefault(True)
        self.btn_criar.setAutoDefault(False)

        btn_row.addWidget(self.btn_criar)
        btn_row.addWidget(self.btn_login)

        layout.addLayout(btn_row)

    def _setup_shortcuts(self):
        # Enter já é login via botão padrão
        shortcut_criar = QShortcut(QKeySequence("Shift+Return"), self)
        shortcut_criar.activated.connect(self._on_criar)

    def _on_login(self):
        codigoempresa = self.edit_empresa.text().strip()
        username = self.edit_usuario.text().strip()
        senha = self.edit_senha.text()

        if not username or not senha:
            QMessageBox.warning(self, "Atenção", "Informe usuário e senha.")
            return

        senha_hash = hash_senha(senha)

        # Se o código da empresa foi informado, login direto como antes
        if codigoempresa:
            user = models.autenticar_usuario(codigoempresa, username, senha_hash)
            if not user:
                QMessageBox.critical(
                    self,
                    "Erro",
                    "Usuário ou senha inválidos, ou empresa inexistente.",
                )
                return

            self._codigoempresa = codigoempresa
            self._usuario = user
            self.accept()
            return

        # Sem código de empresa: procurar empresas ligadas a esse usuário/senha
        empresas = models.listar_empresas_por_usuario_senha(username, senha_hash)
        if not empresas:
            QMessageBox.critical(
                self,
                "Erro",
                "Usuário e senha não encontrados em nenhuma empresa.",
            )
            return

        if len(empresas) == 1:
            codigoempresa = empresas[0]["codigoempresa"]
        else:
            dlg = EmpresaEscolhaDialog(empresas, self)
            if dlg.exec_() != QDialog.Accepted:
                return
            codigoempresa = dlg.get_codigoempresa()
            if not codigoempresa:
                return

        user = models.autenticar_usuario(codigoempresa, username, senha_hash)
        if not user:
            QMessageBox.critical(
                self,
                "Erro",
                "Falha ao autenticar usuário na empresa selecionada.",
            )
            return

        self._codigoempresa = codigoempresa
        self._usuario = user
        self.accept()

    def _on_criar(self):
        dlg = NovaEmpresaDialog(self)
        if dlg.exec_() != QDialog.Accepted:
            return

        dados = dlg.get_dados()
        try:
            models.criar_empresa(
                dados["codigoempresa"],
                dados["razao_social"],
                dados["nome_fantasia"],
                dados["cnpj"],
                dados["regime_tributario"],
                dados["area_atuacao"],
            )
            models.criar_usuario(
                dados["codigoempresa"],
                dados["username"],
                hash_senha(dados["senha"]),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Erro ao criar empresa/usuário:\n{exc}")
            return

        QMessageBox.information(
            self,
            "Sucesso",
            "Empresa e usuário criados. Agora você pode fazer o login.",
        )
        self.edit_empresa.setText(dados["codigoempresa"])
        self.edit_usuario.setText(dados["username"])
        self.edit_senha.setText("")

    def get_result(self):
        return self._codigoempresa, self._usuario
