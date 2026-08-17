param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"
$projectDirectory = Split-Path -Parent $PSScriptRoot
$entryPoint = Join-Path $projectDirectory "server.py"

if (-not $PythonPath) {
    $virtualEnvPython = Join-Path $projectDirectory ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $virtualEnvPython) {
        $PythonPath = $virtualEnvPython
    } else {
        $PythonPath = (Get-Command python -ErrorAction Stop).Source
    }
}

$PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
$entryPoint = (Resolve-Path -LiteralPath $entryPoint).Path

$action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument ('"{0}"' -f $entryPoint) `
    -WorkingDirectory $projectDirectory
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

Register-ScheduledTask `
    -TaskName "OrquestradorCliente" `
    -Description "Executa continuamente os jobs locais do cliente" `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force

Start-ScheduledTask -TaskName "OrquestradorCliente"
Write-Host "Orquestrador instalado e iniciado. Logs: $projectDirectory\logs\orchestrator.log"
