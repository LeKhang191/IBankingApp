# Basic payment workflow automated smoke test against the running application.
# From project root: .\tests\automation\test-workflow.ps1
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    Write-Host '[TEST] Payment Saga + Outbox workflow' -ForegroundColor Cyan
    docker compose exec -T payment-service python -m app.tests.phase3_saga_smoke
    if ($LASTEXITCODE -ne 0) { throw "Payment workflow failed (exit code $LASTEXITCODE)." }
    Write-Host '[PASS] Payment Saga + Outbox workflow' -ForegroundColor Green
} finally { Pop-Location }
