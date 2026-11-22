# SOC Copilot

Assistente para investigar logs de segurança com busca híbrida, embeddings locais,
fontes rastreáveis e provedores de IA plugáveis. Projeto de portfólio de Engenharia
de IA / Blue Team, desenvolvido e executado no Windows com Python 3.12.

**Roda sem chave e sem cobrança de API.** O perfil padrão `extractive` apresenta o
trecho mais relevante e sua fonte; é um baseline extrativo, **não um LLM gerativo**.
Para gerar análises localmente, configure Ollama. OpenRouter, Gemini e OpenAI são
integrações opcionais.

## O que está implementado

- JSON, arrays JSON, JSONL/NDJSON, CSV e exportações Wazuh `hits.hits[*]._source`.
- Normalização, limpeza, timestamps UTC, chunking por tokens com overlap e IDs estáveis.
- Sentence Transformers na CPU e ChromaDB persistente, sem banco externo.
- BM25 + busca vetorial com Reciprocal Rank Fusion; filtros e top-k configuráveis.
- Citações `[S1]` com arquivo, registro, timestamp, ID do evento e trecho armazenado.
- `LLMProvider.chat(messages, tools=None)`, cinco adaptadores e fallback ordenado.
- Agente opcional com `buscar_alertas`, `estatisticas` e `explicar_regra_wazuh`.
- FastAPI, Swagger, CLI de chat, 200 registros fictícios e 20 casos de eval em YAML.
- Testes de contrato HTTP sem consumo de APIs, teste com modelo real e relatório de eval real.

## 1. Preparar o Windows

Use **Windows x64 e Python 3.11, 3.12 ou 3.13**; recomenda-se 3.12, utilizado na
validação. Python 3.14 ainda não faz parte da matriz suportada por estas versões
fixadas. Não precisa de GPU, Docker, WSL ou compilador C++.

Extraia o projeto em uma pasta curta, por exemplo `C:\src\soc-copilot`. O cache de
modelos pode exceder o limite de caminho do Windows se a pasta raiz for longa.
Reserve alguns GB para Python, PyTorch, dependências e modelo; 8 GB de RAM é um
ponto de partida para o baseline. Um LLM local exige memória adicional conforme
o modelo. Internet é necessária para a instalação e o primeiro download do
modelo público. Não é necessária depois de o modelo estar em cache.

### Opção A — uv (recomendada, versões travadas)

Abra PowerShell na pasta do projeto:

```powershell
py -m pip install uv
uv python install 3.12
uv sync --locked --python 3.12 --extra dev
Copy-Item .env.example .env
uv run --locked soc-copilot doctor
```

O `uv.lock` entregue foi gerado para Windows. Não há chave a preencher para o
perfil padrão. Não use `uv lock --upgrade` para reproduzir este resultado.

### Opção B — venv + pip

