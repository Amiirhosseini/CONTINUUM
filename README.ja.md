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
