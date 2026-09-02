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

### クラッシュリカバリ、実際に

下の画像はモックではない。`python demo-run/generate_crash_visual.py` の出力であり、`demo-run/worker.py` をドキュメント 399 で `os._exit(9)` まで実行し、`continuum resume --env dataset=v4` を呼び出して拒否パス（`REQUEST_HUMAN`、`safe:false`、exit 20）を示し、不確かな副作用を探査で調停し、同じデータベースから再開して重複作業なしで完了する。トランスクリプトは監査用に `docs/assets/crash-recovery.txt` としても保存される。

再生成：

```bash
python demo-run/generate_crash_visual.py
# または：python scripts/generate_crash_visual.py
```

![クラッシュリカバリ：バッチ途中のハードキル、拒否、調停、再開](docs/assets/crash-recovery.svg)

コード付きの完全なウォークスルーは `docs/recovery_walkthrough.md`（`examples/recovery_walkthrough.py`）にある。最小の bench harness は `references/bench.md`（`continuum benchmark`）にある。

## 機能

| 機能 | 得られるもの |
|:--|:--|
| セマンティックチェックポイント | コンパクトでバージョン管理され、検査可能な状態。トランスクリプトのダンプではない |
| 冪等なアクション台帳 | 重複する外部副作用を拒否し、不確かなものを照合のために浮かび上がらせる |
| 環境の再検証 | 各チェックポイントコンポーネントは再開前に現在の世界に対して検証される |
| 来歴を意識した状態 | エージェントが報告した進捗は `REQUIRES_REVIEW` と印付けされ、自己認証されることはない |
| リカバリエンジン | 決定的で密封された次アクション契約を持つ七つのリカバリモード |
| デフォルトで拒否する MCP サーバー | 十一のツール、読み取りと変更の分離、呼び出し元 allowlist |
| フレームワークアダプター | 汎用 Python、OpenAI Agents SDK、LangGraph、LangChain 統合 |
| 安全な計画ループ | 二信号の観測検証が高リスク分岐を REQUIRES_REVIEW に昇格させる |
| 周期的な再検証 | 環境はスケジュールに従って再チェックされ、実行中のドリフトを一周期以内に捉える |
| 改ざん証跡ログ | ハッシュチェーンイベントログ（36 種のイベントタイプ）と完全性検証 |
| 強制ゲート | 未請求の副作用呼び出しは実行前に拒否され、拒否メッセージがクレームプロトコルを教える |
| 観測フック | コーディング CLI が書き込むすべてのファイルはダイジェスト検証された証拠となり、モデル制御の外にある |
| セッションブリーフィング | 新しいセッションは開始時に実行状態を決定的に学ぶ。前のセッションの推論サマリーを含む |
| 調停プローブ | 登録されたコマンドは不確かな副作用を自動的に決着させ、人間は残りのみを見る |
| 実行可能なガイダンス | Resume と validate は次のステップを実行可能なコマンドとして描画し、状態としてではない |
| 強制 HTTP ゲートウェイ | 任意の言語からの外向き呼び出しはクレームを要し、応答は実際のステータスコードから決着する |
| OpenTelemetry ブリッジ | 本番トレーシングからのツール呼び出しスパンがゼロコード変更で証拠になる |
| アクションインデックス | 実行を跨ぐ冪等性検索はインデックス化された読み取りであり、全ログスキャンではない |
| バージョンピン留め | 呼び出し元が主張した prompt、ツール、モデルハッシュがクレームごとに保存され、ドリフトは再開時に表面化する |
| リトライ予算 | アクションタイプごとの試行上限がクレーム時に強制され、エージェントは残り試行回数を見る |
| マルチエージェントの親子 | 親の再開は家族の最悪状態を合成し、不確かな子が親をブロックする |
| 情報付きリトライ | エンジンが作成した失敗サマリーがリカバリ後の再開に注入される |
| フォークセマンティクス | 発散する継続は新鮮な権限を持つ子実行に分岐する |
| ログ圧縮 | アンカー前の接頭辞は verbatim でアーカイブされ、ライブログは数ヶ月にわたる実行でも有界に保たれる |
| 消費済み付与の追跡 | 一度きりの権限参照は終端状態で消費済みとして印付けされ、復元後の再利用は拒否される（`GRANT_DENIED`）。チェックポイント復元パスでの権限復活を防御する |
| チェーン証明 | `continuum attest` は Ed25519 で実行のチェーンヘッドに署名し、外部検証者が既知の鍵で履歴が改ざんされていないことを証明できる |
| HITL ダッシュボード | 監査が CLI と同等の確認、照合、完了ボタン |

## セキュリティ拡張

二つの加算的なセキュリティ拡張がリカバリとチェックポイント基盤の上に位置する。它们は再開、再生、または既存のクラッシュ時再検証パスを変更しない。

