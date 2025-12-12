
import sqlite3

# Importa funções de configuração do banco
try:
    # Quando ``db.py`` for usado como parte de um pacote (ex.: core.db)
    from .config import get_db_path, ensure_data_dirs
except ImportError:
    # Quando ``db.py`` for executado no topo do projeto
    from config import get_db_path, ensure_data_dirs

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS empresas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa     TEXT NOT NULL UNIQUE,
    razao_social      TEXT,
    nome_fantasia     TEXT,
    cnpj              TEXT,
    regime_tributario TEXT,
    area_atuacao      TEXT,
    ativo             INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa TEXT NOT NULL,
    username      TEXT NOT NULL,
    senha_hash    TEXT NOT NULL,
    perfil        TEXT DEFAULT 'empresario',
    ativo         INTEGER NOT NULL DEFAULT 1,
    UNIQUE (codigoempresa, username)
);

CREATE TABLE IF NOT EXISTS categories (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa  TEXT NOT NULL,
    nome           TEXT NOT NULL,
    tipo           TEXT NOT NULL,
    grupo          TEXT,
    ordem_exibicao INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS centros_custo (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa TEXT NOT NULL,
    nome          TEXT NOT NULL,
    tipo_setor    TEXT,
    ativo         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS contas (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa          TEXT NOT NULL,
    nome_conta             TEXT NOT NULL,
    tipo_conta             TEXT NOT NULL,
    banco                  TEXT,
    agencia                TEXT,
    numero                 TEXT,
    moeda                  TEXT DEFAULT 'BRL',
    limite_cheque_especial REAL DEFAULT 0,
    limite_cartao          REAL DEFAULT 0,
    dia_vencimento_fatura  INTEGER,
    ativa                  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS favorecidos (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa          TEXT NOT NULL,
    nome                   TEXT NOT NULL,
    tipo                   TEXT,
    categoria_padrao_id    INTEGER,
    centro_custo_padrao_id INTEGER,
    descricao_padrao       TEXT,
    observacoes            TEXT,
    ativo                  INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (categoria_padrao_id)    REFERENCES categories(id),
    FOREIGN KEY (centro_custo_padrao_id) REFERENCES centros_custo(id)
);

CREATE TABLE IF NOT EXISTS importacoes_extrato (
    id                               INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa                    TEXT NOT NULL,
    conta_id                         INTEGER NOT NULL,
    tipo_arquivo                     TEXT NOT NULL,
    nome_arquivo                     TEXT NOT NULL,
    data_importacao                  TEXT NOT NULL,
    periodo_inicio                   TEXT,
    periodo_fim                      TEXT,
    total_no_arquivo                 INTEGER DEFAULT 0,
    total_deduplicados               INTEGER DEFAULT 0,
    total_importados                 INTEGER DEFAULT 0,
    total_desconhecidos_pos_importacao INTEGER DEFAULT 0,
    usuario_id                       INTEGER,
    FOREIGN KEY (conta_id)  REFERENCES contas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS staging_transacoes_import (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa             TEXT NOT NULL,
    importacao_id             INTEGER NOT NULL,
    conta_id                  INTEGER NOT NULL,
    data_lancamento           TEXT,
    descricao_extrato         TEXT,
    favorecido_texto          TEXT,
    valor                     REAL NOT NULL,
    forma_pagamento_detectada TEXT,
    categoria_sugerida_id     INTEGER,
    centro_custo_sugerido_id  INTEGER,
    origem_sugestao           TEXT,
    status_classificacao      TEXT DEFAULT 'desconhecido',
    observacoes               TEXT,
    FOREIGN KEY (importacao_id)            REFERENCES importacoes_extrato(id) ON DELETE CASCADE,
    FOREIGN KEY (conta_id)                 REFERENCES contas(id),
    FOREIGN KEY (categoria_sugerida_id)    REFERENCES categories(id),
    FOREIGN KEY (centro_custo_sugerido_id) REFERENCES centros_custo(id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa    TEXT NOT NULL,
    conta_id         INTEGER NOT NULL,
    data_lancamento  TEXT NOT NULL,
    data_competencia TEXT,
    descricao_extrato TEXT,
    descricao_tratada TEXT,
    favorecido_id    INTEGER,
    tipo_movimento   TEXT NOT NULL,
    valor            REAL NOT NULL,
    categoria_id     INTEGER,
    centro_custo_id  INTEGER,
    forma_pagamento  TEXT,
    id_importacao    INTEGER,
    hash_unico       TEXT,
    conciliado       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    FOREIGN KEY (conta_id)       REFERENCES contas(id),
    FOREIGN KEY (favorecido_id)  REFERENCES favorecidos(id),
    FOREIGN KEY (categoria_id)   REFERENCES categories(id),
    FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
    FOREIGN KEY (id_importacao)  REFERENCES importacoes_extrato(id)
);

CREATE TABLE IF NOT EXISTS regras_auto_categorizacao (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa        TEXT NOT NULL,
    campo_alvo           TEXT NOT NULL,
    tipo_match           TEXT NOT NULL,
    padrao_texto         TEXT NOT NULL,
    categoria_id         INTEGER,
    centro_custo_id      INTEGER,
    descricao_sugerida   TEXT,
    forma_pagamento_fixa TEXT,
    prioridade           INTEGER DEFAULT 0,
    ativo                INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (categoria_id)    REFERENCES categories(id),
    FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id)
);

CREATE TABLE IF NOT EXISTS tributos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa   TEXT NOT NULL,
    tipo_tributo    TEXT NOT NULL,
    competencia     TEXT NOT NULL,
    valor_previsto  REAL,
    valor_pago      REAL,
    data_vencimento TEXT,
    data_pagamento  TEXT,
    status          TEXT,
    observacoes     TEXT
);

CREATE TABLE IF NOT EXISTS folha_setores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa       TEXT NOT NULL,
    competencia         TEXT NOT NULL,
    centro_custo_id     INTEGER NOT NULL,
    total_salarios      REAL DEFAULT 0,
    total_encargos      REAL DEFAULT 0,
    total_beneficios    REAL DEFAULT 0,
    total_terceirizados REAL DEFAULT 0,
    total_geral         REAL DEFAULT 0,
    origem_info         TEXT,
    observacoes         TEXT,
    FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id)
);

CREATE TABLE IF NOT EXISTS projetos (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa      TEXT NOT NULL,
    nome               TEXT NOT NULL,
    tipo               TEXT,
    data_inicio_prevista TEXT,
    data_fim_prevista  TEXT,
    orcamento_previsto REAL,
    valor_realizado    REAL,
    status             TEXT,
    responsavel        TEXT,
    observacoes        TEXT
);

CREATE TABLE IF NOT EXISTS ativos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa   TEXT NOT NULL,
    nome            TEXT NOT NULL,
    tipo            TEXT,
    data_aquisicao  TEXT,
    valor_aquisicao REAL,
    vida_util_meses INTEGER,
    valor_residual  REAL,
    centro_custo_id INTEGER,
    situacao        TEXT,
    observacoes     TEXT,
    FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id)
);

