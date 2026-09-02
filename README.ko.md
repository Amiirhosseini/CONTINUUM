<p align="center">
  <img src="docs/assets/readme-img.png" alt="CONTINUUM 배너" width="100%" />
</p>

<p align="center">
  <strong>CONTINUUM: 장시간 실행되는 AI 에이전트를 위한 검증 가능한 의미론적 복구.</strong>
  시맨틱 체크포인트(대화 덤프가 아님), 중복된 사이드 이펙트를 거부하는 멱등한 액션 원장,
  그리고 해시 체인 기반의 변조 증거 로그를, 기본적으로 거부하는 MCP 서버로 노출한다. 프레임워크에 구애받지 않으며, Python 3.11+를 지원한다.
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://pypi.org/project/continuum-agent/"><img src="https://img.shields.io/pypi/v/continuum-agent?style=flat-square&label=PyPI" alt="PyPI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-blue?style=flat-square" alt="License" /></a>
  <a href="https://pydantic.dev"><img src="https://img.shields.io/badge/pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white" alt="Pydantic v2" /></a>
  <a href="https://continuum-nu-six.vercel.app/"><img src="https://img.shields.io/badge/website-live_demo-E06D53?style=flat-square" alt="Website Demo" /></a>
  <a href="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml"><img src="https://github.com/Cyrax321/CONTINUUM/actions/workflows/ci.yml/badge.svg" alt="CI 상태" /></a>
  <a href="https://app.codecov.io/gh/Cyrax321/CONTINUUM"><img src="https://img.shields.io/codecov/c/github/Cyrax321/CONTINUUM?style=flat-square&logo=codecov" alt="Coverage" /></a>
</p>

<p align="center" style="margin-bottom: 6px;">
  <a href="https://continuum-nu-six.vercel.app/"><strong>CONTINUUM 웹사이트 방문</strong></a>
</p>

<p align="center" style="margin-top: 6px;">
  <a href="https://app.ona.com/#https://github.com/Cyrax321/CONTINUUM"><img src="https://ona.com/build-with-ona.svg" alt="Build with Ona" /></a>
</p>

<p align="center">
  <sub>CONTINUUM이 에이전트의 복구에 도움이 되었다면, 리포지토리에 스타를 눌러주세요. 더 많은 사람들이 발견하고 좋은 first issue가 계속 제공되는 데 도움이 됩니다.</sub>
</p>

<p align="center">
  <sub><a href="README.md">English</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a> | <a href="README.ja.md">日本語</a> | <a href="README.pt-BR.md">Português</a> | <strong>한국어</strong></sub>
</p>

---

## 목차

