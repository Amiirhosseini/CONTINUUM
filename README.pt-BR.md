<p align="center">
  <img src="docs/assets/readme-img.png" alt="Banner do CONTINUUM" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM: Recuperação semântica verificável para agentes de IA de longa duração.</strong>
  Checkpoints semânticos (não dumps de conversa), um ledger idempotente de ações
  que recusa efeitos colaterais duplicados, e um log de eventos encadeado por hash à prova de adulteração,
  tudo exposto como um servidor MCP que nega por padrão. Agnóstico a framework, Python 3.11+.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://pypi.org/project/continuum-agent/"><img src="https://img.shields.io/pypi/v/continuum-agent?style=flat-square&label=PyPI" alt="PyPI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="Status CI" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center" style="margin-bottom: 6px;">
  <a href="https://continuum-nu-six.vercel.app/"><strong>Visite o site do CONTINUUM</strong></a>
</p>

<p align="center" style="margin-top: 6px;">
  <a href="https://app.ona.com/#https://github.com/Cyrax321/CONTINUUM"><img src="https://ona.com/build-with-ona.svg" alt="Build with Ona" /></a>
</p>

<p align="center">
  <sub>Se o CONTINUUM ajuda seus agentes a se recuperarem, por favor dê uma estrela ao repositório. Isso ajuda outros a descobri-lo e mantém as boas first issues chegando.</sub>
</p>

<p align="center">
  <sub><a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a> | <a href="README.ja.md">日本語</a> | <strong>Português</strong></sub>
</p>

---

## Sumário

