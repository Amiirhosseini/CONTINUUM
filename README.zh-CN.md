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
