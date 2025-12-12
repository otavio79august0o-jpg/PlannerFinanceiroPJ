
"""
Configuração e utilidades do Planner Empresarial PJ.

Este módulo centraliza caminhos de diretórios e configurações globais. O
arquivo de banco de dados fica armazenado na pasta ``data`` na raiz do
projeto para evitar misturar dados com o código‑fonte. Pastas de logs e
exportações também são criadas dentro de ``data``.

Para garantir que a estrutura de diretórios exista, chame
``ensure_data_dirs()`` antes de abrir o banco de dados.
"""

from pathlib import Path

# Nome e versão do aplicativo
APP_NAME = "Planner Empresarial PJ"
APP_VERSION = "0.2.0"

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent

# Diretório de dados onde o banco e demais pastas serão armazenados
DATA_DIR = BASE_DIR / "data"

# Nome do arquivo de banco de dados SQLite
DB_FILENAME = "planner_empresarial_pj.db"

# Diretórios auxiliares para logs e exportações dentro de DATA_DIR
LOGS_DIR = DATA_DIR / "logs"
EXPORTS_DIR = DATA_DIR / "exports"


def get_db_path() -> Path:
    """Retorna o caminho absoluto para o arquivo de banco de dados.

    O caminho aponta para ``DATA_DIR / DB_FILENAME``. Caso a pasta de dados
    não exista ainda, ela será criada em ``ensure_data_dirs``.
    """
    return DATA_DIR / DB_FILENAME


def ensure_data_dirs() -> None:
    """Garante que os diretórios de dados, logs e exportações existam.

    Cria ``DATA_DIR``, ``LOGS_DIR`` e ``EXPORTS_DIR`` se ainda não existirem.
    É seguro chamar esta função múltiplas vezes.
    """
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    EXPORTS_DIR.mkdir(exist_ok=True)
