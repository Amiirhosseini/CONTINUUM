<p align="center">
  <img src="docs/assets/readme-img.png" alt="Banner de CONTINUUM" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM: Recuperación semántica verificable para agentes de IA de larga duración.</strong>
  Checkpoints semánticos (no volcados de conversación), un libro mayor idempotente de acciones
  que rechaza efectos secundarios duplicados, y un registro de eventos encadenado y a prueba de manipulaciones,
  todo expuesto como un servidor MCP que deniega por defecto. Agnóstico al framework, Python 3.11+.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://pypi.org/project/continuum-agent/"><img src="https://img.shields.io/pypi/v/continuum-agent?style=flat-square&label=PyPI" alt="PyPI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="Estado CI" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center" style="margin-bottom: 6px;">
  <a href="https://continuum-nu-six.vercel.app/"><strong>Visita el sitio web de CONTINUUM</strong></a>
</p>

<p align="center" style="margin-top: 6px;">
  <a href="https://app.ona.com/#https://github.com/Cyrax321/CONTINUUM"><img src="https://ona.com/build-with-ona.svg" alt="Build with Ona" /></a>
</p>

<p align="center">
  <sub>Si CONTINUUM ayuda a tus agentes a recuperarse, por favor dale una estrella al repositorio. Ayuda a otros a descubrirlo y mantiene las buenas first issues llegando.</sub>
</p>

<p align="center">
  <sub><a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a> | <strong>Español</strong></sub>
</p>

---

## Contenidos

