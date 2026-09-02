<p align="center">
  <img src="docs/assets/readme-img.png" alt="CONTINUUM 横幅" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM：面向长时间运行 AI 智能体的可验证语义恢复。</strong>
  语义检查点（而非对话转储）、拒绝重复副作用的幂等动作账本，以及哈希链防篡改事件日志，全部通过默认拒绝的 MCP 服务器暴露。框架无关，支持 Python 3.11+。
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://pypi.org/project/continuum-agent/"><img src="https://img.shields.io/pypi/v/continuum-agent?style=flat-square&label=PyPI" alt="PyPI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="CI 状态" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center" style="margin-bottom: 6px;">
  <a href="https://continuum-nu-six.vercel.app/"><strong>访问 CONTINUUM 网站</strong></a>
</p>

<p align="center" style="margin-top: 6px;">
  <a href="https://app.ona.com/#https://github.com/Cyrax321/CONTINUUM"><img src="https://ona.com/build-with-ona.svg" alt="Build with Ona" /></a>
</p>

<p align="center">
  <sub>如果 CONTINUUM 帮助你的智能体可靠恢复，请为本仓库点亮 Star，这能帮助更多人发现它并持续带来优质的 good first issue。</sub>
</p>

<p align="center">
  <sub>English | <a href="README.md">English</a> | <strong>简体中文</strong></sub>
</p>

---

## 目录

