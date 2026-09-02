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
