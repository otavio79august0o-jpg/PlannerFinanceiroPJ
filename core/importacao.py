
import csv
from pathlib import Path
from typing import List, Tuple

try:
    # Para execução dentro de um pacote (e.g., core.importacao)
    from .db import get_connection  # type: ignore
    from .utils import parse_date, br_to_float, make_hash_unique, now_iso  # type: ignore
    from .regras import aplicar_regras_auto_categorizacao  # type: ignore
except ImportError:
    # Para execução no topo do projeto
    from db import get_connection  # type: ignore
    from utils import parse_date, br_to_float, make_hash_unique, now_iso  # type: ignore
    from regras import aplicar_regras_auto_categorizacao  # type: ignore


def detectar_formato_arquivo(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".ofx":
        return "OFX"
    if ext == ".csv":
        return "CSV"
    if ext == ".pdf":
        return "PDF"
    raise ValueError(f"Formato de arquivo não suportado: {ext}")


def importar_arquivo_e_criar_staging(
    codigoempresa: str,
    conta_id: int,
    usuario_id: int | None,
    arquivo: Path,
) -> int:
    tipo_arquivo = detectar_formato_arquivo(arquivo)
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO importacoes_extrato
                (codigoempresa, conta_id, tipo_arquivo, nome_arquivo, data_importacao)
            VALUES (?, ?, ?, ?, ?)
            """,
            (codigoempresa, conta_id, tipo_arquivo, arquivo.name, now_iso()),
        )
        importacao_id = cur.lastrowid

        if tipo_arquivo == "OFX":
            linhas = _parse_ofx(arquivo)
        elif tipo_arquivo == "CSV":
            linhas = _parse_csv(arquivo)
        else:
            linhas = []

        total_no_arquivo = len(linhas)
        total_deduplicados, total_desconhecidos = _gravar_staging(
            conn, codigoempresa, conta_id, importacao_id, linhas
        )

        conn.execute(
            """
            UPDATE importacoes_extrato
            SET total_no_arquivo = ?, total_deduplicados = ?, total_desconhecidos_pos_importacao = ?
            WHERE id = ?
            """,
            (total_no_arquivo, total_deduplicados, total_desconhecidos, importacao_id),
        )
        conn.commit()
        return importacao_id
    finally:
        conn.close()


def _parse_ofx(path: Path) -> List[dict]:
    content = path.read_text(encoding="latin-1", errors="ignore")
    linhas: List[dict] = []
    current: dict = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("<DTPOSTED>"):
            raw_date = line.replace("<DTPOSTED>", "").strip()
            data = parse_date(raw_date[:8])
            current["data"] = data
        elif line.startswith("<TRNAMT>"):
            raw_valor = line.replace("<TRNAMT>", "").strip()
            try:
                valor = float(raw_valor.replace(",", "."))
            except ValueError:
                valor = 0.0
            current["valor"] = valor
        elif line.startswith("<MEMO>"):
            desc = line.replace("<MEMO>", "").strip()
            current["descricao"] = desc
            current["favorecido"] = desc
        elif line.startswith("<STMTTRN>"):
            current = {}
        elif line.startswith("</STMTTRN>"):
            if current.get("data") and current.get("valor") is not None:
                linhas.append(current.copy())
            current = {}
    return linhas


def _parse_csv(path: Path) -> List[dict]:
    linhas: List[dict] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader, None)
        if header is None:
            return linhas
        h_norm = [h.strip().lower() for h in header]

        def idx(*possiveis: str) -> int | None:
            for p in possiveis:
                if p in h_norm:
                    return h_norm.index(p)
            return None

        idx_data = idx("data", "dt", "date")
        idx_desc = idx("descricao", "descrição", "historico", "histórico", "memo", "description")
        idx_valor = idx("valor", "amount", "vl", "debito", "crédito", "credito")

        for row in reader:
            if not row or all(not c.strip() for c in row):
                continue
            data = parse_date(row[idx_data]) if idx_data is not None else None
            descricao = row[idx_desc].strip() if idx_desc is not None else ""
            raw_valor = row[idx_valor] if idx_valor is not None else "0"
            valor = br_to_float(raw_valor)
            linhas.append(
                {"data": data, "descricao": descricao, "favorecido": descricao, "valor": valor}
            )
    return linhas


def _gravar_staging(
    conn,
    codigoempresa: str,
    conta_id: int,
    importacao_id: int,
    linhas: List[dict],
) -> Tuple[int, int]:
    total_deduplicados = 0
    total_desconhecidos = 0

    for linha in linhas:
        data_str = linha.get("data")
        descricao = linha.get("descricao", "")
        favorecido_txt = linha.get("favorecido", "")
        valor = float(linha.get("valor") or 0.0)

        forma_pag = None
        _ = make_hash_unique(codigoempresa, conta_id, data_str or "", descricao, str(valor))

        cur = conn.execute(
            """
            SELECT 1 FROM transactions
            WHERE codigoempresa = ? AND conta_id = ?
              AND data_lancamento = ? AND valor = ? AND descricao_extrato = ?
            """,
            (codigoempresa, conta_id, data_str, valor, descricao),
        )
        if cur.fetchone():
            total_deduplicados += 1
            continue

        cat_id, cc_id, desc_sug, forma_fixada = aplicar_regras_auto_categorizacao(
            codigoempresa,
            descricao_extrato=descricao,
            favorecido_texto=favorecido_txt,
            forma_pagamento_detectada=forma_pag,
        )

        if forma_fixada:
            forma_pag = forma_fixada

        origem_sugestao = "desconhecido"
        if cat_id or cc_id or desc_sug:
            origem_sugestao = "regra"

        if origem_sugestao == "desconhecido":
            total_desconhecidos += 1

        conn.execute(
            """
            INSERT INTO staging_transacoes_import
                (codigoempresa, importacao_id, conta_id,
                 data_lancamento, descricao_extrato, favorecido_texto,
                 valor, forma_pagamento_detectada,
                 categoria_sugerida_id, centro_custo_sugerido_id,
                 origem_sugestao, status_classificacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigoempresa,
                importacao_id,
                conta_id,
                data_str,
                descricao,
                favorecido_txt,
                valor,
                forma_pag,
                cat_id,
                cc_id,
                origem_sugestao,
                "desconhecido" if origem_sugestao == "desconhecido" else "sugerido",
            ),
        )

    return total_deduplicados, total_desconhecidos
