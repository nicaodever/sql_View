import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root"),
    "database": os.getenv("DB_NAME", "bd_simulator"),
}

PORTA = 8000

PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estrutura do banco - SGBD</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 24px; color: #222; }
  h1 { font-size: 1.3rem; }
  .linha { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; }
  select { min-width: 260px; padding: 6px; font-size: 1rem; }
  #status { padding: 8px 12px; border-radius: 4px; margin-bottom: 16px; }
  .ok { background: #e6f4ea; color: #1e6b34; }
  .erro { background: #fce8e6; color: #a50e0e; }
  details { border: 1px solid #ccc; border-radius: 4px; margin-bottom: 8px; padding: 6px 10px; }
  summary { cursor: pointer; font-weight: 600; }
  summary span { font-weight: normal; color: #777; margin-left: 8px; }
  table { border-collapse: collapse; margin: 8px 0; width: 100%; }
  th, td { border: 1px solid #ccc; padding: 4px 8px; text-align: left; font-size: 0.9rem; }
  th { background: #f2f2f2; }
  h3 { font-size: 1rem; margin: 12px 0 4px; }
  .vazio { color: #777; font-style: italic; }
</style>
</head>
<body>
<h1>Simulador SGBD - estrutura do banco</h1>

<div id="status">Conectando ao banco...</div>

<div class="linha">
  <label for="schema">Banco (schema):</label>
  <select id="schema" disabled></select>
</div>

<div id="tabelas" class="vazio">Escolha um banco para ver suas tabelas.</div>

<script>
const statusEl = document.getElementById("status");
const selectSchema = document.getElementById("schema");
const areaTabelas = document.getElementById("tabelas");

function mostrarStatus(texto, ok) {
  statusEl.textContent = texto;
  statusEl.className = ok ? "ok" : "erro";
}

function montarTabela(colunas, linhas) {
  if (linhas.length === 0) {
    const vazio = document.createElement("p");
    vazio.className = "vazio";
    vazio.textContent = "Nenhum resultado.";
    return vazio;
  }
  const tabela = document.createElement("table");
  const cabeca = tabela.createTHead().insertRow();
  colunas.forEach(c => {
    const th = document.createElement("th");
    th.textContent = c;
    cabeca.appendChild(th);
  });
  const corpo = tabela.createTBody();
  linhas.forEach(linha => {
    const tr = corpo.insertRow();
    linha.forEach(valor => {
      tr.insertCell().textContent = valor === null ? "NULL" : String(valor);
    });
  });
  return tabela;
}

async function buscar(url) {
  const resposta = await fetch(url);
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.erro || "erro desconhecido");
  return dados;
}

async function carregarSchemas() {
  try {
    const dados = await buscar("/api/schemas");
    mostrarStatus("Conectado ao MySQL. " + dados.linhas.length + " schemas encontrados.", true);
    selectSchema.innerHTML = "";
    const vazio = document.createElement("option");
    vazio.value = "";
    vazio.textContent = "-- escolha --";
    selectSchema.appendChild(vazio);
    dados.linhas.forEach(([nome]) => {
      const opt = document.createElement("option");
      opt.value = nome;
      opt.textContent = nome;
      selectSchema.appendChild(opt);
    });
    selectSchema.disabled = false;
  } catch (erro) {
    mostrarStatus("Falha ao conectar: " + erro.message, false);
  }
}

function criarItemTabela(schema, tabela, tipo) {
  const item = document.createElement("details");
  const resumo = document.createElement("summary");
  resumo.textContent = tabela;
  const detalhe = document.createElement("span");
  detalhe.textContent = tipo;
  resumo.appendChild(detalhe);
  item.appendChild(resumo);

  const conteudo = document.createElement("div");
  item.appendChild(conteudo);

  let carregado = false;
  item.addEventListener("toggle", async () => {
    if (!item.open || carregado) return;
    carregado = true;
    conteudo.textContent = "Carregando estrutura...";
    try {
      const params = "?schema=" + encodeURIComponent(schema) +
                     "&tabela=" + encodeURIComponent(tabela);
      const estrutura = await buscar("/api/colunas" + params);
      conteudo.textContent = "";
      const h = document.createElement("h3");
      h.textContent = "Estrutura de " + schema + "." + tabela;
      conteudo.appendChild(h);
      conteudo.appendChild(montarTabela(estrutura.colunas, estrutura.linhas));
    } catch (erro) {
      carregado = false;
      conteudo.className = "erro";
      conteudo.textContent = "Erro ao carregar estrutura: " + erro.message;
    }
  });
  return item;
}

selectSchema.addEventListener("change", async () => {
  const schema = selectSchema.value;
  areaTabelas.innerHTML = "";
  if (!schema) {
    areaTabelas.className = "vazio";
    areaTabelas.textContent = "Escolha um banco para ver suas tabelas.";
    return;
  }
  try {
    const dados = await buscar("/api/tabelas?schema=" + encodeURIComponent(schema));
    areaTabelas.className = "";
    if (dados.linhas.length === 0) {
      areaTabelas.className = "vazio";
      areaTabelas.textContent = "Esse banco não tem tabelas.";
      return;
    }
    dados.linhas.forEach(([tabela, tipo]) => {
      areaTabelas.appendChild(criarItemTabela(schema, tabela, tipo));
    });
  } catch (erro) {
    areaTabelas.className = "erro";
    areaTabelas.textContent = "Erro ao listar tabelas: " + erro.message;
  }
});

carregarSchemas();
</script>
</body>
</html>
"""


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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        try:
            if url.path == "/":
                self._enviar(200, "text/html; charset=utf-8", PAGINA.encode("utf-8"))
            elif url.path == "/api/schemas":
                colunas, linhas = call("sp_listar_schemas")
                self._json({"colunas": colunas, "linhas": linhas})
            elif url.path == "/api/tabelas":
                schema = query.get("schema", [""])[0]
                colunas, linhas = call("sp_listar_tabelas", schema)
                self._json({"colunas": colunas, "linhas": linhas})
            elif url.path == "/api/colunas":
                schema = query.get("schema", [""])[0]
                tabela = query.get("tabela", [""])[0]
                colunas, linhas = call("sp_colunas_tabela", schema, tabela)
                self._json({"colunas": colunas, "linhas": linhas})
            else:
                self._json({"erro": "rota nao encontrada"}, 404)
        except mysql.connector.Error as erro:
            self._json({"erro": str(erro)}, 500)

    def _json(self, dados, codigo=200):
        corpo = json.dumps(dados, default=str, ensure_ascii=False).encode("utf-8")
        self._enviar(codigo, "application/json; charset=utf-8", corpo)

    def _enviar(self, codigo, tipo, corpo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, formato, *args):
        print(self.address_string(), formato % args)


if __name__ == "__main__":
    servidor = HTTPServer(("127.0.0.1", PORTA), Handler)
    print(f"Abra http://127.0.0.1:{PORTA} no navegador (Ctrl+C para parar)")
    servidor.serve_forever()