[Por quê](#por-quê) · [Início rápido](#início-rápido) · [Como funciona](#como-funciona) · [Onde o CONTINUUM se encaixa](#onde-o-continuum-se-encaixa) · [Funcionalidades](#funcionalidades) · [Extensão de segurança](#extensão-de-segurança) · [Verificação empírica](#verificação-empírica) · [Integração MCP](#integração-mcp) · [Integração de frameworks](#integração-de-frameworks) · [Conceitos centrais](#conceitos-centrais) · [Arquitetura](#arquitetura) · [API e CLI](#api-e-cli) · [Roteiro](#roteiro) · [O que o CONTINUUM não é](#o-que-o-continuum-não-é) · [Trabalho relacionado](#trabalho-relacionado) · [Status e limitações](#status-e-limitações) · [Contribuir](#contribuir) · [Licença](#licença)

---

## Por quê

Agentes de IA modernos executam tarefas longas, com centenas de chamadas LLM, invocações de ferramentas e escritas em arquivos e bancos de dados. Quando falham, a resposta usual é reproduzir tudo do zero, o que duplica trabalho, duplica efeitos colaterais, desperdiça tokens e perde decisões.

O CONTINUUM faz uma pergunta mais estreita e mais difícil: um agente pode retomar a partir de uma representação semântica compacta de seu estado de tarefa enquanto verifica de forma independente que esse estado ainda é válido no ambiente atual? Seu diferencial tem três partes:

- **Checkpoints semânticos**: uma representação compacta e versionada do que o agente precisa para continuar, não um despejo de conversa.
- **Revalidação independente do ambiente**: cada componente do checkpoint é verificado contra o ambiente atual antes de retomar, e a obsolescência se propaga pelo grafo de dependências.
- **Estado com proveniência**: cada fato carrega sua origem, de modo que o progresso reportado pelo agente nunca se auto certifica.

## Início rápido

Publicado no PyPI como `continuum-agent` 0.1.0, execute `pip install continuum-agent` (`pip install continuum-agent==0.1.0` para fixar a versão). As tags de release também anexam wheels construídos em [GitHub Releases](https://github.com/Cyrax321/CONTINUUM/releases).

Caminhos sem configuração (sem clonar, sem instalar, sem publicar nada):

| Caminho | Como |
|:--|:--|
| Instalar do PyPI | `pip install continuum-agent==0.1.0` e depois `continuum --help` |
| Ver a recuperação de falha de ponta a ponta | `docker run --rm ghcr.io/cyrax321/continuum` |
| Usar a CLI via Docker | `docker run --rm ghcr.io/cyrax321/continuum continuum --help` |
| Executar a CLI sem clonar | `uvx --from git+https://github.com/Cyrax321/CONTINUUM.git continuum --help` |
| Windows PowerShell (de um clone) | `powershell -ExecutionPolicy Bypass -File .\try-it.ps1` ou `powershell -ExecutionPolicy Bypass -File .\try-it.ps1 cli --help` |
| Ambiente de desenvolvimento completo no navegador | [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Cyrax321/CONTINUUM?quickstart=1) |

A imagem Docker é publicada no GHCR pelo CI a cada push para `main` e a cada tag de release (`.github/workflows/docker-publish.yml`). O Codespace é definido em `.devcontainer/`.

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM

uv venv && source .venv/bin/activate     # macOS / Linux; Windows: .venv\Scripts\activate

# Colaboradores (recomendado): biblioteca + CLI + todas as ferramentas de teste + cada adaptador
uv pip install -e ".[dev]"

# Ou escolha apenas o que precisa: . (mínimo), [mcp], [otel], [langgraph],
# [openai], [langchain], [attest], [postgres]

# Ou pule o clone por completo:
uv pip install git+https://github.com/Cyrax321/CONTINUUM.git
uv pip install "continuum-agent[mcp] @ git+https://github.com/Cyrax321/CONTINUUM.git"
```

> **Alternativa com pip:** substitua `uv pip install` por `pip install` em cada comando acima.

Verifique:

```bash
continuum --help                 # ponto de entrada CLI
continuum-mcp --help             # ponto de entrada do servidor MCP (precisa de [mcp] ou [dev])
pytest -q                        # ~1,380 testes coletados (o número exato e os pulos variam por ambiente)
ruff check src/ tests/ examples/ && ruff format --check src/ tests/ examples/
mypy src/continuum               # os três portões que o CI exige
```

A biblioteca central tem uma única dependência de runtime (`pydantic>=2.7`), todo o resto é opcional. O mapa completo de pacotes, a matriz de extras, a configuração de testes do Postgres e a verificação por comando estão em [references/install.md](references/install.md).

### Conecte um agente de código em dois minutos

Para Claude Code, Gemini CLI ou Codex, você não escreve Python e não precisa de arquivo de prompts:

```bash
continuum start my-task --goal "O que o agente deve fazer"
continuum hooks install claude-code --with-gate   # também: gemini, codex
```

A partir daí cada arquivo que o agente escreve é capturado como evidência encadeada, sua sessão começa com um briefing automático de estado, efeitos colaterais não declarados registrados em `.continuum/gate.json` são recusados antes de disparar, e uma sessão fresca após qualquer queda retoma com próximos passos executáveis. Não é necessário CLAUDE.md.

Exemplo mínimo de biblioteca, registro e recuperação:

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="Analisar 10,000 documentos"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "Analisar 10,000 documentos", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# Após uma queda, um processo novo retoma exatamente de onde parou:
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # já feito, não se repete
print(store.verify_events("run_4821").ok)  # True, cadeia intacta após a queda
```

**Execute a prova você mesmo:**

```bash
python examples/crash_recovery_agent.py   # morte real do processo, efeito colateral real
python examples/context_compaction.py     # transcrição perdida, checkpoint sobrevive
python examples/model_switch.py           # Modelo A morre, Modelo B retoma com segurança
python scripts/mcp_smoke.py               # subprocesso real, tráfego JSON-RPC real
```

O kit `e2e-autonomy-test/` roteiriza uma tarefa real de lotes de faturas, uma morte brusca no meio da execução e uma sessão fresca de retomada, depois pontua o outbox, o ledger e a cadeia de eventos fora de banda. A execução 1 obteve **7/7 em mecânicas** contra uma sessão real do Claude Code. Passo a passo completo em [references/e2e.md](references/e2e.md).

## Como funciona

O CONTINUUM separa o **contexto LLM** (temporário) do **estado duradouro da tarefa** (permanente). Em vez de salvar o histórico de conversa, ele constrói um checkpoint semântico, a mínima informação verificada necessária para continuar.

![Como o CONTINUUM funciona](docs/assets/architecture.svg)

A explicação detalhada, o modelo de projeção e o contexto de recuperação estão em [references/architecture.md](references/architecture.md).

## Onde o CONTINUUM se encaixa

Quatro preocupações se sobrepõem em cada agente de longa duração. O CONTINUUM é dono apenas da última e toca as outras três por meio de costuras explícitas. Nenhum concorrente é nomeado e nenhuma afirmação é feita sem um módulo entregue ou uma suíte publicada que já a imprima.

| Camada | Responde | Como se conecta (módulos entregues ou saídas publicadas) |
|:--|:--|:--|
| Harness | Como o agente chama ferramentas e avança em direção a um objetivo? | Fora do CONTINUUM. Pontos de conexão entregues em `src/continuum/adapters/generic.py` (`GenericAgentAdapter`), `src/continuum/adapters/thin.py` (hooks de CrewAI, AutoGen, Pydantic AI), `src/continuum/mcp/server.py` (MCP stdio), `src/continuum/hooks.py` e `src/continuum/clienthooks.py` (hooks de ciclo de vida de CLI de código), `src/continuum/gateway.py` (proxy HTTP de cumprimento para qualquer linguagem) e `src/continuum/otel.py` (ponte OpenTelemetry). Receitas em `docs/recipes/` e `references/adapters.md`. |
| Execução durável | O que aconteceu antes de uma queda e o que pode ser reproduzido sem perder trabalho? | Log de eventos encadeado `src/continuum/events.py` com `verify()` e `trusted_through`, armazenamento durável `src/continuum/storage/sqlite.py` (WAL, `synchronous=FULL`, schema v6) e `src/continuum/storage/postgres.py` mais `src/continuum/storage/migrations.py`, checkpoints orientados por políticas `src/continuum/checkpoint/manager.py` e `src/continuum/checkpoint/policy.py` que reproduzem a lacuna em `restore()`. Passo a passo em `docs/recovery_walkthrough.md` (saída de `examples/recovery_walkthrough.py`). |
| Plano de controle | Qual execução está ativa, quem pode agir sobre ela e para onde vai a saída? | Registro de execuções e hierarquia pai/filho `src/continuum/storage/` e `src/continuum/recovery/family.py` (`continuum tree`), autorização allowlist `src/continuum/mcp/authz.py` (`CONTINUUM_MCP_MUTATING_CLIENTS` / `CONTINUUM_MCP_TOKEN`), superfícies de apresentação `src/continuum/dashboard/app.py` e `src/continuum/serve/server.py`, CLI `src/continuum/cli/main.py` (`continuum runs`, `continuum tree`, `continuum health`). |
| Substrato de verificação | Dado o checkpoint no tempo T e o mundo como está agora, ainda é seguro e correto continuar? | `src/continuum/state/validator.py` (obsolescência `dependency -> evidence -> finding -> decision` mais `PlanStep.depends_on`), `src/continuum/provenance_map.py` (`Origin` a `REQUIRES_REVIEW` até `REVIEW_CONFIRMED`), `src/continuum/actions/ledger.py` com `src/continuum/actions/idempotency.py` e `src/continuum/gate.py` / `src/continuum/gateway.py` (reivindicar antes de disparar, recusa duplicatas, lança `UnknownSideEffect` para reconciliação), `src/continuum/replayguard.py` (guarda portátil), `src/continuum/pinning.py` e `src/continuum/replay_similarity.py` (correção de reprodução), `src/continuum/budgets.py` (limites de tentativas), `src/continuum/recovery/engine.py` + `src/continuum/recovery/contract.py` + `src/continuum/recovery/planner.py` + `src/continuum/recovery/observations.py` (severidade máxima `RESUME < ... < ABORT`, contrato selado com `evidence` / `reason` / `next_allowed_action` / `human_steps`), `src/continuum/checkpoint/rewind.py` (rebobinamento atômico de estado duplo), `src/continuum/analysis/prefix_trust.py` (confiança consultiva). Verificações publicadas: `docs/recovery_walkthrough.md`, `benchmarks/fault_injection/` (suíte que imprime `detection_rate` / `unsafe_resume_rate`), `src/continuum/benchmark/phase6/` (suíte de correção de recuperação), `docs/RESULTS.md` e o visual regenerável abaixo. |

Cada linha acima é rastreável a um caminho que existe em `main` no commit etiquetado. Nada nesta tabela reexpõe um número de benchmark, os benchmarks só vivem na saída da suíte que já os imprime. Veja `docs/research.md` para a lista completa de suítes publicadas e documentos de design.
