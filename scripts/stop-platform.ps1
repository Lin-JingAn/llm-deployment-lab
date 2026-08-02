$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $Root "infra\litellm\compose.yaml"

foreach ($port in @(5500, 8002, 8899)) {
    $processIds = @(
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    )

    foreach ($processId in $processIds) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "STOPPED PORT $port PID $processId"
    }

    if ($processIds.Count -eq 0) {
        Write-Host "PORT $port WAS NOT ACTIVE"
    }
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose -f $ComposeFile stop
    Write-Host "DOCKER SERVICES STOPPED WITHOUT DELETING VOLUMES"
}