-- Tabela de orçamentos mensais por categoria
CREATE TABLE IF NOT EXISTS orcamentos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa TEXT NOT NULL,
    categoria_id  INTEGER NOT NULL,
    mes_ano       TEXT NOT NULL,       -- formato 'YYYY-MM'
    valor         REAL NOT NULL,
    UNIQUE (codigoempresa, categoria_id, mes_ano),
    FOREIGN KEY (categoria_id) REFERENCES categories(id)
);

-- Tabela de lançamentos recorrentes
CREATE TABLE IF NOT EXISTS recorrentes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa     TEXT NOT NULL,
    descricao         TEXT NOT NULL,
    categoria_id      INTEGER,
    centro_custo_id   INTEGER,
    valor             REAL NOT NULL,
    frequencia        TEXT NOT NULL,   -- ex: 'mensal', 'semanal', 'diario'
    proxima_data      TEXT NOT NULL,
    data_final        TEXT,
    forma_pagamento   TEXT,
    ativo             INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (categoria_id)    REFERENCES categories(id),
    FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id)
);

CREATE TABLE IF NOT EXISTS logs_atividade (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa TEXT NOT NULL,
    usuario_id    INTEGER,
    data_hora     TEXT NOT NULL,
    acao          TEXT NOT NULL,
    detalhes      TEXT,
    origem_modulo TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS ia_logs (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    codigoempresa          TEXT NOT NULL,
    tipo                   TEXT NOT NULL,
    qtd_transacoes_enviadas INTEGER DEFAULT 0,
    tokens_input           INTEGER DEFAULT 0,
    tokens_output          INTEGER DEFAULT 0,
    custo_estimado         REAL DEFAULT 0,
    data_hora              TEXT NOT NULL,
    sucesso                INTEGER NOT NULL DEFAULT 1,
    mensagem_erro          TEXT
);
"""


def get_connection() -> sqlite3.Connection:
    """Abre uma conexão SQLite configurada para o banco de dados da aplicação.

    Antes de abrir a conexão, garante que os diretórios de dados e arquivos
    auxiliares existam chamando ``ensure_data_dirs()``. Também ativa o
    suporte a chaves estrangeiras e define o retorno das linhas como
    dicionários para facilitar o uso na camada de modelos.

    Returns:
        Uma instância de ``sqlite3.Connection`` configurada.
    """
    # Garante que a pasta data e subpastas existam
    try:
        ensure_data_dirs()
    except Exception:
        # Se a função não estiver disponível, simplesmente prossegue
        pass
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    # Retornar linhas como dict
    conn.row_factory = sqlite3.Row
    # Ativar chaves estrangeiras
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()

def fetchall_dict(sql: str, params=()):
    """
    Executa um SELECT e retorna uma lista de dicionários.
    Não depende de row_factory, monta o dict com base em cur.description.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        resultado = []
        for r in rows:
            resultado.append(dict(zip(cols, r)))
        return resultado
    finally:
        conn.close()


def fetchone_dict(sql: str, params=()):
    """
    Executa um SELECT e retorna um único dicionário (ou None).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description] if cur.description else []
        return dict(zip(cols, row))
    finally:
        conn.close()