Com Python 3.12 instalado:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m soc_copilot doctor
```

`requirements-lock.txt` reproduz as dependências de execução. `requirements.txt`
instala o projeto com os intervalos do `pyproject.toml`; pode resolver versões
transitivas diferentes. Para desenvolver com pip: `python -m pip install -e ".[dev]"`.
Os comandos seguintes usam `uv run`; com venv, substitua `uv run soc-copilot` por
`.\.venv\Scripts\python.exe -m soc_copilot`.

## 2. Indexar e perguntar

Execute sempre da raiz do projeto, onde ficam `.env`, `data` e `evals`:

```powershell
uv run soc-copilot ingest data/samples
uv run soc-copilot ask "O que ocorreu no evento LAB-SQLI-001 de origem 192.0.2.121?"
uv run soc-copilot chat
```

No chat, `/sair` encerra. Cada pergunta é independente; não há memória de conversa.
`ask --json` retorna o objeto completo. `--top-k 8` muda o número de candidatos.
O baseline cita o melhor candidato; os demais ficam em `retrieved` na saída JSON.

Exemplo do formato:

```text
Evidência mais próxima encontrada: DVWA: tentativa de SQL injection ... [S1]
[S1] samples/dvwa_alerts.csv | registro 1 | 2026-11-02T06:00:00Z
```

O resultado efetivamente executado está em [docs/resposta-exemplo.json](docs/resposta-exemplo.json).
Uma citação válida identifica o trecho; não prova que uma interpretação gerada
pelo LLM seja correta. Um HTTP 200, por exemplo, não comprova sucesso de exploração.

Após a primeira ingestão, coloque `EMBEDDING_OFFLINE=true` no `.env` para impedir
downloads do modelo. `extractive` e Ollama local não enviam logs para APIs.

## 3. Configurar um provedor

Edite **somente seu `.env`**, ignorado pelo Git. Nenhuma chave é embutida no código.
`LLM_MODEL` substitui o modelo do provedor principal quando preenchido. Os fallbacks
usam seus próprios `GEMINI_MODEL`, `OLLAMA_MODEL`, etc.

| Provedor | Variáveis necessárias | Custo / observações |
|---|---|---|
| `extractive` | Nenhuma chave | Gratuito, local, sem geração nem chamadas de ferramentas |
| `ollama` | `OLLAMA_MODEL`, serviço Ollama local | Gratuito, modelo e hardware locais |
| `openrouter` | `OPENROUTER_API_KEY`; padrão `openrouter/free` | Roteador gratuito com limites e disponibilidade variável |
| `gemini` | `GEMINI_API_KEY`, `GEMINI_MODEL` | Escolha modelo com free tier na sua conta AI Studio |
| `openai` | `OPENAI_API_KEY`, `OPENAI_MODEL` | Opcional; pode ter cobrança |

### OpenRouter

Crie uma chave no [painel OpenRouter](https://openrouter.ai/keys), preencha
`OPENROUTER_API_KEY` e altere:

```dotenv
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/free
OPENROUTER_FREE_ONLY=true
LLM_FALLBACKS=extractive
```

Com `OPENROUTER_FREE_ONLY=true`, o adaptador recusa IDs que não sejam
`openrouter/free` ou terminem em `:free`. Só use `:free` se a variante existir no
[catálogo oficial](https://openrouter.ai/collections/free-models). Modelos gratuitos
têm cotas; o projeto não compra créditos nem escolhe modelos pagos automaticamente.

### Gemini / Google AI Studio

Obtenha a chave no [AI Studio](https://aistudio.google.com/api-keys). Preencha
`GEMINI_API_KEY` e `GEMINI_MODEL` com um ID habilitado na sua conta e que ofereça
[free tier](https://ai.google.dev/gemini-api/docs/pricing). Depois:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=
LLM_FALLBACKS=extractive
```

O modelo fica deliberadamente vazio no exemplo: não presumimos disponibilidade
da sua conta. A política de cobrança é definida pelo Google e pela conta; o cliente
não consegue garantir gratuidade se você habilitar um modelo ou plano pago.

### OpenAI / endpoint compatível

Preencha `OPENAI_MODEL` e `OPENAI_API_KEY`, selecione `LLM_PROVIDER=openai` e
deixe `LLM_MODEL` vazio para usar `OPENAI_MODEL`. `OPENAI_BASE_URL` é a raiz da API,
por exemplo a URL oficial já incluída, **sem** `/chat/completions` ou `/responses`.

- `OPENAI_API_MODE=chat_completions`: envia o contrato Chat Completions.
- `OPENAI_API_MODE=responses`: envia o contrato Responses e preserva os itens
  necessários à continuação de chamadas de ferramentas.

Para um modelo GPT/Codex, confira no serviço escolhido qual endpoint ele suporta.
“Compatível com OpenAI” não implica suporte a todos os modelos ou a Responses.
Este projeto **não acessa sessões do app Codex, não reutiliza tokens do ChatGPT e
não transforma uma assinatura em acesso gratuito à API**. Um endpoint local em
`127.0.0.1`/`localhost` pode funcionar sem chave se o próprio servidor permitir.

### Ollama: geração inteiramente local