[왜](#왜) · [빠른 시작](#빠른-시작) · [작동 방식](#작동-방식) · [CONTINUUM의 위치](#continuum의-위치) · [기능](#기능) · [보안 확장](#보안-확장) · [실증적 검증](#실증적-검증) · [MCP 통합](#mcp-통합) · [프레임워크 통합](#프레임워크-통합) · [핵심 개념](#핵심-개념) · [아키텍처](#아키텍처) · [API와 CLI](#api와-cli) · [로드맵](#로드맵) · [CONTINUUM이 아닌 것](#continuum이-아닌-것) · [관련 연구](#관련-연구) · [상태와 제한](#상태와-제한) · [기여](#기여) · [라이선스](#라이선스)

---

## 왜

현대 AI 에이전트는 긴 작업을 실행한다. 수백 번의 LLM 호출, 도구 호출, 파일 및 데이터베이스 쓰기가 포함된다. 충돌이 발생하면 일반적인 대응은 모든 것을 처음부터 다시 재생하는 것이며, 이는 작업을 중복시키고, 사이드 이펙트를 중복시키며, 토큰을 낭비하고, 결정을 잃게 만든다.

CONTINUUM은 더 좁고 더 어려운 질문을 던진다. 에이전트가 작업 상태의 컴팩트한 의미론적 표현으로부터 재개하면서, 그 상태가 현재 환경에서 여전히 유효한지 독립적으로 검증할 수 있는가. 그 차별화는 세 부분으로 이루어진다.

- **시맨틱 체크포인트**: 에이전트가 계속하는 데 필요한 컴팩트하고 버전 관리된 표현이며, 대화 덤프가 아니다.
- **독립적인 환경 재검증**: 각 체크포인트 구성 요소는 재개 전에 현재 환경에 대해 검증되며, 오래됨은 의존성 그래프를 통해 전파된다.
- **출처를 인식하는 상태**: 모든 사실은 그 기원을 추적하므로, 에이전트가 보고한 진행 상황이 스스로 인증되는 일은 결코 없다.

## 빠른 시작

PyPI에 `continuum-agent` 0.1.0으로 게시됨. `pip install continuum-agent` 실행 (`pip install continuum-agent==0.1.0`으로 고정). 릴리스 태그는 빌드된 wheel을 [GitHub Releases](https://github.com/Cyrax321/CONTINUUM/releases)에 첨부한다.

제로 설정 경로 (클론도, 설치도, 게시도 필요 없음):

| 경로 | 방법 |
|:--|:--|
| PyPI에서 설치 | `pip install continuum-agent==0.1.0` 후 `continuum --help` |
| 크래시 복구를 끝에서 끝까지 보기 | `docker run --rm ghcr.io/cyrax321/continuum` |
| Docker를 통해 CLI 사용 | `docker run --rm ghcr.io/cyrax321/continuum continuum --help` |
| 클론 없이 CLI 실행 | `uvx --from git+https://github.com/Cyrax321/CONTINUUM.git continuum --help` |
| Windows PowerShell (클론 내부) | `powershell -ExecutionPolicy Bypass -File .\try-it.ps1` 또는 `powershell -ExecutionPolicy Bypass -File .\try-it.ps1 cli --help` |
| 브라우저에서 완전한 개발 환경 | [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/Cyrax321/CONTINUUM?quickstart=1) |

Docker 이미지는 CI가 `main`에 대한 각 push와 각 릴리스 태그마다 GHCR에 게시한다 (`.github/workflows/docker-publish.yml`). Codespace는 `.devcontainer/`에 정의되어 있다.

```bash
git clone https://github.com/Cyrax321/CONTINUUM.git
cd CONTINUUM

uv venv && source .venv/bin/activate     # macOS / Linux; Windows: .venv\Scripts\activate

# 기여자 (권장): 라이브러리 + CLI + 모든 테스트 도구 + 모든 어댑터
uv pip install -e ".[dev]"

# 또는 필요한 것만 선택: . (최소), [mcp], [otel], [langgraph],
# [openai], [langchain], [attest], [postgres]

# 또는 클론을 완전히 건너뛰기:
uv pip install git+https://github.com/Cyrax321/CONTINUUM.git
uv pip install "continuum-agent[mcp] @ git+https://github.com/Cyrax321/CONTINUUM.git"
```

> **pip 폴백:** 위의 모든 명령에서 `uv pip install`을 `pip install`로 교체하십시오.

검증:

```bash
continuum --help                 # CLI 진입점
continuum-mcp --help             # MCP 서버 진입점 ([mcp] 또는 [dev] 필요)
pytest -q                        # 약 1,380개 테스트 수집 (정확한 수와 스킵 수는 환경에 따라 다름)
ruff check src/ tests/ examples/ && ruff format --check src/ tests/ examples/
mypy src/continuum               # CI가 강제하는 세 가지 게이트
```

코어 라이브러리는 하나의 런타임 의존성(`pydantic>=2.7`)만 가지며, 나머지는 모두 선택 사항이다. 전체 패키지 맵, extras 행렬, Postgres 테스트 설정, 명령별 검증은 [references/install.md](references/install.md)에 있다.

### 코딩 에이전트를 2분 안에 연결

Claude Code, Gemini CLI 또는 Codex의 경우 Python을 작성할 필요도 없고 프롬프트 파일도 필요하지 않다.

```bash
continuum start my-task --goal "에이전트가 해야 할 일"
continuum hooks install claude-code --with-gate   # 동일하게: gemini, codex
```

그 이후 에이전트가 작성하는 모든 파일은 해시 체인 증거로 캡처되고, 세션 시작 시 자동으로 상태 브리핑이 제공되며, `.continuum/gate.json`에 등록된 청구되지 않은 사이드 이펙트는 실행 전에 거부되고, 어떤 충돌 후의 새로운 세션도 실행 가능한 다음 단계로 재개된다. CLAUDE.md는 필요하지 않다.

최소 라이브러리 예제, 기록과 복구:

```python
from continuum import EventType, Run, SQLiteStorage, project

store = SQLiteStorage("agent.db")
store.create_run(Run(run_id="run_4821", goal="10,000개 문서 분석"))
store.append_event("run_4821", EventType.RUN_STARTED, {"goal": "10,000개 문서 분석", "total": 10_000})

for i, doc in enumerate(documents):
    analyze(doc)
    store.append_event("run_4821", EventType.WORK_COMPLETED, {"doc": i})

# 충돌 후, 새로운 프로세스는 중단된 지점에서 정확히 재개한다:
state = project("run_4821", store.read_events("run_4821"))
print(state.progress.completed)            # 이미 완료, 반복하지 않음
print(store.verify_events("run_4821").ok)  # True, 충돌 후에도 체인은 온전함
```

**직접 증명을 실행:**

```bash
python examples/crash_recovery_agent.py   # 실제 프로세스 킬, 실제 사이드 이펙트
python examples/context_compaction.py     # 트랜스크립트 손실, 체크포인트는 생존
python examples/model_switch.py           # 모델 A 사망, 모델 B가 안전하게 인계
python scripts/mcp_smoke.py               # 실제 서브프로세스, 실제 JSON-RPC 트래픽
```

`e2e-autonomy-test/` 키트는 실제 인보이스 배치 작업, 실행 중 하드킬, 그리고 새로운 재개 세션을 스크립트화한 뒤, outbox, 원장, 이벤트 체인을 대역 외에서 채점한다. 실행 1은 실제 Claude Code 세션에서 **7/7 메커니즘**을 획득했다. 전체 워크스루는 [references/e2e.md](references/e2e.md)에 있다.

## 작동 방식

CONTINUUM은 **LLM 컨텍스트**(일시적)와 **지속적인 작업 상태**(영구적)를 분리한다. 대화 기록을 저장하는 대신, 계속하는 데 필요한 최소한의 검증된 정보인 시맨틱 체크포인트를 구축한다.

![CONTINUUM 작동 방식](docs/assets/architecture.svg)

자세한 설명, 프로젝션 모델, 복구 컨텍스트는 [references/architecture.md](references/architecture.md)에 있다.

## CONTINUUM의 위치

네 가지 관심사가 모든 장시간 실행 에이전트에서 겹친다. CONTINUUM은 마지막 하나만 소유하고, 다른 세 가지는 명시적인 심을 통해 건드린다. 경쟁자를 지명하지 않으며, 제공된 모듈이나 게시된 스위트가 이미 출력하지 않은 주장을 하지 않는다.

| 레이어 | 질문에 답함 | 연결 방법 (제공된 모듈 또는 게시된 출력) |
|:--|:--|:--|
| Harness | 에이전트는 도구를 어떻게 호출하고 목표를 향해 나아가는가 | CONTINUUM 외부. 연결 지점은 `src/continuum/adapters/generic.py`(`GenericAgentAdapter`), `src/continuum/adapters/thin.py`(CrewAI, AutoGen, Pydantic AI 훅), `src/continuum/mcp/server.py`(MCP stdio), `src/continuum/hooks.py`와 `src/continuum/clienthooks.py`(코딩 CLI 수명 주기 훅), `src/continuum/gateway.py`(모든 언어용 강제 HTTP 프록시), `src/continuum/otel.py`(OpenTelemetry 브리지)에서 제공된다. 레시피는 `docs/recipes/`와 `references/adapters.md`에 있다. |
| 내구성 있는 실행 | 충돌 전에 무슨 일이 일어났고, 무엇을 잃지 않고 재생할 수 있는가 | 해시 체인 이벤트 로그 `src/continuum/events.py`와 `verify()`와 `trusted_through`, 영속 저장소 `src/continuum/storage/sqlite.py`(WAL, `synchronous=FULL`, schema v6)와 `src/continuum/storage/postgres.py` plus `src/continuum/storage/migrations.py`, 정책 기반 체크포인트 `src/continuum/checkpoint/manager.py`와 `src/continuum/checkpoint/policy.py`가 `restore()`에서 간격을 재생한다. 워크스루는 `docs/recovery_walkthrough.md`(`examples/recovery_walkthrough.py`의 출력)에 있다. |
| 제어 평면 | 어떤 실행이 활성 상태이며, 누가 그것에 대해 행동할 수 있고, 출력은 어디로 가는가 | 실행 레지스트리와 부모-자식 계층 `src/continuum/storage/`와 `src/continuum/recovery/family.py`(`continuum tree`), allowlist 인가 `src/continuum/mcp/authz.py`(`CONTINUUM_MCP_MUTATING_CLIENTS` / `CONTINUUM_MCP_TOKEN`), 표현 표면 `src/continuum/dashboard/app.py`와 `src/continuum/serve/server.py`, CLI `src/continuum/cli/main.py`(`continuum runs`, `continuum tree`, `continuum health`). |
| 검증 기판 | 시간 T의 체크포인트와 지금의 세계가 주어졌을 때, 계속하는 것이 여전히 안전하고 정확한가 | `src/continuum/state/validator.py`(오래됨 `dependency -> evidence -> finding -> decision` plus `PlanStep.depends_on`), `src/continuum/provenance_map.py`(`Origin`에서 `REQUIRES_REVIEW`까지 `REVIEW_CONFIRMED`까지), `src/continuum/actions/ledger.py`와 `src/continuum/actions/idempotency.py` 및 `src/continuum/gate.py` / `src/continuum/gateway.py`(실행 전 청구, 중복 거부, 조정을 위해 `UnknownSideEffect` 발생), `src/continuum/replayguard.py`(휴대용 가드), `src/continuum/pinning.py`와 `src/continuum/replay_similarity.py`(재생 정확성), `src/continuum/budgets.py`(재시도 상한), `src/continuum/recovery/engine.py` + `src/continuum/recovery/contract.py` + `src/continuum/recovery/planner.py` + `src/continuum/recovery/observations.py`(최대 심각도 `RESUME < ... < ABORT`, `evidence` / `reason` / `next_allowed_action` / `human_steps`가 있는 봉인된 계약), `src/continuum/checkpoint/rewind.py`(원자적 이중 상태 되감기), `src/continuum/analysis/prefix_trust.py`(조언적 신뢰). 게시된 검사: `docs/recovery_walkthrough.md`, `benchmarks/fault_injection/`(`detection_rate` / `unsafe_resume_rate`를 출력하는 스위트), `src/continuum/benchmark/phase6/`(복구 정확성 스위트), `docs/RESULTS.md` 그리고 아래의 재생성 가능한 시각화. |

위의 각 행은 태그가 지정된 커밋 시점에 `main`에 존재하는 경로로 추적 가능하다. 이 표에서는 벤치마크 수치를 다시 게시하지 않는다. 벤치마크는 이미 출력한 스위트 출력에만 존재한다. 게시된 스위트와 설계 문서의 전체 목록은 `docs/research.md`에 있다.
