# PostgreSQL concurrency test: use a disposable test database only.
# Example: $env:TEST_DATABASE_URL='postgresql://user:pass@localhost:5432/disposable_test_db'
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
if (-not $env:TEST_DATABASE_URL) { throw 'Set TEST_DATABASE_URL to a disposable PostgreSQL test database. Never use production data.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    python -m pytest tests/automation/test_postgres_concurrency.py -v -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw "Concurrency tests failed (exit code $LASTEXITCODE)." }
} finally { Pop-Location }
