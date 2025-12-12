
from typing import List, Optional
# Importa o módulo de banco de dados; suporta execução em pacote ou em nível de projeto.
try:
    from . import db  # type: ignore
    from .db import get_connection  # type: ignore
except ImportError:
    import db  # type: ignore
    from db import get_connection  # type: ignore

def listar_empresas_por_usuario_senha(username: str, senha_hash: str):
    sql = """
        SELECT
            u.codigoempresa,
            e.razao_social,
            e.nome_fantasia
        FROM usuarios u
        JOIN empresas e
          ON e.codigoempresa = u.codigoempresa
        WHERE u.username = ?
          AND u.senha_hash = ?
          AND u.ativo = 1
          AND e.ativo = 1
        ORDER BY e.nome_fantasia, e.razao_social, u.codigoempresa
    """
    return db.fetchall_dict(sql, (username, senha_hash))


def get_empresa_por_codigo(codigoempresa: str) -> Optional[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM empresas WHERE codigoempresa = ? AND ativo = 1",
            (codigoempresa,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def criar_empresa(
    codigoempresa: str,
    razao_social: str,
    nome_fantasia: str,
    cnpj: str,
    regime_tributario: str,
    area_atuacao: str,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO empresas
                (codigoempresa, razao_social, nome_fantasia, cnpj, regime_tributario, area_atuacao, ativo)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (codigoempresa, razao_social, nome_fantasia, cnpj, regime_tributario, area_atuacao),
        )
        conn.commit()
    finally:
        conn.close()


def autenticar_usuario(codigoempresa: str, username: str, senha_hash: str) -> Optional[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM usuarios
            WHERE codigoempresa = ? AND username = ? AND senha_hash = ? AND ativo = 1
            """,
            (codigoempresa, username, senha_hash),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def criar_usuario(
    codigoempresa: str,
    username: str,
    senha_hash: str,
    perfil: str = "empresario",
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO usuarios (codigoempresa, username, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (codigoempresa, username, senha_hash, perfil),
        )
        conn.commit()
    finally:
        conn.close()


def listar_contas(codigoempresa: str) -> List[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM contas WHERE codigoempresa = ? AND ativa = 1 ORDER BY nome_conta",
            (codigoempresa,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def listar_transacoes_simples(codigoempresa: str, limite: int = 100) -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT t.*, c.nome_conta
            FROM transactions t
            JOIN contas c ON c.id = t.conta_id
            WHERE t.codigoempresa = ?
            ORDER BY t.data_lancamento DESC, t.id DESC
            LIMIT ?
            """,
            (codigoempresa, limite),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

# endregion

# region Funções avançadas de transações

def listar_transacoes_filtradas(
    codigoempresa: str,
    busca: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limite: int = 200,
) -> list[dict]:
    """
    Lista transações com filtros opcionais de busca e datas.

    A busca é feita sobre as descrições do extrato e tratada, bem
    como sobre o nome do favorecido (caso implementado). Os parâmetros
    ``data_inicio`` e ``data_fim`` devem ser strings no formato
    ``YYYY-MM-DD``. Quando ambos são fornecidos, o intervalo é
    inclusivo.

    A consulta retorna dados adicionais: nome da conta, nome da
    categoria e nome do centro de custo, quando existirem.

    Args:
        codigoempresa: Identificador da empresa.
        busca: Texto para busca parcial em descrições.
        data_inicio: Data mínima de lançamento (inclusive).
        data_fim: Data máxima de lançamento (inclusive).
        limite: Número máximo de resultados.

    Returns:
        Lista de dicionários com os campos da transação e colunas
        associadas.
    """
    conn = get_connection()
    try:
        sql = [
            "SELECT t.*, c.nome_conta, cat.nome AS categoria_nome, cc.nome AS centro_nome",
            "FROM transactions t",
            "JOIN contas c ON c.id = t.conta_id",
            "LEFT JOIN categories cat ON cat.id = t.categoria_id",
            "LEFT JOIN centros_custo cc ON cc.id = t.centro_custo_id",
            "WHERE t.codigoempresa = ?",
        ]
        params: list = [codigoempresa]
        if busca:
            sql.append(
                "AND (t.descricao_extrato LIKE ? OR t.descricao_tratada LIKE ?)"
            )
            like = f"%{busca}%"
            params.extend([like, like])
        if data_inicio:
            sql.append("AND DATE(t.data_lancamento) >= DATE(?)")
            params.append(data_inicio)
        if data_fim:
            sql.append("AND DATE(t.data_lancamento) <= DATE(?)")
            params.append(data_fim)
        sql.append(
            "ORDER BY t.data_lancamento DESC, t.id DESC"
        )
        sql.append("LIMIT ?")
        params.append(limite)
        query = "\n".join(sql)
        cur = conn.execute(query, tuple(params))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def criar_transacao(
    codigoempresa: str,
    conta_id: int,
    data_lancamento: str,
    descricao_extrato: str,
    descricao_tratada: Optional[str],
    valor: Optional[float],
    categoria_id: Optional[int],
    centro_custo_id: Optional[int],
    forma_pagamento: Optional[str],
) -> None:
    """
    Cria um novo registro em transactions. A data de competência é
    definida igual à data de lançamento. O tipo de movimento é
    determinado pelo sinal do valor: positivo => crédito; negativo
    => débito.

    Args:
        codigoempresa: Código da empresa.
        conta_id: ID da conta associada.
        data_lancamento: Data do lançamento (YYYY-MM-DD).
        descricao_extrato: Descrição original do extrato.
        descricao_tratada: Descrição tratada/opcional.
        valor: Valor da transação (positivo para crédito,
            negativo para débito).
        categoria_id: ID da categoria (ou None).
        centro_custo_id: ID do centro de custo (ou None).
        forma_pagamento: Texto indicando forma de pagamento.
    """
    conn = get_connection()
    try:
        tipo_movimento = None
        if valor is not None:
            tipo_movimento = "credito" if valor > 0 else "debito"
        conn.execute(
            """
            INSERT INTO transactions (
                codigoempresa,
                conta_id,
                data_lancamento,
                data_competencia,
                descricao_extrato,
                descricao_tratada,
                categoria_id,
                centro_custo_id,
                valor,
                tipo_movimento,
                forma_pagamento,
                conciliado,
                created_at,
                updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, DATETIME('now'), DATETIME('now')
            )
            """,
            (
                codigoempresa,
                conta_id,
                data_lancamento,
                data_lancamento,
                descricao_extrato,
                descricao_tratada,
                categoria_id,
                centro_custo_id,
                valor,
                tipo_movimento,
                forma_pagamento,
            ),
        )
        conn.commit()
    finally:
        conn.close()

def excluir_transacao(transacao_id: int) -> None:
    """Exclui uma transação pelo seu ID."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM transactions WHERE id = ?", (transacao_id,))
        conn.commit()
    finally:
        conn.close()


# region Funções de contas

def criar_conta(
    codigoempresa: str,
    nome_conta: str,
    tipo_conta: str,
    banco: Optional[str] = None,
    agencia: Optional[str] = None,
    numero: Optional[str] = None,
    moeda: str = "BRL",
    limite_cheque_especial: float = 0,
    limite_cartao: float = 0,
    dia_vencimento_fatura: Optional[int] = None,
) -> None:
    """
    Cria uma nova conta financeira para a empresa.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO contas (
                codigoempresa, nome_conta, tipo_conta,
                banco, agencia, numero, moeda,
                limite_cheque_especial, limite_cartao, dia_vencimento_fatura, ativa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                codigoempresa,
                nome_conta,
                tipo_conta,
                banco,
                agencia,
                numero,
                moeda or "BRL",
                limite_cheque_especial or 0,
                limite_cartao or 0,
                dia_vencimento_fatura,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def editar_conta(
    conta_id: int,
    nome_conta: str,
    tipo_conta: str,
    banco: Optional[str] = None,
    agencia: Optional[str] = None,
    numero: Optional[str] = None,
    moeda: str = "BRL",
    limite_cheque_especial: float = 0,
    limite_cartao: float = 0,
    dia_vencimento_fatura: Optional[int] = None,
) -> None:
    """
    Atualiza os dados de uma conta existente.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE contas
            SET nome_conta             = ?,
                tipo_conta             = ?,
                banco                  = ?,
                agencia                = ?,
                numero                 = ?,
                moeda                  = ?,
                limite_cheque_especial = ?,
                limite_cartao          = ?,
                dia_vencimento_fatura  = ?
            WHERE id = ?
            """,
            (
                nome_conta,
                tipo_conta,
                banco,
                agencia,
                numero,
                moeda or "BRL",
                limite_cheque_especial or 0,
                limite_cartao or 0,
                dia_vencimento_fatura,
                conta_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def excluir_conta(conta_id: int) -> None:
    """
    Remove uma conta do banco de dados.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM contas WHERE id = ?", (conta_id,))
        conn.commit()
    finally:
        conn.close()

# endregion

# region Funções de categorias

def listar_categorias(codigoempresa: str) -> List[dict]:
    """
    Retorna todas as categorias cadastradas para a empresa.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM categories
            WHERE codigoempresa = ?
            ORDER BY tipo, grupo, nome
            """,
            (codigoempresa,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def criar_categoria(
    codigoempresa: str,
    nome: str,
    tipo: str,
    grupo: Optional[str] = None,
    ordem_exibicao: Optional[int] = None,
) -> None:
    """
    Insere uma nova categoria no banco de dados.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO categories (
                codigoempresa, nome, tipo, grupo, ordem_exibicao
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                codigoempresa,
                nome,
                tipo,
                grupo,
                ordem_exibicao if ordem_exibicao is not None else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def editar_categoria(
    categoria_id: int,
    nome: str,
    tipo: str,
    grupo: Optional[str] = None,
    ordem_exibicao: Optional[int] = None,
) -> None:
    """
    Atualiza os dados de uma categoria existente.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE categories
            SET nome           = ?,
                tipo           = ?,
                grupo          = ?,
                ordem_exibicao = ?
            WHERE id = ?
            """,
            (
                nome,
                tipo,
                grupo,
                ordem_exibicao if ordem_exibicao is not None else 0,
                categoria_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def excluir_categoria(categoria_id: int) -> None:
    """
    Exclui uma categoria do banco de dados.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM categories WHERE id = ?", (categoria_id,))
        conn.commit()
    finally:
        conn.close()

# endregion

# region Funções de orçamentos

def listar_orcamentos(codigoempresa: str) -> List[dict]:
    """
    Lista todos os orçamentos cadastrados para a empresa, incluindo o nome da categoria.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT o.id,
                   o.categoria_id,
                   o.mes_ano,
                   o.valor,
                   c.nome AS categoria_nome
            FROM orcamentos o
            JOIN categories c ON c.id = o.categoria_id
            WHERE o.codigoempresa = ?
            ORDER BY o.mes_ano DESC, c.nome
            """,
            (codigoempresa,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def criar_orcamento(
    codigoempresa: str,
    categoria_id: int,
    mes_ano: str,
    valor: float,
) -> None:
    """
    Cria um novo orçamento mensal para uma categoria. Se já existir, substitui.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO orcamentos (
                codigoempresa, categoria_id, mes_ano, valor
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(codigoempresa, categoria_id, mes_ano)
            DO UPDATE SET valor=excluded.valor
            """,
            (codigoempresa, categoria_id, mes_ano, valor),
        )
        conn.commit()
    finally:
        conn.close()


def editar_orcamento(
    orcamento_id: int,
    categoria_id: int,
    mes_ano: str,
    valor: float,
) -> None:
    """
    Atualiza um orçamento existente.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE orcamentos
            SET categoria_id = ?,
                mes_ano      = ?,
                valor        = ?
            WHERE id = ?
            """,
            (categoria_id, mes_ano, valor, orcamento_id),
        )
        conn.commit()
    finally:
        conn.close()


def excluir_orcamento(orcamento_id: int) -> None:
    """
    Remove um orçamento do banco de dados.
    """
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM orcamentos WHERE id = ?",
            (orcamento_id,),
        )
        conn.commit()
    finally:
        conn.close()

# endregion

# region Funções de centros de custo

def listar_centros_custo(codigoempresa: str) -> List[dict]:
    """
    Retorna todos os centros de custo ativos da empresa.

    Args:
        codigoempresa: código da empresa.

    Returns:
        Lista de dicionários com os campos da tabela ``centros_custo``.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM centros_custo
            WHERE codigoempresa = ? AND ativo = 1
            ORDER BY nome
            """,
            (codigoempresa,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

# endregion

# region Funções utilitárias

def buscar_categoria_por_id(categoria_id: int) -> Optional[dict]:
    """
    Busca uma categoria pelo seu ID.

    Args:
        categoria_id: identificador da categoria.

    Returns:
        Um dicionário com os campos da categoria ou None se não encontrada.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT * FROM categories WHERE id = ?",
            (categoria_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def editar_transacao(
    transacao_id: int,
    descricao_tratada: Optional[str] = None,
    categoria_id: Optional[int] = None,
    centro_custo_id: Optional[int] = None,
    valor: Optional[float] = None,
    forma_pagamento: Optional[str] = None,
    data_competencia: Optional[str] = None,
) -> None:
    """
    Atualiza campos de uma transação existente.

    Somente os campos fornecidos serão atualizados. O campo
    ``updated_at`` é sempre atualizado para a data/hora corrente.

    Args:
        transacao_id: ID da transação a ser atualizada.
        descricao_tratada: descrição tratada (pode ser None para não alterar).
        categoria_id: nova categoria (ou None).
        centro_custo_id: novo centro de custo (ou None).
        valor: novo valor (ou None).
        forma_pagamento: nova forma de pagamento (ou None).
        data_competencia: nova data de competência (YYYY-MM-DD) ou None.
    """
    conn = get_connection()
    try:
        campos: list[str] = []
        params: list = []
        if descricao_tratada is not None:
            campos.append("descricao_tratada = ?")
            params.append(descricao_tratada)
        if categoria_id is not None:
            campos.append("categoria_id = ?")
            params.append(categoria_id)
        if centro_custo_id is not None:
            campos.append("centro_custo_id = ?")
            params.append(centro_custo_id)
        if valor is not None:
            campos.append("valor = ?")
            params.append(valor)
        if forma_pagamento is not None:
            campos.append("forma_pagamento = ?")
            params.append(forma_pagamento)
        if data_competencia is not None:
            campos.append("data_competencia = ?")
            params.append(data_competencia)
        # always update updated_at
        campos.append("updated_at = DATETIME('now')")
        sql = "UPDATE transactions SET " + ", ".join(campos) + " WHERE id = ?"
        params.append(transacao_id)
        conn.execute(sql, tuple(params))
        conn.commit()
    finally:
        conn.close()

# endregion

# region Funções de recorrentes

def listar_recorrentes(codigoempresa: str) -> List[dict]:
    """
    Lista todas as transações recorrentes de uma empresa.

    Args:
        codigoempresa: código da empresa.

    Returns:
        Uma lista de dicionários com os campos da tabela ``recorrentes``.
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM recorrentes
            WHERE codigoempresa = ?
            ORDER BY proxima_data ASC, id ASC
            """,
            (codigoempresa,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def criar_recorrente(
    codigoempresa: str,
    descricao: str,
    categoria_id: Optional[int],
    centro_custo_id: Optional[int],
    valor: float,
    frequencia: str,
    proxima_data: str,
    data_final: Optional[str],
    forma_pagamento: Optional[str],
    ativo: bool = True,
) -> None:
    """
    Cria uma nova transação recorrente.

    Args:
        codigoempresa: código da empresa.
        descricao: descrição da recorrência.
        categoria_id: ID da categoria associada.
        centro_custo_id: ID do centro de custo associado.
        valor: valor da transação.
        frequencia: frequência da recorrência (ex.: 'Mensal').
        proxima_data: data da próxima ocorrência (YYYY-MM-DD).
        data_final: data final (YYYY-MM-DD) ou None.
        forma_pagamento: forma de pagamento ou None.
        ativo: indica se a recorrência está ativa.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO recorrentes (
                codigoempresa, descricao, categoria_id, centro_custo_id,
                valor, frequencia, proxima_data, data_final, forma_pagamento, ativo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                codigoempresa,
                descricao,
                categoria_id,
                centro_custo_id,
                valor,
                frequencia,
                proxima_data,
                data_final,
                forma_pagamento,
                1 if ativo else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def editar_recorrente(
    recorrente_id: int,
    descricao: str,
    categoria_id: Optional[int],
    centro_custo_id: Optional[int],
    valor: float,
    frequencia: str,
    proxima_data: str,
    data_final: Optional[str],
    forma_pagamento: Optional[str],
    ativo: bool,
) -> None:
    """
    Atualiza uma transação recorrente existente.

    Args:
        recorrente_id: ID da recorrência.
        descricao: nova descrição.
        categoria_id: ID da categoria.
        centro_custo_id: ID do centro de custo.
        valor: novo valor.
        frequencia: nova frequência.
        proxima_data: nova próxima data.
        data_final: nova data final ou None.
        forma_pagamento: nova forma de pagamento ou None.
        ativo: indica se está ativa.
    """
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE recorrentes
            SET descricao       = ?,
                categoria_id    = ?,
                centro_custo_id = ?,
                valor           = ?,
                frequencia      = ?,
                proxima_data    = ?,
                data_final      = ?,
                forma_pagamento = ?,
                ativo           = ?
            WHERE id = ?
            """,
            (
                descricao,
                categoria_id,
                centro_custo_id,
                valor,
                frequencia,
                proxima_data,
                data_final,
                forma_pagamento,
                1 if ativo else 0,
                recorrente_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def excluir_recorrente(recorrente_id: int) -> None:
    """
    Exclui uma recorrência do banco de dados.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM recorrentes WHERE id = ?", (recorrente_id,))
        conn.commit()
    finally:
        conn.close()

# endregion

# endregion
