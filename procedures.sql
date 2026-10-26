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
    WHERE t.TABLE_SCHEMA = p_schema
    ORDER BY t.TABLE_NAME;
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

DELIMITER ;
