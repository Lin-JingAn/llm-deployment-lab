$ErrorActionPreference = "Continue"

function Test-HttpEndpoint {
    param(
        [string]$Name,
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8
        Write-Host "OK   $Name $($response.StatusCode) $Url"
        return $true
    } catch {
        Write-Host "FAIL $Name $Url"
        Write-Host "     $($_.Exception.Message)"
        return $false
    }
}

function Test-TcpPort {
    param(
        [string]$Name,
        [int]$Port
    )

    $active = [bool](
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    )

    if ($active) {
        Write-Host "OK   $Name port $Port"
    } else {
        Write-Host "FAIL $Name port $Port"
    }

    return $active
}

$results = @()
$results += Test-HttpEndpoint "Web" "http://127.0.0.1:5500"
$results += Test-HttpEndpoint "FastAPI" "http://127.0.0.1:8002/health"
$results += Test-HttpEndpoint "Readiness" "http://127.0.0.1:8002/health/readiness"
$results += Test-TcpPort "Direct proxy" 8899
$results += Test-TcpPort "LiteLLM" 4000
$results += Test-TcpPort "PostgreSQL" 5433

if ($results -contains $false) {
    Write-Host "PLATFORM_HEALTH_CHECK_FAILED"
    exit 1
}

Write-Host "PLATFORM_HEALTH_CHECK_OK"
