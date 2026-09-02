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
