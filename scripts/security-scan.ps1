$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$extensions = @(".py", ".js", ".html", ".css", ".yaml", ".yml", ".json", ".toml", ".ini", ".md", ".ps1")
$excludedParts = @("\.venv\", "\.git\", "\backups\", "\__pycache__\")
$patterns = @(
    "sk-[A-Za-z0-9_-]{16,}",
    "AKIA[0-9A-Z]{16}",
    "(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['""][^'""]{8,}['""]"
)

$findings = @()

Get-ChildItem $Root -Recurse -File | ForEach-Object {
    $path = $_.FullName

    if ($_.Name -eq ".env" -or $_.Name -like ".env.*") {
        if ($_.Name -ne ".env.example") {
            Write-Host "LOCAL_SECRET_FILE_PRESENT $path"
        }
        return
    }

    if ($extensions -notcontains $_.Extension.ToLowerInvariant()) {
        return
    }

    foreach ($excludedPart in $excludedParts) {
        if ($path.Contains($excludedPart)) {
            return
        }
    }

    $lineNumber = 0
    Get-Content $path -ErrorAction SilentlyContinue | ForEach-Object {
        $lineNumber += 1
        $line = $_

        foreach ($pattern in $patterns) {
            if ($line -match $pattern -and $line -notmatch "replace-me|<access-token>|example") {
                $findings += "$path`:$lineNumber"
                break
            }
        }
    }
}

$findings = $findings | Sort-Object -Unique

if ($findings.Count -gt 0) {
    Write-Host "POSSIBLE_SECRET_LOCATIONS"
    $findings | ForEach-Object { Write-Host $_ }
    Write-Host "SECURITY_SCAN_REVIEW_REQUIRED"
    exit 2
}

Write-Host "SECURITY_SCAN_OK"
