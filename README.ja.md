<p align="center">
  <img src="docs/assets/readme-img.png" alt="CONTINUUM バナー" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM: 長時間実行される AI エージェントのための検証可能な意味的リカバリ。</strong>
  セマンティックチェックポイント（会話のダンプではない）、重複する副作用を拒否する冪等なアクション台帳、
  そしてハッシュチェーンによる改ざん証跡ログを、デフォルトで拒否する MCP サーバーとして公開。フレームワーク非依存、Python 3.11+。
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://pypi.org/project/continuum-agent/"><img src="https://img.shields.io/pypi/v/continuum-agent?style=flat-square&label=PyPI" alt="PyPI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="CI 状態" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center" style="margin-bottom: 6px;">
  <a href="https://continuum-nu-six.vercel.app/"><strong>CONTINUUM ウェブサイトを見る</strong></a>
</p>

<p align="center" style="margin-top: 6px;">
  <a href="https://app.ona.com/#https://github.com/Cyrax321/CONTINUUM"><img src="https://ona.com/build-with-ona.svg" alt="Build with Ona" /></a>
</p>

<p align="center">
  <sub>CONTINUUM がエージェントの復旧に役立ったなら、リポジトリにスターを付けてください。他の人が見つけやすくなり、良い first issue が届き続けます。</sub>
</p>

<p align="center">
  <sub><a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a> | <strong>日本語</strong></sub>
</p>

---

## 目次

