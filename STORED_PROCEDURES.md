# Stored procedures do Simulador SGBD

Documentação detalhada das 3 stored procedures definidas em `procedures.sql`.
Todas leem o `information_schema` do MySQL (o catálogo de metadados) e fazem
apenas `SELECT`: não alteram dados nem usam SQL dinâmico.

## Sumário

1. [Conceitos básicos](#conceitos-básicos)
2. [Visão geral](#visão-geral)
3. [sp_listar_schemas](#1-sp_listar_schemas)
4. [sp_listar_tabelas](#2-sp_listar_tabelas)
5. [sp_colunas_tabela](#3-sp_colunas_tabela)
6. [Como o Python chama as procedures](#como-o-python-chama-as-procedures)
7. [Limitações e observações](#limitações-e-observações)

---

## Conceitos básicos

### Stored procedure
Bloco de SQL guardado no servidor e executado com `CALL nome(argumentos)`.
A lógica fica no banco; a aplicação (Python) só pede o resultado.

### Estrutura do script

| Trecho | Função |
|---|---|
| `CREATE DATABASE IF NOT EXISTS bd_simulator;` | Cria o banco que guarda as procedures, sem erro se ele já existir. |
| `USE bd_simulator;` | As procedures são criadas dentro desse banco. |
| `DELIMITER $$` | Troca o terminador de comando de `;` para `$$`. Sem isso, o `;` dentro do `BEGIN...END` encerraria o `CREATE PROCEDURE` antes da hora. |
| `DROP PROCEDURE IF EXISTS ...` | Remove a versão anterior antes de recriar, o que torna o script **idempotente** (pode ser executado várias vezes). |
| `DELIMITER ;` | Restaura o terminador padrão no fim do script. |

### Parâmetros `IN`
Os parâmetros são só de entrada. O prefixo `p_` (`p_schema`, `p_tabela`) evita
conflito com nomes de colunas do `information_schema`, que têm nomes parecidos
(`TABLE_SCHEMA`, `TABLE_NAME`).

### Tabelas do `information_schema` usadas

| Tabela | O que descreve |
|---|---|
| `SCHEMATA` | Um registro por banco de dados (schema). |
| `TABLES` | Um registro por tabela ou view, com tipo e engine. |
| `COLUMNS` | Um registro por coluna de cada tabela. |

---

## Visão geral

| # | Procedure | Parâmetros | Retorna |
|---|---|---|---|
| 1 | `sp_listar_schemas` | nenhum | Nomes dos bancos |
| 2 | `sp_listar_tabelas` | `p_schema` | Tabelas do schema, com tipo e engine |
| 3 | `sp_colunas_tabela` | `p_schema`, `p_tabela` | Colunas de uma tabela |

Rota HTTP de cada uma em `teste_web.py`:

| Procedure | Rota |
|---|---|
| `sp_listar_schemas` | `/api/schemas` |
| `sp_listar_tabelas` | `/api/tabelas?schema=` |
| `sp_colunas_tabela` | `/api/colunas?schema=&tabela=` |

---

## 1. `sp_listar_schemas`

**Objetivo:** listar todos os bancos de dados do servidor. Alimenta o
`<select>` de escolha do schema na página.

**Assinatura:** `sp_listar_schemas()`

### Código

```sql
SELECT SCHEMA_NAME AS banco_nome
FROM information_schema.SCHEMATA
ORDER BY SCHEMA_NAME;
```

### Como funciona
1. Lê `information_schema.SCHEMATA`, que tem um registro por schema.
2. Renomeia `SCHEMA_NAME` para `banco_nome`.
3. Ordena em ordem alfabética.

### Saída

| Coluna | Descrição |
|---|---|
| `banco_nome` | Nome do schema |

### Exemplo

```sql
CALL sp_listar_schemas();
```

| banco_nome |
|---|
| bd_simulator |
| information_schema |
| mysql |
| sakila |

### Observação
Aparecem também os schemas do sistema (`information_schema`, `mysql`,
`performance_schema`, `sys`), pois não há filtro.

---

## 2. `sp_listar_tabelas`

**Objetivo:** listar as tabelas e views de um schema. Alimenta a lista de
itens expansíveis (`<details>`) da página.

**Assinatura:** `sp_listar_tabelas(IN p_schema VARCHAR(64))`

### Código

```sql
SELECT t.TABLE_NAME AS tabela,
       t.TABLE_TYPE AS tipo,
       t.ENGINE AS engine
FROM information_schema.TABLES t
WHERE t.TABLE_SCHEMA = p_schema
ORDER BY t.TABLE_NAME;
```

### Como funciona
1. Lê `information_schema.TABLES` filtrando pelo schema recebido.
2. Ordena pelo nome da tabela.

O nome do engine já vem na própria coluna `TABLES.ENGINE`, por isso não é
necessário consultar `information_schema.ENGINES`.

### Saída

| Coluna | Descrição |
|---|---|
| `tabela` | Nome da tabela ou view |
| `tipo` | `BASE TABLE`, `VIEW` ou `SYSTEM VIEW` |
| `engine` | Mecanismo de armazenamento (`InnoDB`, `MyISAM`, ...). É `NULL` para views. |

### O que é engine
É o componente do MySQL que decide como os dados da tabela são gravados,
indexados e protegidos. O **InnoDB** (padrão) suporta transações e chaves
estrangeiras. Já o **MyISAM** aceita a sintaxe de FK, mas a ignora.

### Exemplo

```sql
CALL sp_listar_tabelas('sakila');
```

| tabela | tipo | engine |
|---|---|---|
| actor | BASE TABLE | InnoDB |
| actor_info | VIEW | NULL |
| film | BASE TABLE | InnoDB |

### Por que não há `JOIN` com `ENGINES`
Uma versão anterior fazia `LEFT JOIN information_schema.ENGINES e ON e.ENGINE = t.ENGINE`.
Ele foi removido por ser desnecessário:

1. **Nenhuma coluna de `ENGINES` era selecionada.** O `SELECT` usa só `t.TABLE_NAME`, `t.TABLE_TYPE` e `t.ENGINE`, todas de `TABLES`.
2. **A informação já está em `TABLES.ENGINE`.** O join só buscaria o mesmo nome de engine de novo.
3. **Não filtrava nada.** Por ser `LEFT JOIN`, todas as linhas de `TABLES` permanecem, inclusive as views, cujo engine é `NULL`.
4. **Não duplicava linhas.** Cada engine aparece uma única vez em `ENGINES`, então o join não multiplicava resultados.

Ou seja, o resultado era idêntico com ou sem o join. Mantê-lo só custaria uma
leitura extra do catálogo e deixaria a procedure mais confusa.

---

## 3. `sp_colunas_tabela`

**Objetivo:** mostrar a estrutura (colunas) de uma tabela. É chamada quando o
usuário expande uma tabela na página.

**Assinatura:** `sp_colunas_tabela(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))`

### Código

```sql
SELECT ORDINAL_POSITION AS posicao,
       COLUMN_NAME AS coluna,
       COLUMN_TYPE AS tipo,
       IS_NULLABLE AS aceita_nulo,
       COLUMN_KEY AS chave,
       COLUMN_DEFAULT AS valor_padrao,
       EXTRA AS extra
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = p_schema
  AND TABLE_NAME = p_tabela
ORDER BY ORDINAL_POSITION;
```

### Como funciona
1. Lê `information_schema.COLUMNS`, com um registro por coluna.
2. Filtra pelo schema e pela tabela recebidos.
3. Ordena pela posição original da coluna na tabela.

### Saída

| Coluna | Descrição |
|---|---|
| `posicao` | Posição da coluna na tabela (começa em 1) |
| `coluna` | Nome da coluna |
| `tipo` | Tipo completo, com tamanho (`varchar(45)`, `smallint unsigned`) |
| `aceita_nulo` | `YES` ou `NO` |
| `chave` | `PRI` (chave primária), `UNI` (única), `MUL` (índice não único, comum em FKs) ou vazio |
| `valor_padrao` | Valor `DEFAULT`, ou `NULL` |
| `extra` | Informações extras, como `auto_increment` |

### Exemplo

```sql
CALL sp_colunas_tabela('sakila', 'film');
```

| posicao | coluna | tipo | aceita_nulo | chave | valor_padrao | extra |
|---|---|---|---|---|---|---|
| 1 | film_id | smallint unsigned | NO | PRI | NULL | auto_increment |
| 2 | title | varchar(128) | NO | MUL | NULL | |
| 4 | release_year | year | YES | | NULL | |

---

## Como o Python chama as procedures

A função `call` em `teste_web.py` é o único ponto de contato com o banco:

```python
def call(procedure, *args):
    conn = mysql.connector.connect(**CONFIG)
    try:
        cursor = conn.cursor()
        colunas, linhas = [], []
        cursor.callproc(procedure, args)
        for resultado in cursor.stored_results():
            dados = resultado.fetchall()
            if not colunas:
                colunas = [d[0] for d in resultado.description]
                linhas = dados
        cursor.close()
        return colunas, linhas
    finally:
        conn.close()
```

1. Abre uma conexão com os dados do `.env`.
2. `callproc` executa o `CALL` passando os parâmetros como valores (não por concatenação de texto).
3. `stored_results()` percorre os conjuntos de resultado devolvidos pela procedure.
4. Os nomes das colunas vêm de `resultado.description`.
5. Fecha a conexão no `finally`, mesmo em caso de erro.

---

## Limitações e observações

| Ponto | Detalhe |
|---|---|
| Segurança | Só `SELECT`; parâmetros passados como valores, sem concatenação. Isso protege contra SQL injection. |
| Permissões | O usuário da aplicação só precisa de `EXECUTE` nas procedures. |
| Escopo do `information_schema` | O MySQL só mostra objetos sobre os quais o usuário tem algum privilégio. |