Instale [Ollama para Windows](https://ollama.com/download/windows) e baixe um modelo
adequado à memória disponível. Use `ollama list` para obter o ID exato instalado;
copie-o para `OLLAMA_MODEL`. Configure:

```dotenv
LLM_PROVIDER=ollama
LLM_MODEL=
OLLAMA_BASE_URL=http://127.0.0.1:11434
LLM_FALLBACKS=extractive
```

Para habilitar o agente, escolha um modelo com suporte a tools. O baseline
extrativo funciona como fallback, mas não faz análises gerativas nem usa ferramentas.
O adaptador Ollama foi validado por contrato simulado, sem baixar um LLM nesta entrega.

### Fallback e tratamento de erros

Exemplo: `LLM_FALLBACKS=gemini,ollama,extractive`. Configure a chave/modelo de cada
serviço listado. A ordem é principal → lista; repetidos são removidos. Timeout,
erro HTTP, resposta inválida ou configuração incompleta fazem tentar o próximo.
Há uma tentativa por provedor por rodada, sem retry oculto. Falha de todos retorna
erro claro (HTTP 503 na API). O resultado informa o provedor usado e as falhas em
`warnings`. Nenhuma chave ou corpo de erro remoto é registrado.

Ao habilitar APIs, perguntas, trechos e saídas das ferramentas podem ser enviados
a esses serviços, inclusive aos fallbacks. Use os dados sintéticos para demonstração
e avalie a política de dados do serviço antes de enviar logs reais.

## 4. Agente e ferramentas

Com um modelo que suporte function calling:

```powershell
uv run soc-copilot ask "Quantos eventos há entre 2026-11-01T00:00:00Z e 2026-11-01T23:59:59Z?" --agent
uv run soc-copilot ask "Explique a regra Wazuh 100001 usando os registros locais." --agent
```

Ou configure `AGENT_ENABLED=true`. São permitidas até `AGENT_MAX_ROUNDS=3` rodadas
de ferramentas, mais uma resposta final, e até cinco chamadas por rodada.

- `buscar_alertas(filtro, limit)`: filtros exatos por `rule_id`, `src_ip`, `agent`,
  `source`, `event_id`, `min_level`, `start` e `end`.
- `estatisticas(periodo)`: conta registros únicos por arquivo/registro; não conta
  chunks como eventos. Período UTC inclusivo, com fuso obrigatório. Sem período,
  considera a base inteira. As citações anexas são uma amostra dos registros.
- `explicar_regra_wazuh(id)`: retorna descrição e níveis observados na base.
  Não inventa a definição oficial de uma regra inexistente.

As ferramentas não executam comandos nem ações sobre hosts. Os IDs de regras
100001..100006 da amostra representam regras **customizadas fictícias**.

## 5. API REST

```powershell
uv run soc-copilot serve --port 8000
```

Abra [Swagger local](http://127.0.0.1:8000/docs). O servidor escuta apenas loopback,
sem autenticação, para uso individual. Use **um processo por diretório Chroma**;
encerre a API antes de ingerir pela CLI, ou ingira via endpoint da própria API.

| Método | Rota | Corpo |
|---|---|---|
| GET | `/health` | — |
| POST | `/ingest` | `{"path":"samples/wazuh_alerts.json"}` |
| POST | `/search` | `{"question":"SSH","top_k":5}` |
| POST | `/chat` | `{"question":"SSH","agent":false,"filters":{"min_level":5}}` |
| POST | `/stats` | `{"start":"2026-11-01T00:00:00Z","end":"2026-11-01T23:59:59Z"}` |

```powershell
$body = @{ question = 'Qual o alerta LAB-SSH-001?'; top_k = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

`filters` restringe a recuperação inicial. As ferramentas do agente usam os filtros
que constam em seus próprios argumentos; isso não é um mecanismo de autorização
ou isolamento entre usuários. `/ingest` aceita apenas arquivos sob `DATA_DIR` e
nunca aceita caminhos arbitrários fora dessa pasta.

## 6. Seus próprios dados

Coloque os exports em `data/private/` e rode `ingest data/private`. O diretório está
ignorado pelo Git. UTF-8 com ou sem BOM; CSV com vírgula, ponto e vírgula ou tab.
Campos Wazuh podem estar aninhados ou em colunas como `rule.id` e `agent.name`.

Para DVWA, não há um formato universal de exportação. O contrato usado aqui é:

```csv
event_id,timestamp,host,src_ip,level,message
MEU-001,2026-11-01T12:00:00Z,dvwa-lab,192.0.2.1,8,Tentativa registrada no laboratório
```

É necessário ao menos `message`, `description`, `full_log` ou `rule.description`.
Timestamp ausente vira `unknown`; inválido ou sem fuso é rejeitado. O timestamp
original permanece no texto normalizado. IPs reservados `192.0.2.0/24` e hosts
`lab-*` sinalizam dados fictícios.

Arquivos têm limite de 50 MiB. Um registro inválido interrompe aquele arquivo antes
de alterar o índice; os arquivos anteriores de uma execução podem já ter sido
ingeridos. Reingerir o mesmo caminho relativo atualiza seus chunks e remove os
obsoletos; não duplica registros. Um arquivo vazio remove os registros antes
associados àquela fonte. Mover/copiar o mesmo conteúdo para outro caminho cria
outra fonte. Exclusão do arquivo no disco não remove automaticamente seus dados
do índice. A sincronização de lotes não é transacional; após interrupção, reingira.

## 7. Avaliar e testar

```powershell
uv run soc-copilot eval --questions evals/questions.yaml --report reports/latest.md
uv run pytest -m "not integration"
uv run ruff check src tests scripts
uv run mypy src
```

Teste com o modelo real já baixado:

```powershell
$env:SOC_TEST_MODEL_CACHE = (Resolve-Path models).Path
uv run pytest -m integration
```

O teste de integração usa somente cache local. Sem `SOC_TEST_MODEL_CACHE`, ele é
marcado como skipped, explicitamente. Para regenerar os dados e o YAML:

```powershell
uv run python scripts/generate_samples.py
```

O [relatório de exemplo](docs/relatorio-exemplo.md) foi **calculado**, com 200 eventos,
444 chunks, embeddings reais e `extractive`: recuperação 100%, citação 95%,
similaridade média 0,761, sem erros nas 20 perguntas. O caso q04 recuperou o evento
esperado no top-k, mas o baseline citou outro candidato; o erro está preservado.

Score = `0.5 × hit_de_citação + 0.5 × similaridade_cosseno`. O hit exige arquivo e
ID do evento esperados na **citação da resposta**. A similaridade usa o mesmo
modelo de embeddings, com limite de tokens do modelo. Esse conjunto faz consultas
factuais por ID/IP; é um smoke test sintético. Para medir generalização, amplie com
perguntas sem identificadores, casos sem resposta, dados reais revisados, injeção
de prompt e avaliações humanas de fidelidade. Não trate similaridade como verdade.

APIs pagas/gratuitas não foram chamadas na validação: não foram fornecidas chaves.
Os testes HTTP verificam tradução de contratos, erros, fallback e tool calling;
acesso real, disponibilidade e qualidade de cada modelo dependem da sua configuração.

## Estrutura

```text
src/soc_copilot/
  ingest/       # parsers e pipeline
  embeddings/   # Sentence Transformers local
  retrieval/    # Chroma, BM25, filtros e fusão
  providers/    # interface, adaptadores e fallback
  agent/        # ferramentas, evidências e serviço RAG
  evals/        # execução e pontuação
  api/          # FastAPI
  cli.py        # CLI e chat
tests/          # testes unitários, contratos e integração
data/samples/   # 120 Wazuh JSON + 80 DVWA CSV
evals/          # 20 perguntas e respostas esperadas
scripts/        # gerador reproduzível
docs/           # arquitetura, decisões e resultados
```

Veja [arquitetura e decisões](docs/arquitetura.md) e [registro de validação](docs/validacao.md).

## Solução de problemas

- **Caminho não encontrado no Hugging Face:** extraia em pasta curta ou configure
  `EMBEDDING_CACHE_DIR=C:/soc-models` em uma pasta onde tenha permissão. Não é preciso
  habilitar symlinks ou executar como administrador.
- **Chroma encerra sem traceback / access violation:** o runtime C++ antigo do
  sistema foi a causa observada durante o desenvolvimento. O pacote `msvc-runtime`
  e o bootstrap em `windows_runtime.py` carregam a DLL no venv. Use o ambiente e
  versões travadas. Veja a investigação em `docs/arquitetura.md`.
- **Outro modelo/chunking na coleção:** escolha um novo `CHROMA_COLLECTION` no
  `.env` e reingira os arquivos. Não misture embeddings diferentes no mesmo índice.
- **Nenhum trecho:** confira `DATA_DIR`, ingestão, filtros, modelo e pergunta.
  O corte vetorial 0,35 é heurístico e não calibrado; BM25 também participa da busca.
- **401/429/503:** confira chave, cotas, modelo e `warnings`; use `extractive` ou
  Ollama para não depender da disponibilidade de uma API.
- **Pergunta de contagem sem agente:** use `/stats` ou um modelo com tools e `--agent`.
  Top-k não representa o total do corpus.
- **API lenta na primeira inicialização:** o modelo é carregado uma vez por processo;
  na CLI, cada comando inicia um processo. `chat` e API reutilizam o modelo em memória.

## Licença

Código sob MIT. Os dados desta entrega são sintéticos. Pacotes e modelos mantêm
suas próprias licenças; consulte o model card do modelo de embeddings escolhido.
