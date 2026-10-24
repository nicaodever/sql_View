CREATE DATABASE IF NOT EXISTS bd_simulator;
USE bd_simulator;

DELIMITER $$

DROP PROCEDURE IF EXISTS sp_listar_schemas$$
CREATE PROCEDURE `sp_listar_schemas`()
BEGIN
    SELECT SCHEMA_NAME AS banco_nome
    FROM information_schema.SCHEMATA
    ORDER BY SCHEMA_NAME;
END$$

DROP PROCEDURE IF EXISTS sp_listar_tabelas$$
CREATE PROCEDURE `sp_listar_tabelas`(IN p_schema VARCHAR(64))
BEGIN
    SELECT t.TABLE_NAME AS tabela,
           t.TABLE_TYPE AS tipo,
           t.ENGINE AS engine
    FROM information_schema.TABLES t
    LEFT JOIN information_schema.ENGINES e ON e.ENGINE = t.ENGINE
    WHERE t.TABLE_SCHEMA = p_schema
    ORDER BY t.TABLE_NAME;
END$$

DROP PROCEDURE IF EXISTS sp_cardinalidade$$
CREATE PROCEDURE `sp_cardinalidade`(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))
BEGIN
    -- Cada FK gera uma linha: a tabela que contem a FK e o lado N,
    -- a tabela referenciada e o lado 1 (ou 1:1 se a coluna da FK for unica).
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
END$$

DROP PROCEDURE IF EXISTS sp_colunas_tabela$$
CREATE PROCEDURE `sp_colunas_tabela`(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))
BEGIN
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
END$$

DROP PROCEDURE IF EXISTS sp_estrutura_relacionados$$
CREATE PROCEDURE `sp_estrutura_relacionados`(IN p_schema VARCHAR(64), IN p_tabela VARCHAR(64))
BEGIN
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
END$$

DELIMITER ;