[为什么](#为什么) · [快速开始](#快速开始) · [工作原理](#工作原理) · [CONTINUUM 的位置](#continuum-的位置) · [功能特性](#功能特性) · [安全扩展](#安全扩展) · [实证验证](#实证验证) · [MCP 集成](#mcp-集成) · [框架集成](#框架集成) · [核心概念](#核心概念) · [架构](#架构) · [API 和 CLI](#api-和-cli) · [路线图](#路线图) · [CONTINUUM 不是什么](#continuum-不是什么) · [相关工作](#相关工作) · [状态与局限](#状态与局限) · [贡献](#贡献) · [许可证](#许可证)

---

## 为什么

现代 AI 智能体执行长时间任务（数百次 LLM 调用、工具调用、文件和数据库写入）。当它们崩溃时，常见的处理方式是从头开始重放，这会重复工作、重复副作用、浪费 token 并丢失决策。

CONTINUUM 提出一个更窄但更难的问题：智能体能否从任务状态的紧凑语义表示中恢复，同时独立验证该状态在当前环境中仍然有效？其差异化体现在三部分：

- **语义检查点**：所需继续执行的最小化、带版本的紧凑表示，而非对话转储。
- **独立的环境重验证**：恢复前每个检查点组件都会对照当前环境进行验证，过期状态会通过依赖图传播。
- **可溯源的状态**：每个事实都可追溯到其来源，因此智能体报告的进度永远不会自我认证。

## 快速开始

以 `continuum-agent` 0.1.0 发布至 PyPI，执行 `pip install continuum-agent` 即可（固定版本请用 `pip install continuum-agent==0.1.0`）。发布标签还会将构建好的 wheel 附加到 [GitHub Releases](https://github.com/Cyrax321/CONTINUUM/releases)。

零配置路径（无需克隆、无需安装、无需发布）：

| 路径 | 方法 |
|:--|:--|
| 从 PyPI 安装 | `pip install continuum-agent==0.1.0`，然后执行 `continuum --help` |
| 端到端观看崩溃恢复 | `docker run --rm ghcr.io/cyrax321/continuum` |
| 通过 Docker 使用 CLI | `docker run --rm ghcr.io/cyrax321/continuum continuum --help` |
| 无需克隆即可运行 CLI | `uvx --from git+https://github.com/Cyrax321/CONTINUUM.git continuum --help` |
| Windows PowerShell（在克隆中） | `powershell -ExecutionPolicy Bypass -File .\try-it.ps1` 或 `powershell -ExecutionPolicy Bypass -File .\try-it.ps1 cli --help` |
| 浏览器中的完整开发环境 | [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Cyrax321/CONTINUUM?quickstart=1) |

Docker 镜像由 CI 在每次推送到 `main` 和每个发布标签时发布到 GHCR（`.github/workflows/docker-publish.yml`）。Codespace 在 `.devcontainer/` 中定义。

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM

uv venv && source .venv/bin/activate     # macOS / Linux; Windows: .venv\Scripts\activate

# 贡献者（推荐）：库 + CLI + 全部测试工具 + 全部适配器
uv pip install -e ".[dev]"

# 或按需选择：.（最小）、[mcp]、[otel]、[langgraph]、
# [openai]、[langchain]、[attest]、[postgres]

# 或完全跳过克隆：
uv pip install git+https://github.com/Cyrax321/CONTINUUM.git
uv pip install "continuum-agent[mcp] @ git+https://github.com/Cyrax321/CONTINUUM.git"
```

> **pip 回退：** 将上面所有命令中的 `uv pip install` 替换为 `pip install`。

验证：

```bash
continuum --help                 # CLI 入口
continuum-mcp --help             # MCP 服务器入口（需要 [mcp] 或 [dev]）
pytest -q                        # 约 1,380 个用例被收集（具体数量和跳过数因环境而异）
ruff check src/ tests/ examples/ && ruff format --check src/ tests/ examples/
mypy src/continuum               # CI 强制的三扇门禁
```

核心库只有一个运行时依赖（`pydantic>=2.7`），其余均为可选。完整的包映射、extras 矩阵、Postgres 测试配置和按命令验证说明见 [references/install.md](references/install.md)。

### 两分钟接入编码智能体

对于 Claude Code、Gemini CLI 或 Codex，你无需编写 Python 也无需提示词文件：

```bash
continuum start my-task --goal "智能体应该做什么"
continuum hooks install claude-code --with-gate   # 同样支持：gemini、codex
```

此后智能体写入的每个文件都会被捕获为哈希链证据，会话开始时自动获得状态简报，在 `.continuum/gate.json` 中注册的未声明副作用会在触发前被拒绝，而任何崩溃后的全新会话都会带着可执行的下一步恢复。无需 CLAUDE.md。

最小化库示例，记录与恢复：

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="分析 10,000 份文档"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "分析 10,000 份文档", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# 崩溃后，新进程从停止的地方精确接续：
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # 已完成，不会重复
print(store.verify_events("run_4821").ok)  # True，崩溃后链仍然完整
```

**亲自运行验证：**

```bash
python examples/crash_recovery_agent.py   # 真实进程杀死，真实副作用
python examples/context_compaction.py     # 转录丢失，检查点存活
python examples/model_switch.py           # 模型 A 死亡，模型 B 安全接管
python scripts/mcp_smoke.py               # 真实子进程，真实 JSON-RPC 流量
```

`e2e-autonomy-test/` 套件脚本化了一个真实的发票批量任务、在运行中硬杀，以及全新的恢复会话，然后在带外对 outbox、账本和事件链进行评分。Run 1 对真实的 Claude Code 会话取得了 **7/7 机制** 评分。完整 walkthrough 见 [references/e2e.md](references/e2e.md)。

## 工作原理

CONTINUUM 将 **LLM 上下文**（临时）与 **持久任务状态**（永久）分离开来。它不保存对话历史，而是构造语义检查点，即继续执行所需的最小化已验证信息。

![CONTINUUM 工作原理](docs/assets/architecture.svg)

详细说明、投影模型和恢复上下文见 [references/architecture.md](references/architecture.md)。

## CONTINUUM 的位置

四个关注点在每个长时间运行的智能体中重叠。CONTINUUM 只拥有最后一项，并通过显式接缝触及其他三项。不点名任何竞品，也不做没有已交付模块或已发布套件支撑的主张。

| 层 | 回答的问题 | 如何连接（已交付模块或已发布输出） |
|:--|:--|:--|
| Harness | 智能体如何调用工具并朝目标推进？ | 在 CONTINUUM 之外。接线点在 `src/continuum/adapters/generic.py`（`GenericAgentAdapter`）、`src/continuum/adapters/thin.py`（CrewAI、AutoGen、Pydantic AI 钩子）、`src/continuum/mcp/server.py`（MCP stdio）、`src/continuum/hooks.py` 和 `src/continuum/clienthooks.py`（编码 CLI 生命周期钩子）、`src/continuum/gateway.py`（面向任意语言的强制 HTTP 代理）和 `src/continuum/otel.py`（OpenTelemetry 桥）中交付。配方见 `docs/recipes/` 和 `references/adapters.md`。 |
| 持久执行 | 崩溃前发生了什么，哪些工作可以在不丢失的情况下重放？ | 哈希链事件日志 `src/continuum/events.py` 带 `verify()` 和 `trusted_through`，持久存储 `src/continuum/storage/sqlite.py`（WAL，`synchronous=FULL`，schema v6）和 `src/continuum/storage/postgres.py` 加上 `src/continuum/storage/migrations.py`，策略驱动的检查点 `src/continuum/checkpoint/manager.py` 和 `src/continuum/checkpoint/policy.py` 在 `restore()` 时重放间隔。Walkthrough 在 `docs/recovery_walkthrough.md`（`examples/recovery_walkthrough.py` 的输出）中。 |
| 控制面 | 哪个 run 处于活动状态、谁可以操作它、输出去向何处？ | Run 注册表和父子层级 `src/continuum/storage/` 与 `src/continuum/recovery/family.py`（`continuum tree`），allowlist 鉴权 `src/continuum/mcp/authz.py`（`CONTINUUM_MCP_MUTATING_CLIENTS` / `CONTINUUM_MCP_TOKEN`），展示面 `src/continuum/dashboard/app.py` 和 `src/continuum/serve/server.py`，CLI `src/continuum/cli/main.py`（`continuum runs`、`continuum tree`、`continuum health`）。 |
| 验证基座 | 给定时间 T 的检查点和当下的世界，继续是否仍然安全和正确？ | `src/continuum/state/validator.py`（过期性 `dependency -> evidence -> finding -> decision` 加上 `PlanStep.depends_on`）、`src/continuum/provenance_map.py`（`Origin` 到 `REQUIRES_REVIEW` 直至 `REVIEW_CONFIRMED`）、`src/continuum/actions/ledger.py` 配合 `src/continuum/actions/idempotency.py` 与 `src/continuum/gate.py` / `src/continuum/gateway.py`（先声明再触发，拒绝重复并为对账抛出 `UnknownSideEffect`）、`src/continuum/replayguard.py`（可移植守卫）、`src/continuum/pinning.py` 与 `src/continuum/replay_similarity.py`（重放正确性）、`src/continuum/budgets.py`（重试上限）、`src/continuum/recovery/engine.py` + `src/continuum/recovery/contract.py` + `src/continuum/recovery/planner.py` + `src/continuum/recovery/observations.py`（最大严重度 `RESUME < ... < ABORT`，带 `evidence` / `reason` / `next_allowed_action` / `human_steps` 的密封合约）、`src/continuum/checkpoint/rewind.py`（原子双状态回滚）、`src/continuum/analysis/prefix_trust.py`（建议性信任）。已发布的检查：`docs/recovery_walkthrough.md`、`benchmarks/fault_injection/`（打印 `detection_rate` / `unsafe_resume_rate` 的套件）、`src/continuum/benchmark/phase6/`（恢复正确性套件）、`docs/RESULTS.md` 以及下方可再生的可视化。 |

该表中的每一行都可在打标签的提交上追溯到 `main` 上存在的路径。表格中不复述任何基准数字，基准只活在已打印它们的套件输出中。完整的已发布套件和设计文档列表见 `docs/research.md`。
