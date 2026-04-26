param(
    [string]$JsonFile = "",
    [string]$WebhookUrl = "http://localhost:8000/webhook",
    [string]$EnvPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-EnvPath {
    param([string]$InputPath)

    if ($InputPath) {
        return $InputPath
    }

    $scriptDir = Split-Path -Parent $PSCommandPath
    $repoEnv = Join-Path $scriptDir "..\.env"
    if (Test-Path $repoEnv) {
        return $repoEnv
    }

    return ".env"
}

function Get-EnvValue {
    param(
        [string]$Path,
        [string]$Key
    )

    if (-not (Test-Path $Path)) {
        throw "Env file not found: $Path"
    }

    $line = Get-Content $Path | Where-Object {
        $_ -match "^\s*$Key\s*="
    } | Select-Object -First 1

    if (-not $line) {
        return $null
    }

    $value = ($line -split "=", 2)[1].Trim()
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    return $value
}

function Read-JsonPayload {
    param([string]$Path)

    if ($Path) {
        if (-not (Test-Path $Path)) {
            throw "JSON file not found: $Path"
        }
        return Get-Content $Path -Raw
    }

    Write-Host "Paste JSON payload from Claude." -ForegroundColor Cyan
    Write-Host "When finished, type END on a new line and press Enter." -ForegroundColor Cyan

    $lines = New-Object System.Collections.Generic.List[string]
    while ($true) {
        $line = Read-Host
        if ($line -eq "END") {
            break
        }
        $lines.Add($line)
    }

    return ($lines -join [Environment]::NewLine)
}

function Assert-EnvelopeShape {
    param($Payload)

    if (-not $Payload.PSObject.Properties.Name.Contains("status")) {
        throw "Payload must include 'status'"
    }

    if (-not $Payload.PSObject.Properties.Name.Contains("processed")) {
        throw "Payload must include 'processed'"
    }

    $status = "$($Payload.status)".ToLowerInvariant()

    if ($status -eq "pending") {
        if (-not $Payload.signal) {
            throw "status=pending requires 'signal' object"
        }

        $requiredSignalFields = @("strategy_id", "symbol", "action", "confidence", "size")
        foreach ($field in $requiredSignalFields) {
            if (-not $Payload.signal.PSObject.Properties.Name.Contains($field)) {
                throw "signal missing required field: $field"
            }
        }

        $Payload.signal.symbol = "$($Payload.signal.symbol)".ToUpperInvariant()
        $validActions = @("buy", "sell", "close")
        if ($validActions -notcontains "$($Payload.signal.action)".ToLowerInvariant()) {
            throw "signal.action must be one of: buy, sell, close"
        }
    }
}

try {
    $EnvPath = Resolve-EnvPath -InputPath $EnvPath
    $secret = Get-EnvValue -Path $EnvPath -Key "WEBHOOK_SECRET"
    if (-not $secret) {
        throw "WEBHOOK_SECRET not found in $EnvPath"
    }

    $jsonText = Read-JsonPayload -Path $JsonFile
    if (-not $jsonText.Trim()) {
        throw "Payload is empty"
    }

    $payloadObj = $jsonText | ConvertFrom-Json
    Assert-EnvelopeShape -Payload $payloadObj

    if (-not $payloadObj.PSObject.Properties.Name.Contains("timestamp")) {
        $payloadObj | Add-Member -NotePropertyName "timestamp" -NotePropertyValue (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
    }

    $payloadFinal = $payloadObj | ConvertTo-Json -Depth 10 -Compress

    $response = Invoke-RestMethod -Uri $WebhookUrl -Method POST -Headers @{
        "X-Webhook-Secret" = $secret
        "Content-Type" = "application/json"
    } -Body $payloadFinal

    Write-Host "Webhook sent successfully." -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