- **安全な計画ループ**：観測は来歴を持ち、二つの独立した信号で検証される（`verified` / `unverified` / `contested`）。未検証または競合する観測によってガードされた計画分岐は `REQUIRES_REVIEW` に昇格する。決定は台帳に `PERCEPTION_OBSERVED` と `BRANCH_RESOLVED` イベントとして追記される。
- **周期的な再検証**：リカバリエンジンをステップ間隔（デフォルト 25）とアプリ切り替え時に再利用し、実行中の環境ドリフトを一周期以内に捉える。次のクラッシュまで待たない。

[docs/PROBLEM.md](docs/PROBLEM.md)、[docs/RESULTS.md](docs/RESULTS.md)、[STATUS.md](STATUS.md) を参照。

## 実証的検証

CONTINUUM はモックの単体テストだけでなく、実際の LLM エージェント、ライブのプロトコル境界、ハードなプロセスクラッシュに対して検証される。

- **実際のエージェント**：実行中に `SIGKILL` された Claude Code による複数セッションの請求書バッチ。メカニクスで 7/7 を獲得。再開セッションは `continuum_resume` を照会し、二段階台帳で副作用を経路付け、検証済み書き込みの重複を拒否し、`request_human` を尊重した。ライブテストはプロンプトドリフトの重複排除ギャップを露わにし、`ActionLedger.claim()` における正規パス正規化とトークンベースのフォールバックで閉じられた。
- **サードパーティクライアント**：Gemini CLI と Kilo Code が stdio JSON-RPC でライブ SQLite ストアに対して接続し、マルチエージェント共存と認可の分離を検証。
- **プロトコル準拠**：`@modelcontextprotocol/inspector --cli` でプロセス死を跨いで端から端まで駆動。変更ツールはデフォルトで `CONTINUUM_MCP_MUTATING_CLIENTS` の背後で拒否され、外部クレームは `REQUIRES_REVIEW`（`safe: false`）に降格する。
- **自己修復**：ハードキルされたサーバーは起動時に一度だけのリトライで孤立した SQLite `-wal`/`-shm` サイドカーをクリーンアップして回復する。
- **スケール**：約 1,380 件のテストが収集され（約 1,360 が通過、残りはオプションサービスなしでスキップ）、Python 3.11、3.12、3.13 で実行（unit、`hypothesis` によるプロパティベース、並行性、敵対的）。CONTINUUM-Bench は五つのクラッシュシナリオに加え専用の argument-drift シナリオを実行し、CONTINUUM について 0 の重複作業と 0 の重複副作用を、単純な再生については完全な重複を測定する。さらに 12 シナリオのリカバリ正確性スイート（`continuum.benchmark.phase6`）が耐久実行サーベイのクラッシュポイントを実行可能なアサーションとして符号化する。
- **敵対的監査**：完全な MCP 面がライブプロトコル上で監査され、三つの欠陥が見つかり修正された。手法と再現手順は [test.md](test.md) にある。

## MCP 統合

CONTINUUM は MCP サーバーを提供する。エージェントはライブラリを埋め込むことなく進捗を記録し、チェックポイントを作成し、副作用を台帳経由で経路付けできる。

```bash
uv pip install -e ".[mcp]"
CONTINUUM_MCP_MUTATING_CLIENTS=your-client-name continuum-mcp
```

stdio 経由の十一のツール。三つは読み取り専用（`continuum_validate`、`continuum_resume`、`continuum_list_actions`）、八つは変更する。副作用は二段階（クレーム、実行、完了）であり、変更ツールはデフォルトで allowlist の背後で拒否される。エージェントが報告した状態は来歴 `Origin.EXTERNAL_AGENT` で記録され `REQUIRES_REVIEW` と印付けされる。

