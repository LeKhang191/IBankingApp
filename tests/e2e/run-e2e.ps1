<#
Runs isolated HTTP E2E checks. Run this ONLY with the disposable E2E compose project.
From repository root: .\tests\e2e\run-e2e.ps1
No volumes are deleted by this script.
#>
[CmdletBinding()]
param([switch]$Build)
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    $upArgs=@('-f','docker-compose.e2e.yml','up','-d')
    if ($Build) { $upArgs+='--build' }
    & docker compose @upArgs
    if ($LASTEXITCODE -ne 0) { throw 'E2E stack failed to start. Inspect docker compose logs.' }
    & docker compose -f docker-compose.e2e.yml run --rm e2e-tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
