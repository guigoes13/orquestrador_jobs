$ErrorActionPreference = "Stop"

if (Get-ScheduledTask -TaskName "OrquestradorCliente" -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName "OrquestradorCliente" -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "OrquestradorCliente" -Confirm:$false
    Write-Host "Tarefa OrquestradorCliente removida."
} else {
    Write-Host "A tarefa OrquestradorCliente não está instalada."
}
