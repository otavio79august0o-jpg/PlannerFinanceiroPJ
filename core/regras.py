
import re
from typing import Optional, Tuple

try:
    from .db import get_connection  # type: ignore
except ImportError:
    from db import get_connection  # type: ignore


def _match_pattern(valor: str, tipo_match: str, padrao: str) -> bool:
    valor_norm = (valor or "").upper()
    padrao_norm = (padrao or "").upper()

    if tipo_match == "contem":
        return padrao_norm in valor_norm
    if tipo_match == "igual":
        return valor_norm == padrao_norm
    if tipo_match == "prefixo":
        return valor_norm.startswith(padrao_norm)
    if tipo_match == "sufixo":
        return valor_norm.endswith(padrao_norm)
    if tipo_match == "regex":
        try:
            return re.search(padrao, valor or "") is not None
        except re.error:
            return False
    return False


def aplicar_regras_auto_categorizacao(
    codigoempresa: str,
    descricao_extrato: str,
    favorecido_texto: str | None,
    forma_pagamento_detectada: str | None,
) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM regras_auto_categorizacao
            WHERE codigoempresa = ? AND ativo = 1
            ORDER BY prioridade DESC
            """,
            (codigoempresa,),
        )
        regras = cur.fetchall()
    finally:
        conn.close()

    campo_map = {
        "descricao_extrato": descricao_extrato or "",
        "favorecido_texto": favorecido_texto or "",
        "forma_pagamento": forma_pagamento_detectada or "",
    }

    for regra in regras:
        campo_alvo = regra["campo_alvo"]
        tipo_match = regra["tipo_match"]
        padrao = regra["padrao_texto"]

        valor_referencia = campo_map.get(campo_alvo, "")
        if not valor_referencia:
            continue

        if _match_pattern(valor_referencia, tipo_match, padrao):
            return (
                regra["categoria_id"],
                regra["centro_custo_id"],
                regra["descricao_sugerida"],
                regra["forma_pagamento_fixa"],
            )

    return None, None, None, None
