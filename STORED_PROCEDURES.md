# Stored procedures do Simulador SGBD

Documentação detalhada das 5 stored procedures definidas em `procedures.sql`.
Todas leem o `information_schema` do MySQL (o catálogo de metadados) e fazem
apenas `SELECT`: não alteram dados nem usam SQL dinâmico.

## Sumário

1. [Conceitos básicos](#conceitos-básicos)
2. [Visão geral](#visão-geral)
3. [sp_listar_schemas](#1-sp_listar_schemas)
4. [sp_listar_tabelas](#2-sp_listar_tabelas)
5. [sp_colunas_tabela](#3-sp_colunas_tabela)
6. [sp_cardinalidade](#4-sp_cardinalidade)
7. [sp_estrutura_relacionados](#5-sp_estrutura_relacionados)
8. [Como o Python chama as procedures](#como-o-python-chama-as-procedures)
9. [Limitações e observações](#limitações-e-observações)

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
| `KEY_COLUMN_USAGE` | Colunas que fazem parte de chaves (PK, UK e **FK**). Nas FKs, preenche as colunas `REFERENCED_*`. |
| `STATISTICS` | Os índices de cada tabela, um registro por coluna do índice. |

---

## Visão geral

| # | Procedure | Parâmetros | Retorna |
|---|---|---|---|
| 1 | `sp_listar_schemas` | nenhum | Nomes dos bancos |
| 2 | `sp_listar_tabelas` | `p_schema` | Tabelas do schema, com tipo e engine |
| 3 | `sp_colunas_tabela` | `p_schema`, `p_tabela` | Colunas de uma tabela |
| 4 | `sp_cardinalidade` | `p_schema`, `p_tabela` | FKs ligadas à tabela e a cardinalidade de cada uma |
| 5 | `sp_estrutura_relacionados` | `p_schema`, `p_tabela` | Colunas da tabela e de todas as tabelas relacionadas |

Rota HTTP de cada uma em `teste_web.py`:

| Procedure | Rota |
|---|---|
| `sp_listar_schemas` | `/api/schemas` |
| `sp_listar_tabelas` | `/api/tabelas?schema=` |
| `sp_colunas_tabela` | `/api/colunas?schema=&tabela=` |
| `sp_cardinalidade` | `/api/relacionamentos?schema=&tabela=` |
| `sp_estrutura_relacionados` | `/api/estrutura?schema=&tabela=` |

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
estrangeiras. Já o **MyISAM** aceita a sintaxe de FK, mas a ignora. Por isso,
tabelas MyISAM não aparecem com relacionamentos no simulador.

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

**Objetivo:** mostrar a estrutura (colunas) de uma tabela. É usada para a
tabela escolhida e para cada tabela relacionada.

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

## 4. `sp_cardinalidade`

**Objetivo:** listar todas as chaves estrangeiras que envolvem a tabela
escolhida, nos dois sentidos, e classificar cada relacionamento como **1:1**
ou **1:N**. É a procedure central do projeto e a que dá origem aos blocos
coloridos da página.

**Assinatura:** `sp_cardinalidade(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))`

### Ideia central
- A tabela que **contém a FK** fica no **lado N**.
- A tabela **referenciada** fica no **lado 1**.
- Se a coluna da FK for **única**, o relacionamento é **1:1**. Caso contrário, é **1:N**.

### Código

```sql
SELECT CONCAT(k.TABLE_SCHEMA, '.', k.TABLE_NAME)  AS lado_n,
       k.COLUMN_NAME                              AS coluna_n,
       CONCAT(k.REFERENCED_TABLE_SCHEMA, '.', k.REFERENCED_TABLE_NAME) AS lado_1,
       k.REFERENCED_COLUMN_NAME                   AS coluna_1,
       CASE WHEN EXISTS (
                SELECT 1
                FROM information_schema.STATISTICS s
                WHERE s.TABLE_SCHEMA = k.TABLE_SCHEMA
                  AND s.TABLE_NAME = k.TABLE_NAME
                  AND s.NON_UNIQUE = 0
                  AND s.INDEX_NAME IN (
                      SELECT INDEX_NAME FROM information_schema.STATISTICS
                      WHERE TABLE_SCHEMA = k.TABLE_SCHEMA AND TABLE_NAME = k.TABLE_NAME
                      GROUP BY INDEX_NAME HAVING COUNT(*) = 1)
                  AND s.COLUMN_NAME = k.COLUMN_NAME)
            THEN '1:1' ELSE '1:N' END             AS cardinalidade,
       k.CONSTRAINT_NAME                          AS constraint_fk,
       CASE WHEN k.TABLE_SCHEMA = p_schema AND k.TABLE_NAME = p_tabela
            THEN 'a tabela escolhida esta no lado N'
            ELSE 'a tabela escolhida esta no lado 1' END AS posicao
FROM information_schema.KEY_COLUMN_USAGE k
WHERE k.REFERENCED_TABLE_NAME IS NOT NULL
  AND ((k.TABLE_SCHEMA = p_schema AND k.TABLE_NAME = p_tabela)
    OR (k.REFERENCED_TABLE_SCHEMA = p_schema AND k.REFERENCED_TABLE_NAME = p_tabela))
ORDER BY posicao DESC, lado_n, k.CONSTRAINT_NAME, k.ORDINAL_POSITION;
```

### Passo a passo

**1. Localizar as FKs (`FROM` e `WHERE`)**
`KEY_COLUMN_USAGE` guarda todas as colunas que participam de chaves. Quando
`REFERENCED_TABLE_NAME IS NOT NULL`, a linha é uma **FK**. O filtro pega dois grupos:

| Condição | Significado |
|---|---|
| `k.TABLE_* = p_schema/p_tabela` | FKs que **saem** da tabela escolhida (ela é o lado N) |
| `k.REFERENCED_TABLE_* = p_schema/p_tabela` | FKs de outras tabelas que **apontam para** a escolhida (ela é o lado 1) |

**2. Montar os nomes (`CONCAT`)**
`lado_n` e `lado_1` saem no formato `schema.tabela`. O front-end separa esse
texto no primeiro ponto para buscar a estrutura das tabelas relacionadas.

**3. Decidir 1:1 ou 1:N (`CASE WHEN EXISTS`)**
A subconsulta verifica se a coluna da FK é coberta por um índice único de
**uma só coluna**:

- `s.NON_UNIQUE = 0` seleciona apenas índices únicos (inclui a PK).
- A subconsulta interna com `GROUP BY INDEX_NAME HAVING COUNT(*) = 1` mantém só os índices com uma única coluna.
- `s.COLUMN_NAME = k.COLUMN_NAME` exige que o índice seja sobre a própria coluna da FK.
- Se existir, a coluna não repete valores, então cada linha do lado 1 se liga a no máximo uma do lado N: **1:1**. Se não, **1:N**.

**4. Indicar a posição (`CASE` final)**
A coluna `posicao` diz de que lado está a tabela escolhida. O front-end usa
esses dois textos exatos para separar os blocos laranja (lado N) e azul
(lado 1). Alterar a redação aqui quebra a página.

**5. Ordenar**
`ORDER BY posicao DESC` coloca "lado N" antes de "lado 1" (ordem alfabética
decrescente). Depois ordena por tabela, constraint e posição da coluna na FK.

### Saída

| Coluna | Descrição |
|---|---|
| `lado_n` | `schema.tabela` que contém a FK |
| `coluna_n` | Coluna da FK |
| `lado_1` | `schema.tabela` referenciada |
| `coluna_1` | Coluna referenciada (geralmente a PK) |
| `cardinalidade` | `1:1` ou `1:N` |
| `constraint_fk` | Nome da constraint |
| `posicao` | De que lado a tabela escolhida está |

### Exemplo

```sql
CALL sp_cardinalidade('sakila', 'film');
```

| lado_n | coluna_n | lado_1 | coluna_1 | cardinalidade | constraint_fk | posicao |
|---|---|---|---|---|---|---|
| sakila.film | language_id | sakila.language | language_id | 1:N | fk_film_language | a tabela escolhida esta no lado N |
| sakila.film_actor | film_id | sakila.film | film_id | 1:N | fk_film_actor_film | a tabela escolhida esta no lado 1 |

### Observações
- Para uma FK **composta** (várias colunas), cada coluna gera uma linha. Como o índice único tem mais de uma coluna, a procedure a classifica como 1:N.
- Se a coluna da FK for também a PK da tabela (caso típico de tabela de extensão 1:1), ela é detectada como 1:1.
- Auto-relacionamentos (a tabela referencia a si mesma) aparecem como lado N, pela ordem das condições do `CASE`.
- Só FKs reais (InnoDB) são encontradas.

---

## 5. `sp_estrutura_relacionados`

**Objetivo:** devolver, em uma única consulta, as colunas da tabela escolhida
e das tabelas ligadas a ela por FK, em ambos os sentidos, identificando o
papel de cada uma.

**Assinatura:** `sp_estrutura_relacionados(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))`

### Código

```sql
SELECT rel.papel,
       c.TABLE_NAME AS tabela,
       c.ORDINAL_POSITION AS posicao,
       c.COLUMN_NAME AS coluna,
       c.COLUMN_TYPE AS tipo,
       c.IS_NULLABLE AS aceita_nulo,
       c.COLUMN_KEY AS chave,
       c.COLUMN_DEFAULT AS valor_padrao,
       c.EXTRA AS extra
FROM (
    SELECT p_schema AS sch, p_tabela AS tab, 'principal' AS papel

    UNION

    SELECT REFERENCED_TABLE_SCHEMA, REFERENCED_TABLE_NAME, 'referenciada'
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = p_schema
      AND TABLE_NAME = p_tabela
      AND REFERENCED_TABLE_NAME IS NOT NULL

    UNION

    SELECT TABLE_SCHEMA, TABLE_NAME, 'referenciadora'
    FROM information_schema.KEY_COLUMN_USAGE
    WHERE REFERENCED_TABLE_SCHEMA = p_schema
      AND REFERENCED_TABLE_NAME = p_tabela
) AS rel
JOIN information_schema.COLUMNS c
  ON c.TABLE_SCHEMA = rel.sch
 AND c.TABLE_NAME = rel.tab
ORDER BY FIELD(rel.papel, 'principal', 'referenciada', 'referenciadora'),
         c.TABLE_NAME,
         c.ORDINAL_POSITION;
```

### Passo a passo

**1. Subconsulta `rel` com três `SELECT` unidos por `UNION`**
Monta a lista de tabelas envolvidas (`sch`, `tab`) e o papel de cada uma:

| Papel | Origem | Significado |
|---|---|---|
| `principal` | Valor literal dos parâmetros | A tabela escolhida |
| `referenciada` | `REFERENCED_*` das FKs que **saem** da escolhida | Tabelas que a escolhida referencia (lado 1) |
| `referenciadora` | `TABLE_*` das FKs que **chegam** na escolhida | Tabelas que a referenciam (lado N) |

O `UNION` (sem `ALL`) remove duplicatas. Uma tabela com duas FKs para a mesma
referenciada aparece uma só vez.

**2. `JOIN` com `COLUMNS`**
Para cada par (`sch`, `tab`) de `rel`, traz todas as colunas da tabela.

**3. Ordenação personalizada**
`FIELD(rel.papel, ...)` devolve a posição do papel na lista. Isso impõe a ordem
principal → referenciada → referenciadora, o que não seria possível com a
ordem alfabética.

### Saída

| Coluna | Descrição |
|---|---|
| `papel` | `principal`, `referenciada` ou `referenciadora` |
| `tabela` | Nome da tabela |
| `posicao`, `coluna`, `tipo`, `aceita_nulo`, `chave`, `valor_padrao`, `extra` | Mesmos campos da `sp_colunas_tabela` |

### Exemplo

```sql
CALL sp_estrutura_relacionados('sakila', 'film');
```

| papel | tabela | posicao | coluna | tipo | ... |
|---|---|---|---|---|---|
| principal | film | 1 | film_id | smallint unsigned | ... |
| principal | film | 2 | title | varchar(128) | ... |
| referenciada | language | 1 | language_id | tinyint unsigned | ... |
| referenciadora | film_actor | 1 | actor_id | smallint unsigned | ... |

### Observações
- O `UNION` entre um valor literal e consultas ao `information_schema` pode gerar avisos de collation em alguns servidores. Em ambientes com collations diferentes, vale conferir.
- A página atual **não usa** essa procedure: ela monta a mesma informação com várias chamadas a `sp_colunas_tabela`. A rota `/api/estrutura` existe, mas fica sem consumidor no front-end.

---

## Como o Python chama as procedures

A função `chamar` em `teste_web.py` é o único ponto de contato com o banco:

```python
def chamar(procedure, *args):
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
| FKs compostas | Cada coluna gera uma linha e a cardinalidade é sempre 1:N. |
| Engines sem FK | Tabelas MyISAM não têm relacionamentos detectáveis. |
| Rota sem uso | `/api/estrutura` (`sp_estrutura_relacionados`) não é consumida pela página. |
| Acoplamento | O front-end depende dos textos exatos da coluna `posicao` de `sp_cardinalidade`. |