[Por qué](#por-qué) · [Inicio rápido](#inicio-rápido) · [Cómo funciona](#cómo-funciona) · [Dónde se sitúa CONTINUUM](#dónde-se-sitúa-continuum) · [Características](#características) · [Extensión de seguridad](#extensión-de-seguridad) · [Verificación empírica](#verificación-empírica) · [Integración MCP](#integración-mcp) · [Integración de frameworks](#integración-de-frameworks) · [Conceptos clave](#conceptos-clave) · [Arquitectura](#arquitectura) · [API y CLI](#api-y-cli) · [Hoja de ruta](#hoja-de-ruta) · [Lo que CONTINUUM no es](#lo-que-continuum-no-es) · [Trabajo relacionado](#trabajo-relacionado) · [Estado y limitaciones](#estado-y-limitaciones) · [Contribuir](#contribuir) · [Licencia](#licencia)

---

## Por qué

Los agentes de IA modernos ejecutan tareas largas, con cientos de llamadas LLM, invocaciones de herramientas y escrituras en archivos y bases de datos. Cuando fallan, la respuesta habitual es reproducir todo desde cero, lo que duplica trabajo, duplica efectos secundarios, malgasta tokens y pierde decisiones.

CONTINUUM plantea una pregunta más precisa y más difícil: puede un agente reanudarse desde una representación semántica compacta de su estado de tarea mientras verifica de forma independiente que ese estado sigue siendo válido en el entorno actual? Su diferenciador tiene tres partes:

- **Checkpoints semánticos**: una representación compacta y versionada de lo que el agente necesita para continuar, no un volcado de conversación.
- **Revalidación independiente del entorno**: cada componente del checkpoint se verifica contra el entorno actual antes de reanudar, y la obsolescencia se propaga por el grafo de dependencias.
- **Estado con procedencia**: cada hecho lleva su origen, por lo que el progreso reportado por el agente nunca se auto certifica.

## Inicio rápido

Publicado en PyPI como `continuum-agent` 0.1.0, ejecuta `pip install continuum-agent` (`pip install continuum-agent==0.1.0` para fijar la versión). Las etiquetas de release además adjuntan wheels construidos en [GitHub Releases](https://github.com/Cyrax321/CONTINUUM/releases).

Rutas sin configuración (sin clonar, sin instalar, sin publicar nada):

| Ruta | Cómo |
|:--|:--|
| Instalar desde PyPI | `pip install continuum-agent==0.1.0` y luego `continuum --help` |
| Ver la recuperación tras fallo de principio a fin | `docker run --rm ghcr.io/cyrax321/continuum` |
| Usar la CLI a través de Docker | `docker run --rm ghcr.io/cyrax321/continuum continuum --help` |
| Ejecutar la CLI sin clonar | `uvx --from git+https://github.com/Cyrax321/CONTINUUM.git continuum --help` |
| Windows PowerShell (desde un clon) | `powershell -ExecutionPolicy Bypass -File .\try-it.ps1` o `powershell -ExecutionPolicy Bypass -File .\try-it.ps1 cli --help` |
| Entorno de desarrollo completo en el navegador | [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Cyrax321/CONTINUUM?quickstart=1) |

La imagen Docker se publica en GHCR por CI en cada push a `main` y en cada etiqueta de release (`.github/workflows/docker-publish.yml`). El Codespace se define en `.devcontainer/`.

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM

uv venv && source .venv/bin/activate     # macOS / Linux; Windows: .venv\Scripts\activate

# Colaboradores (recomendado): librería + CLI + todas las herramientas de test + cada adaptador
uv pip install -e ".[dev]"

# O elige solo lo que necesitas: . (mínimo), [mcp], [otel], [langgraph],
# [openai], [langchain], [attest], [postgres]

# O sáltate el clon por completo:
uv pip install git+https://github.com/Cyrax321/CONTINUUM.git
uv pip install "continuum-agent[mcp] @ git+https://github.com/Cyrax321/CONTINUUM.git"
```

> **Alternativa con pip:** reemplaza `uv pip install` por `pip install` en cada comando anterior.

Verifica:

```bash
continuum --help                 # punto de entrada CLI
continuum-mcp --help             # punto de entrada servidor MCP (necesita [mcp] o [dev])
pytest -q                        # ~1,380 tests recogidos (el número exacto y los saltos varían por entorno)
ruff check src/ tests/ examples/ && ruff format --check src/ tests/ examples/
mypy src/continuum               # las tres puertas que CI exige
```

La librería central tiene una sola dependencia de runtime (`pydantic>=2.7`), todo lo demás es opcional. El mapa completo de paquetes, la matriz de extras, la configuración de tests de Postgres y la verificación por comando están en [references/install.md](references/install.md).

### Conecta un agente de código en dos minutos

Para Claude Code, Gemini CLI o Codex, no escribes Python y no necesitas archivo de prompts:

```bash
continuum start my-task --goal "Qué debe hacer el agente"
continuum hooks install claude-code --with-gate   # también: gemini, codex
```

Desde entonces cada archivo que el agente escribe se captura como evidencia encadenada, su sesión arranca con un briefing automático de estado, los efectos secundarios no declarados registrados en `.continuum/gate.json` se rechazan antes de ejecutarse, y una sesión fresca tras cualquier caída se reanuda con pasos siguientes ejecutables. No se necesita CLAUDE.md.

Ejemplo mínimo de librería, registro y recuperación:

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="Analizar 10,000 documentos"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "Analizar 10,000 documentos", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# Tras una caída, un proceso nuevo retoma exactamente donde se detuvo:
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # ya hecho, no se repite
print(store.verify_events("run_4821").ok)  # True, cadena intacta tras la caída
```

**Ejecuta la prueba tú mismo:**

```bash
python examples/crash_recovery_agent.py   # muerte real del proceso, efecto secundario real
python examples/context_compaction.py     # transcripción perdida, checkpoint sobrevive
python examples/model_switch.py           # Modelo A muere, Modelo B retoma de forma segura
python scripts/mcp_smoke.py               # subproceso real, tráfico JSON-RPC real
```

El kit `e2e-autonomy-test/` guioniza una tarea real de lotes de facturas, una muerte brusca a mitad de ejecución y una sesión fresca de reanudación, luego puntúa el outbox, el libro mayor y la cadena de eventos fuera de banda. La ejecución 1 obtuvo **7/7 en mecánicas** contra una sesión real de Claude Code. Recorrido completo en [references/e2e.md](references/e2e.md).

## Cómo funciona

CONTINUUM separa el **contexto LLM** (temporal) del **estado duradero de la tarea** (permanente). En lugar de guardar el historial de conversación, construye un checkpoint semántico, la mínima información verificada necesaria para continuar.

![Cómo funciona CONTINUUM](docs/assets/architecture.svg)

La explicación detallada, el modelo de proyección y el contexto de recuperación están en [references/architecture.md](references/architecture.md).

## Dónde se sitúa CONTINUUM

Cuatro preocupaciones se solapan en cada agente de larga duración. CONTINUUM solo es dueño de la última y toca las otras tres a través de costuras explícitas. No se nombra a ningún competidor y no se hace ninguna afirmación sin un módulo entregado o una suite publicada que ya lo imprima.

| Capa | Responde | Cómo se conecta (módulos entregados o salidas publicadas) |
|:--|:--|:--|
| Harness | Cómo el agente llama a herramientas y avanza hacia un objetivo? | Fuera de CONTINUUM. Puntos de conexión entregados en `src/continuum/adapters/generic.py` (`GenericAgentAdapter`), `src/continuum/adapters/thin.py` (hooks de CrewAI, AutoGen, Pydantic AI), `src/continuum/mcp/server.py` (MCP stdio), `src/continuum/hooks.py` y `src/continuum/clienthooks.py` (hooks de ciclo de vida de CLI de código), `src/continuum/gateway.py` (proxy HTTP de cumplimiento para cualquier lenguaje) y `src/continuum/otel.py` (puente OpenTelemetry). Recetas en `docs/recipes/` y `references/adapters.md`. |
| Ejecución durable | Qué pasó antes de una caída y qué puede reproducirse sin perder trabajo? | Registro de eventos encadenado `src/continuum/events.py` con `verify()` y `trusted_through`, almacenamiento durable `src/continuum/storage/sqlite.py` (WAL, `synchronous=FULL`, schema v6) y `src/continuum/storage/postgres.py` más `src/continuum/storage/migrations.py`, checkpoints dirigidos por políticas `src/continuum/checkpoint/manager.py` y `src/continuum/checkpoint/policy.py` que reproducen el hueco en `restore()`. Recorrido en `docs/recovery_walkthrough.md` (salida de `examples/recovery_walkthrough.py`). |
| Plano de control | Qué ejecución está activa, quién puede actuar sobre ella y a dónde va la salida? | Registro de ejecuciones y jerarquía padre/hijo `src/continuum/storage/` y `src/continuum/recovery/family.py` (`continuum tree`), autorización allowlist `src/continuum/mcp/authz.py` (`CONTINUUM_MCP_MUTATING_CLIENTS` / `CONTINUUM_MCP_TOKEN`), superficies de presentación `src/continuum/dashboard/app.py` y `src/continuum/serve/server.py`, CLI `src/continuum/cli/main.py` (`continuum runs`, `continuum tree`, `continuum health`). |
| Sustrato de verificación | Dado el checkpoint en el tiempo T y el mundo tal como está ahora, sigue siendo seguro y correcto continuar? | `src/continuum/state/validator.py` (obsolescencia `dependency -> evidence -> finding -> decision` más `PlanStep.depends_on`), `src/continuum/provenance_map.py` (`Origin` a `REQUIRES_REVIEW` hasta `REVIEW_CONFIRMED`), `src/continuum/actions/ledger.py` con `src/continuum/actions/idempotency.py` y `src/continuum/gate.py` / `src/continuum/gateway.py` (reclamar antes de ejecutar, rechaza duplicados, lanza `UnknownSideEffect` para reconciliación), `src/continuum/replayguard.py` (guardia portable), `src/continuum/pinning.py` y `src/continuum/replay_similarity.py` (corrección de reproducción), `src/continuum/budgets.py` (límites de reintentos), `src/continuum/recovery/engine.py` + `src/continuum/recovery/contract.py` + `src/continuum/recovery/planner.py` + `src/continuum/recovery/observations.py` (severidad máxima `RESUME < ... < ABORT`, contrato sellado con `evidence` / `reason` / `next_allowed_action` / `human_steps`), `src/continuum/checkpoint/rewind.py` (rebobinado atómico de doble estado), `src/continuum/analysis/prefix_trust.py` (confianza consultiva). Comprobaciones publicadas: `docs/recovery_walkthrough.md`, `benchmarks/fault_injection/` (suite que imprime `detection_rate` / `unsafe_resume_rate`), `src/continuum/benchmark/phase6/` (suite de corrección de recuperación), `docs/RESULTS.md` y el visual regenerable de abajo. |

Cada fila de arriba es rastreable a una ruta que existe en `main` en el commit etiquetado. Nada en esta tabla vuelve a exponer un número de benchmark, los benchmarks solo viven en la salida de la suite que ya los imprime. Consulta `docs/research.md` para la lista completa de suites publicadas y documentos de diseño.

### Recuperación tras caída, de verdad

La imagen de abajo no es una maqueta. Es la salida de `python demo-run/generate_crash_visual.py`, que ejecuta `demo-run/worker.py` hasta `os._exit(9)` en el documento 399, llama a `continuum resume --env dataset=v4` y muestra la ruta de rechazo (`REQUEST_HUMAN`, `safe:false`, exit 20), reconcilia el efecto secundario incierto con una sonda, luego se reanuda desde la misma base de datos y termina sin trabajo duplicado. La transcripción también se guarda como `docs/assets/crash-recovery.txt` para auditoría.

Regenerarlo:

```bash
python demo-run/generate_crash_visual.py
# o: python scripts/generate_crash_visual.py
```

![Recuperación tras caída: muerte brusca a mitad de lote, rechazo, reconciliación, reanudación](docs/assets/crash-recovery.svg)

Recorrido completo con código en `docs/recovery_walkthrough.md` (`examples/recovery_walkthrough.py`). El harness mínimo de bench está en `references/bench.md` (`continuum benchmark`).