検証の詳細（起動時のクラッシュリカバリや Claude Code による端から端のテストを含む）は [references/mcp.md](references/mcp.md) にある。登録済みサーバーが `CONNECTION_CLOSED` を報告した場合、原因はほぼ常に `PATH` 解決でありサーバー自身ではない。[docs/api/mcp.md](docs/api/mcp.md#troubleshooting) に診断と二つの是正策がある。

## フレームワーク統合

九つのアダプターが `src/continuum/adapters/` に提供される（一つのインプロセスファサードに加え八つの統合）。すべてオプションインストールのためコアは標準ライブラリのみのままである。

| アダプター | クラス | 備考 |
|:--|:--|:--|
| 汎用 Python エージェント | `GenericAgentAdapter` | インプロセスファサード。信頼できる（`Origin.DETERMINISTIC`）状態を書き込む。 |
| ファイルシステムサンドボックス | `FilesystemSandboxAdapter` | ローカルディレクトリサンドボックス。外部サービスなし。ドキュメントと CI のデフォルト。 |
| Python インプロセス | `PythonInProcAdapter` | 一時作業ディレクトリで Python を実行し、台帳経由で記録する。 |
| コンテナ | `ContainerAdapter` | Docker ベース。`docker` 不在時はガード付きスキップ。 |
| ブラウザ | `BrowserAdapter` | Playwright ベース。未インストール時はガード付きスキップ。 |
| Kubernetes | `KubernetesAdapter` | `kubectl` ベース。未設定時はガード付きスキップ。 |
| OpenAI Agents SDK | `OpenAIAgentAdapter` | 実験的。`ToolContext` / `RunHooks` にフック。オプション `openai-agents`。 |
| LangGraph | `LangGraphAgentAdapter` | 実験的。`StateGraph` をラップ。オプション `langgraph`。 |
| LangChain | `LangChainAgentAdapter` | 実験的。LCEL `Runnable` パイプラインと `create_agent` ツール呼び出しループに `checkpoint_node` を落とす。オプション `langchain`。 |

各アダプターは台帳経由で進捗を記録し、二段階のインターセプトと完了プロトコルで外部効果を経路付ける。三つのフレームワークアダプターはすべて端から端の統合テストを持ち、**ライブの OpenRouter モデル** に対して駆動され、その実行で LLM 引数ドリフトの重複排除ギャップと二つの OpenAI アダプター欠陥（アダプターごとのライブのハードクラッシュ（副作用の最中の `os._exit(137)`）証明を含む）が露わになり閉じられた。完全な使用法、ライブモデル結果、実行可能な例は [references/adapters.md](references/adapters.md) にある。

本番の LangGraph アプリはネイティブな永続化 API を維持することもできる。`make_continuum_checkpointer(storage)` は LangGraph の `BaseCheckpointSaver` を CONTINUUM ストレージ上で実装する。したがって各 put は同じハッシュチェーンで来歴タグ付けされたイベントログに着地する（[references/adapters.md](references/adapters.md) を参照）。

さらに三つの本番フレームワークが [`adapters/thin.py`](src/continuum/adapters/thin.py) の SDK 不要な薄いフック面でカバーされる。

| フレームワーク | インターセプト面 | エントリーポイント |
|:--|:--|:--|
| CrewAI | グローバルなツール呼び出し前後のフック | `install_crewai_hooks(storage, run_id)` |
| AutoGen core | `FunctionTool.run_json` をその場でラップ | `wrap_autogen_tool(tool, storage, run_id)` |
| Pydantic AI | 非同期 Hooks ケーパビリティ | `Agent(capabilities=[wrap_pydantic_ai_hooks(storage, run_id)])` |

これらのいずれにも届かないスタックでは：`continuum gateway` が任意の言語からの外向き HTTP にクレームを強制し、`continuum.otel.make_span_processor(storage)` が既存の OpenTelemetry ツールスパンを証拠に変え、`continuum serve` が MCP ツールと同じ操作を言語非依存の JSON ワイヤプロトコルで公開する（stdio、または `--transport http` による HTTP と `CONTINUUM_SERVE_TOKEN` 認証）。

### エージェントまたは MCP が報告した実行の再開

MCP 経由、または OpenAI アダプター経由で報告された状態は来歴 `Origin.EXTERNAL_AGENT` を持ち、`request_human` に解決されるまで確認されない。LangGraph と LangChain の実行は `Origin.DETERMINISTIC` を使い直接再開する。レビューをクリアして再開するには：

```bash
continuum confirm <run_id>   # REVIEW_CONFIRMED を記録し、再評価する
continuum resume <run_id>    # 今度は RESUME を報告する
```

MCP 上では同等物が `continuum_confirm` ツールの後の `continuum_resume` である。確認は一回限りの人間による証明イベントであり、自己認証の安全性の逃げ道である。したがって外部駆動の実行が永続的に詰まることはない。

## コアコンセプト

各コンセプトの深いリファレンスは [references/concepts.md](references/concepts.md) にある。

- **セマンティックチェックポイント**、エージェントが継続するために必要なコンパクトでバージョン管理された表現。
- **状態検証**、各コンポーネントが独立して検証され、陳腐化は依存グラフを通じて伝播する。
- **冪等なアクション台帳**、外部副作用が追跡され重複排除され、不確かな結果は静かに再試行されるのではなく送出される。
- **リカバリモード**、`RESUME`、`REPAIR_AND_RESUME`、`ROLLBACK`、`WAIT`、`REQUEST_HUMAN`、`ABORT`（さらに `REPLAN`）。
- **リカバリ契約**、決定的で完全性が封印され、ゲートされた次のアクション。
