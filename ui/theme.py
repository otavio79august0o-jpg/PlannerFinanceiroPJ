from pathlib import Path
from PyQt5.QtWidgets import QApplication
from core.config import BASE_DIR

# Fallback QSS definitions in case theme files cannot be loaded.
# These strings are simplified versions of the dark and light themes used
# in the original MF Financier. They ensure that even se o sistema não
# encontrar os arquivos ``dark.qss`` ou ``light.qss``, um tema
# consistente ainda será aplicado.
DARK_FALLBACK = """
/* Tema escuro padrão */
QWidget {
    background-color: #020617;
    color: #e5e7eb;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QFrame#TopBar {
    background-color: #020617;
    border-bottom: 1px solid #1e293b;
}

QFrame#Sidebar {
    background-color: #020617;
    border-right: 1px solid #1e2937;
}

QPushButton {
    background-color: #0f172a;
    color: #e5e7eb;
    border-radius: 8px;
    padding: 6px 10px;
    border: 1px solid #1f2937;
}
QPushButton:hover {
    background-color: #111827;
}
QPushButton:pressed {
    background-color: #1f2937;
}

QLineEdit, QComboBox, QSpinBox, QDateEdit {
    background-color: #020617;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #2563eb;
    selection-color: #f9fafb;
}

QTableWidget {
    background-color: #020617;
    gridline-color: #273549;
    border-radius: 10px;
    border: 1px solid #1e293b;
}

QHeaderView::section {
    background-color: #0b1120;
    color: #e5e7eb;
    padding: 6px 4px;
    border: none;
    border-bottom: 1px solid #1f2937;
}

QDialog {
    background-color: #020617;
    border-radius: 12px;
}

/* Customize list widgets in the sidebar for dark theme */
QListWidget {
    background-color: #020617;
    color: #e5e7eb;
    border: none;
}
QListWidget::item {
    padding: 10px 14px;
}
QListWidget::item:selected {
    background-color: #0f172a;
    color: #ffffff;
}

"""

LIGHT_FALLBACK = """
/* Tema claro padrão */
QWidget {
    background-color: #f9fafb;
    color: #111827;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QFrame#TopBar {
    background-color: #f3f4f6;
    border-bottom: 1px solid #d1d5db;
}

QFrame#Sidebar {
    background-color: #f9fafb;
    border-right: 1px solid #d1d5db;
}

QPushButton {
    background-color: #ffffff;
    color: #111827;
    border-radius: 8px;
    padding: 6px 10px;
    border: 1px solid #d1d5db;
}
QPushButton:hover {
    background-color: #f3f4f6;
}
QPushButton:pressed {
    background-color: #e5e7eb;
}

QLineEdit, QComboBox, QSpinBox, QDateEdit {
    background-color: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 4px 6px;
    selection-background-color: #2563eb;
    selection-color: #f9fafb;
}

QTableWidget {
    background-color: #ffffff;
    gridline-color: #e5e7eb;
    border-radius: 10px;
    border: 1px solid #e5e7eb;
}

QHeaderView::section {
    background-color: #f3f4f6;
    color: #111827;
    padding: 6px 4px;
    border: none;
    border-bottom: 1px solid #e5e7eb;
}

QDialog {
    background-color: #f9fafb;
    border-radius: 12px;
}

/* Customize list widgets in the sidebar for light theme */
QListWidget {
    background-color: #f9fafb;
    color: #111827;
    border: none;
}
QListWidget::item {
    padding: 10px 14px;
}
QListWidget::item:selected {
    background-color: #e5e7eb;
    color: #111827;
}
"""


def _load_qss(filename: str) -> str:
    """
    Carrega o conteúdo de um arquivo QSS.

    Este utilitário tenta localizar o arquivo de estilo em diversos
    diretórios potenciais. Como o projeto pode ser extraído em
    estruturas diferentes (por exemplo, com ``core`` e ``resources`` no
    mesmo nível ou dentro de uma pasta ``planner``), não podemos
    depender de um único caminho.

    A ordem de busca é a seguinte:

    1. ``BASE_DIR / 'resources'`` — recursos ao lado do pacote core.
    2. ``BASE_DIR.parent / 'resources'`` — recursos na raiz do projeto.
    3. ``BASE_DIR.parent.parent / 'resources'`` — caso o pacote esteja
       aninhado em uma subpasta (como ``planner``).
    4. ``cwd / 'resources'`` — recursos relativos ao diretório de
       execução atual.

    Args:
        filename: nome do arquivo QSS (por exemplo, ``"dark.qss"``).

    Returns:
        Conteúdo do QSS encontrado ou uma string vazia se nenhum
        arquivo válido for localizado.
    """
    from pathlib import Path

    # Lista de diretórios para procurar o QSS
    candidate_dirs = [
        BASE_DIR / "resources",
        BASE_DIR.parent / "resources",
        BASE_DIR.parent.parent / "resources",
        Path.cwd() / "resources",
    ]
    for dir_path in candidate_dirs:
        qss_path = dir_path / filename
        if qss_path.exists():
            try:
                return qss_path.read_text(encoding="utf-8")
            except Exception:
                # Continue tentando outras pastas se a leitura falhar
                pass
    return ""


def apply_theme(app: QApplication, theme: str = "dark") -> None:
    if theme == "light":
        qss = _load_qss("light.qss")
        if not qss:
            qss = LIGHT_FALLBACK
    else:
        qss = _load_qss("dark.qss")
        if not qss:
            qss = DARK_FALLBACK
    app.setStyleSheet(qss)
