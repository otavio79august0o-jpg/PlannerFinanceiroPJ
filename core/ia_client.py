
from typing import Dict, List

try:
    from .logs import log_atividade  # type: ignore
except ImportError:
    from logs import log_atividade  # type: ignore


def classificar_transacoes_em_lote(
    codigoempresa: str,
    itens: List[dict],
) -> Dict[int, dict]:
    resultados: Dict[int, dict] = {}
    for item in itens:
        valor = float(item.get("valor") or 0.0)
        sugestao_categoria = "Receita não classificada" if valor > 0 else "Despesa não classificada"
        descricao_tratada = (item.get("descricao_extrato") or "").strip() or "Lançamento sem descrição"
        resultados[item["id_staging"]] = {
            "categoria_nome": sugestao_categoria,
            "descricao_tratada": descricao_tratada,
            "centro_custo_nome": None,
        }

    if itens:
        log_atividade(
            codigoempresa=codigoempresa,
            acao="ia_classificacao_lote_stub",
            detalhes=f"{len(itens)} transações enviadas para IA (stub)",
            origem_modulo="ia_client",
        )
    return resultados
