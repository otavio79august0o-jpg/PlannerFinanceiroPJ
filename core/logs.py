
import logging
from typing import Optional

try:
    from .db import get_connection  # type: ignore
    from .utils import now_iso  # type: ignore
except ImportError:
    from db import get_connection  # type: ignore
    from utils import now_iso  # type: ignore

LOGGER = logging.getLogger("planner_empresarial_pj")


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


def log_atividade(
    codigoempresa: str,
    acao: str,
    detalhes: str = "",
    origem_modulo: str = "",
    usuario_id: Optional[int] = None,
) -> None:
    LOGGER.info("%s - %s", acao, detalhes)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO logs_atividade
                (codigoempresa, usuario_id, data_hora, acao, detalhes, origem_modulo)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (codigoempresa, usuario_id, now_iso(), acao, detalhes, origem_modulo),
        )
        conn.commit()
    finally:
        conn.close()
