# CONTINUUM - one-command demo for Windows PowerShell.
# Run:  powershell -ExecutionPolicy Bypass -File try-it.ps1
# Modes match try-it.sh: demo (default), test, cli ..., shell
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
Set-Location $Root

$venvScripts = Join-Path $Root ".venv\Scripts"
if (Test-Path $venvScripts) {
    $env:PATH = "$venvScripts;$env:PATH"
}
$env:PYTHONPATH = Join-Path $Root "src"

$python = if (Test-Path (Join-Path $venvScripts "python.exe")) {
    Join-Path $venvScripts "python.exe"
} else {
    "python"
}

$mode = if ($args.Count -gt 0) { $args[0] } else { "demo" }

switch ($mode) {
    "demo" {
        & $python (Join-Path $Root "examples\crash_recovery_agent.py")
    }
    "test" {
        & $python -m pytest
    }
    "cli" {
        $cliArgs = @()
        if ($args.Count -gt 1) {
            $cliArgs = $args[1..($args.Count - 1)]
        }
        & continuum @cliArgs
    }
    "shell" {
        Write-Host "PATH and PYTHONPATH set. Try: continuum --help"
    }
    default {
        Write-Host "usage: try-it.ps1 [demo|test|cli ...|shell]"
        exit 1
    }
}