[なぜ](#なぜ) · [クイックスタート](#クイックスタート) · [仕組み](#仕組み) · [CONTINUUM の位置づけ](#continuum-の位置づけ) · [機能](#機能) · [セキュリティ拡張](#セキュリティ拡張) · [実証的検証](#実証的検証) · [MCP 統合](#mcp-統合) · [フレームワーク統合](#フレームワーク統合) · [コアコンセプト](#コアコンセプト) · [アーキテクチャ](#アーキテクチャ) · [API と CLI](#api-と-cli) · [ロードマップ](#ロードマップ) · [CONTINUUM ではないもの](#continuum-ではないもの) · [関連研究](#関連研究) · [ステータスと制限](#ステータスと制限) · [コントリビューション](#コントリビューション) · [ライセンス](#ライセンス)

---

## なぜ

現代の AI エージェントは長時間タスクを実行します（数百回の LLM 呼び出し、ツール呼び出し、ファイルやデータベースへの書き込み）。クラッシュしたとき、従来の対応はすべてを最初から再生することであり、これは作業を重複させ、副作用を重複させ、トークンを浪費し、意思決定を失わせます。

CONTINUUM はより狭く、より難しい問いを立てます。エージェントはタスク状態のコンパクトな意味的表現から再開しつつ、その状態が現在の環境で依然として有効であることを独立して検証できるか。その差別化は三つの部分にあります。

- **セマンティックチェックポイント**：エージェントが継続するために必要なコンパクトでバージョン管理された表現であり、会話のダンプではない。
- **独立した環境の再検証**：各チェックポイントコンポーネントは再開前に現在の環境に対して検証され、陳腐化は依存グラフを通じて伝播する。
- **来歴を意識した状態**：すべての事実はその起源をたどることができ、エージェントが報告した進捗が自己認証されることは決してない。

## クイックスタート

PyPI に `continuum-agent` 0.1.0 として公開。`pip install continuum-agent` を実行（固定する場合は `pip install continuum-agent==0.1.0`）。リリースタグではビルド済み wheel が [GitHub Releases](https://github.com/Cyrax321/CONTINUUM/releases) に添付される。

ゼロセットアップのパス（クローンもインストールも公開も不要）：

| パス | 方法 |
|:--|:--|
| PyPI からインストール | `pip install continuum-agent==0.1.0` してから `continuum --help` |
| クラッシュリカバリを端から端まで見る | `docker run --rm ghcr.io/cyrax321/continuum` |
| Docker 経由で CLI を使う | `docker run --rm ghcr.io/cyrax321/continuum continuum --help` |
| クローンせずに CLI を実行 | `uvx --from git+https://github.com/Cyrax321/CONTINUUM.git continuum --help` |
| Windows PowerShell（クローン内） | `powershell -ExecutionPolicy Bypass -File .\try-it.ps1` または `powershell -ExecutionPolicy Bypass -File .\try-it.ps1 cli --help` |
| ブラウザで完全な開発環境 | [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Cyrax321/CONTINUUM?quickstart=1) |

Docker イメージは CI によって `main` への各 push と各リリースタグで GHCR に公開される（`.github/workflows/docker-publish.yml`）。Codespace は `.devcontainer/` で定義される。

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM

uv venv && source .venv/bin/activate     # macOS / Linux; Windows: .venv\Scripts\activate

# コントリビューター（推奨）：ライブラリ + CLI + すべてのテストツール + すべてのアダプター
uv pip install -e ".[dev]"

# または必要なものだけを選ぶ：.（最小）、[mcp]、[otel]、[langgraph]、
# [openai]、[langchain]、[attest]、[postgres]

# またはクローンを完全にスキップ：
uv pip install git+https://github.com/Cyrax321/CONTINUUM.git
uv pip install "continuum-agent[mcp] @ git+https://github.com/Cyrax321/CONTINUUM.git"
```

> **pip フォールバック：** 上記のすべてのコマンドで `uv pip install` を `pip install` に置き換えてください。

検証：

```bash
continuum --help                 # CLI エントリーポイント
continuum-mcp --help             # MCP サーバーエントリーポイント（[mcp] または [dev] が必要）
pytest -q                        # 約 1,380 件が収集される（正確な数とスキップ数は環境により異なる）
ruff check src/ tests/ examples/ && ruff format --check src/ tests/ examples/
mypy src/continuum               # CI が強制する三つのゲート
```

コアライブラリは一つのランタイム依存（`pydantic>=2.7`）のみを持ち、残りはすべてオプションである。完全なパッケージマップ、extras 行列、Postgres テスト設定、コマンドごとの検証は [references/install.md](references/install.md) にある。

### コーディングエージェントを2分で接続

Claude Code、Gemini CLI、または Codex の場合、Python を書く必要もプロンプトファイルも不要である。

```bash
continuum start my-task --goal "エージェントにやらせたいこと"
continuum hooks install claude-code --with-gate   # 同様に：gemini、codex
```

それ以降、エージェントが書き込むすべてのファイルはハッシュチェーン証拠としてキャプチャされ、セッション開始時に自動的に状態ブリーフィングが入り、`.continuum/gate.json` に登録された未請求の副作用は実行前に拒否され、どんなクラッシュ後の新しいセッションも実行可能な次のステップで再開する。CLAUDE.md は不要である。

最小限のライブラリ例。記録とリカバリ：

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="10,000 ドキュメントを分析"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "10,000 ドキュメントを分析", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# クラッシュ後、新しいプロセスは停止した場所から正確に再開する：
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # すでに完了、繰り返さない
print(store.verify_events("run_4821").ok)  # True、クラッシュ後もチェーンは無傷
```

**自分で証明を実行：**

```bash
python examples/crash_recovery_agent.py   # 実際のプロセスキル、実際の副作用
python examples/context_compaction.py     # トランスクリプト喪失、チェックポイントは生存
python examples/model_switch.py           # モデル A が死亡、モデル B が安全に引き継ぎ
python scripts/mcp_smoke.py               # 実際の子プロセス、実際の JSON-RPC トラフィック
```

`e2e-autonomy-test/` キットは実際の請求書バッチタスク、実行中のハードキル、そして新しい再開セッションをスクリプト化し、その後 outbox、台帳、イベントチェーンを帯域外で採点する。実行 1 は実際の Claude Code セッションで **7/7 のメカニクス** を獲得した。完全なウォークスルーは [references/e2e.md](references/e2e.md) にある。

## 仕組み

CONTINUUM は **LLM コンテキスト**（一時的）と **永続的なタスク状態**（永続的）を分離する。会話履歴を保存する代わりに、継続するために必要な最小限の検証済み情報であるセマンティックチェックポイントを構築する。

![CONTINUUM の仕組み](docs/assets/architecture.svg)

詳細な説明、投影モデル、リカバリコンテキストは [references/architecture.md](references/architecture.md) にある。

## CONTINUUM の位置づけ

四つの関心事が長時間実行されるすべてのエージェントで重なる。CONTINUUM は最後の一つだけを所有し、他の三つには明示的な継ぎ目を通じて触れる。競合を名指しすることも、提供済みモジュールや公開済みスイートが既に印字していない主張をすることもない。

| レイヤー | 問いに答える | 接続方法（提供済みモジュールまたは公開済み出力） |
|:--|:--|:--|
| Harness | エージェントはどのようにツールを呼び出し目標に向かって進むか | CONTINUUM の外。接続点は `src/continuum/adapters/generic.py`（`GenericAgentAdapter`）、`src/continuum/adapters/thin.py`（CrewAI、AutoGen、Pydantic AI フック）、`src/continuum/mcp/server.py`（MCP stdio）、`src/continuum/hooks.py` と `src/continuum/clienthooks.py`（コーディング CLI ライフサイクルフック）、`src/continuum/gateway.py`（任意の言語向け強制 HTTP プロキシ）、`src/continuum/otel.py`（OpenTelemetry ブリッジ）で提供。レシピは `docs/recipes/` と `references/adapters.md` にある。 |
| 耐久実行 | クラッシュ前に何が起こり、何が失われずに再生できるか | ハッシュチェーンイベントログ `src/continuum/events.py` と `verify()` と `trusted_through`、永続ストレージ `src/continuum/storage/sqlite.py`（WAL、`synchronous=FULL`、schema v6）と `src/continuum/storage/postgres.py` に加え `src/continuum/storage/migrations.py`、ポリシー駆動チェックポイント `src/continuum/checkpoint/manager.py` と `src/continuum/checkpoint/policy.py` が `restore()` でギャップを再生。ウォークスルーは `docs/recovery_walkthrough.md`（`examples/recovery_walkthrough.py` の出力）にある。 |
| コントロールプレーン | どの実行がアクティブで、誰がそれに作用でき、出力はどこへ行くか | 実行レジストリと親子階層 `src/continuum/storage/` と `src/continuum/recovery/family.py`（`continuum tree`）、allowlist 認可 `src/continuum/mcp/authz.py`（`CONTINUUM_MCP_MUTATING_CLIENTS` / `CONTINUUM_MCP_TOKEN`）、表示面 `src/continuum/dashboard/app.py` と `src/continuum/serve/server.py`、CLI `src/continuum/cli/main.py`（`continuum runs`、`continuum tree`、`continuum health`）。 |
| 検証基盤 | 時刻 T のチェックポイントと今の世界が与えられたとき、継続しても安全かつ正確か | `src/continuum/state/validator.py`（陳腐化 `dependency -> evidence -> finding -> decision` に加え `PlanStep.depends_on`）、`src/continuum/provenance_map.py`（`Origin` から `REQUIRES_REVIEW` まで `REVIEW_CONFIRMED` まで）、`src/continuum/actions/ledger.py` と `src/continuum/actions/idempotency.py` および `src/continuum/gate.py` / `src/continuum/gateway.py`（実行前にクレーム、重複を拒否し、照合のために `UnknownSideEffect` を送出）、`src/continuum/replayguard.py`（ポータブルガード）、`src/continuum/pinning.py` と `src/continuum/replay_similarity.py`（再生の正確性）、`src/continuum/budgets.py`（リトライ上限）、`src/continuum/recovery/engine.py` + `src/continuum/recovery/contract.py` + `src/continuum/recovery/planner.py` + `src/continuum/recovery/observations.py`（最大深刻度 `RESUME < ... < ABORT`、`evidence` / `reason` / `next_allowed_action` / `human_steps` を持つ密封契約）、`src/continuum/checkpoint/rewind.py`（アトミックな二重状態巻き戻し）、`src/continuum/analysis/prefix_trust.py`（助言的信頼）。公開済みチェック：`docs/recovery_walkthrough.md`、`benchmarks/fault_injection/`（`detection_rate` / `unsafe_resume_rate` を印字するスイート）、`src/continuum/benchmark/phase6/`（リカバリ正確性スイート）、`docs/RESULTS.md`、そして下の再生成可能なビジュアル。 |

上記の各行は、タグ付けされたコミット時点で `main` に存在するパスに追跡可能である。この表ではベンチマーク数値を再掲しない。ベンチマークはそれらを既に印字したスイート出力の中にのみ生きる。公開済みスイートと設計文書の完全なリストは `docs/research.md` にある。
