# Simulador SGBD - consulta de metadados

Aplicação web que mostra, para uma tabela escolhida, os relacionamentos
(lado N e lado 1) e a estrutura das tabelas envolvidas. O Python apenas
chama (`CALL`) stored procedures que leem o `information_schema` do MySQL.

## Requisitos
- Python 3.9 ou superior
- MySQL em execução (`127.0.0.1`, porta 3306)

## Como rodar

1. **Criar as procedures no MySQL.** Abra o `procedures.sql` no MySQL Workbench
   (File > Open SQL Script) e execute tudo (raio, ou Ctrl+Shift+Enter).
   O script cria o banco `bd_simulator` e as procedures; pode ser executado
   mais de uma vez.

2. **Instalar a dependência** (na pasta do projeto):

   ```
   pip install -r requirements.txt
   ```

3. **Conferir usuário e senha do MySQL** no início do `teste_web.py`
   (padrão: `root` / `root`).

4. **Iniciar o servidor:**

   ```
   python teste_web.py
   ```

5. Abrir **http://127.0.0.1:8000** no navegador. Escolha o banco (schema) e
   expanda uma tabela para ver os relacionamentos.


