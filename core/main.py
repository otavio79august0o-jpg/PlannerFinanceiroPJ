"""
Arquivo principal para iniciar o Planner Empresarial PJ.

Este módulo inicializa a aplicação Qt, exibe a janela de login e,
após autenticação, cria a janela principal (MainWindow) passando
o código da empresa e as informações do usuário logado. O banco de
dados é armazenado no diretório ``data`` conforme configurado em
``core.config``.
"""

import sys
import datetime

from PyQt5.QtWidgets import QApplication, QDialog

from ui.login_window import LoginWindow
from ui.main_window import MainWindow
# Importa ensure_data_dirs a partir do módulo de configuração. Se
# existir um pacote ``core``, tenta importar a partir dele; caso
# contrário, importa diretamente de config.
try:
    from core.config import ensure_data_dirs  # type: ignore
except ImportError:
    from config import ensure_data_dirs  # type: ignore


def main() -> None:
    """Função principal para iniciar a aplicação."""
    # Garante que diretórios de dados existem
    ensure_data_dirs()

    app = QApplication(sys.argv)
    # Exibe a janela de login
    login = LoginWindow()
    ret = login.exec_()
    if ret != QDialog.Accepted:
        # Usuário cancelou o login
        sys.exit(0)
    # Recupera a empresa e usuário
    codigoempresa, usuario = login.get_result()
    if not codigoempresa or not usuario:
        print("Erro: login não forneceu empresa ou usuário.")
        sys.exit(1)
    # Cria e exibe a janela principal
    window = MainWindow(codigoempresa=codigoempresa, usuario=usuario)
    window.show()
    # Executa o loop do Qt
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()