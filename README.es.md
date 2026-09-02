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
