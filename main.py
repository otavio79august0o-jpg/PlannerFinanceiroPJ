import sys
import traceback
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QDialog
from ui.theme import apply_theme
from ui.login_window import LoginWindow
from ui.main_window import MainWindow  # nova MainWindow (MF Financier PJ)

# Garante criação de diretórios de dados antes de iniciar o app
try:
    from core.config import ensure_data_dirs  # type: ignore
except ImportError:
    from config import ensure_data_dirs  # type: ignore


def excepthook(exc_type, exc_value, exc_tb):
    """
    Hook global de exceções.
    Qualquer erro não tratado vai cair aqui, inclusive erros em slots do Qt.
    """
    traceback.print_exception(exc_type, exc_value, exc_tb)

    # Se você tiver um core.logs, tenta registrar lá também (sem deixar quebrar)
    try:
        from core import logs  # type: ignore
        logger = getattr(logs, "get_logger", None)
        if callable(logger):
            logger(__name__).error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        elif hasattr(logs, "logger"):
            logs.logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        pass


sys.excepthook = excepthook


def main():
    # High DPI
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    apply_theme(app, "dark")

    # Garante que a pasta de dados exista (por exemplo, a pasta ``data``)
    try:
        ensure_data_dirs()
    except Exception:
        # Falha ao criar diretórios não deve impedir a inicialização
        pass

    # Login
    login = LoginWindow()
    ret = login.exec_()
    if ret != QDialog.Accepted:
        sys.exit(0)

    codigoempresa, usuario = login.get_result()
    if not codigoempresa or not usuario:
        print("Login retornou dados vazios (codigoempresa/usuario). Encerrando.")
        sys.exit(1)

    # Cria e exibe a janela principal passando empresa e usuário completos
    # O ``MainWindow`` espera ``codigoempresa`` e ``usuario`` como argumentos
    window = MainWindow(
        codigoempresa=codigoempresa,
        usuario=usuario,
    )
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        excepthook(*sys.exc_info())
        sys.exit(1)
