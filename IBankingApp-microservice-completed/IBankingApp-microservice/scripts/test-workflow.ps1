[CmdletBinding()]
param(
    [switch]$SkipSmokeTest,
    [switch]$ShowLogs
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$script:Passed = 0
$script:Failed = 0

function Write-Section([string]$Title) {
    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Invoke-Check([string]$Name, [scriptblock]$Action) {
    Write-Host "`n[TEST] $Name" -ForegroundColor Yellow
    try {
        & $Action
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            throw "Command exited with code $LASTEXITCODE"
        }
        $script:Passed++
        Write-Host "[PASS] $Name" -ForegroundColor Green
    }
    catch {
        $script:Failed++
        Write-Host "[FAIL] $Name - $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Invoke-ComposeHealth([string]$Name, [string]$Url) {
    Invoke-Check "$Name health endpoint" {
        $response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 8
        $response | ConvertTo-Json -Compress | Write-Host
        if ($response.status -ne 'ok') { throw "Unexpected health response from $Url" }
    }
}

Write-Section 'iBanking Phase 3 - Windows Workflow Test'
Write-Host "Project: $ProjectRoot"

if (-not (Test-Path (Join-Path $ProjectRoot 'docker-compose.yml')) -and -not (Test-Path (Join-Path $ProjectRoot 'compose.yml'))) {
    Write-Host '[ERROR] Không tìm thấy docker-compose.yml/compose.yml. Hãy đặt thư mục scripts trong thư mục gốc project.' -ForegroundColor Red
    exit 2
}

Invoke-Check 'Docker CLI available' {
    docker --version
    if ($LASTEXITCODE -ne 0) { throw 'Docker CLI không chạy được.' }
}

Invoke-Check 'Docker Compose configuration' {
    docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'docker compose config có lỗi. Kiểm tra file .env.' }
}

Invoke-Check 'Required containers are running' {
    docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Không đọc được trạng thái Docker Compose.' }
    $running = docker compose ps --status running --services
    $required = @('postgres','db-bootstrap','auth-service','tuition-service','payment-service','payment-worker','notification-service','api-gateway','frontend')
    foreach ($service in $required) {
        if ($running -notcontains $service) {
            # db-bootstrap is a one-shot container and should exit successfully, not remain running.
            if ($service -eq 'db-bootstrap') { continue }
            throw "Service '$service' chưa running. Chạy docker compose up -d và xem logs."
        }
    }
}

Invoke-ComposeHealth 'API Gateway' 'http://localhost:8080/health'
foreach ($service in @('auth-service','tuition-service','payment-service')) {
    Invoke-Check "$service internal health" {
        docker compose exec -T $service python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=5).read().decode())"
        if ($LASTEXITCODE -ne 0) { throw "Internal service $service failed health check" }
    }
}

Invoke-Check 'Notification Service health (inside Docker network)' {
    docker compose exec -T notification-service python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8003/health', timeout=5).read().decode())"
    if ($LASTEXITCODE -ne 0) { throw 'Notification Service health check thất bại.' }
}

Invoke-Check 'Payment Worker process' {
    docker compose exec -T payment-worker python -c "import os; print('worker container is reachable; pid=', os.getpid())"
    if ($LASTEXITCODE -ne 0) { throw 'Payment Worker không chạy hoặc không thể exec.' }
}

Invoke-Check 'Phase 2 databases exist' {
    $sql = "SELECT string_agg(datname, ',' ORDER BY datname) FROM pg_database WHERE datname IN ('auth_db','tuition_db','payment_db');"
    $result = docker compose exec -T postgres psql -U postgres -d postgres -t -A -c $sql
    if ($LASTEXITCODE -ne 0) { throw 'Không truy vấn được PostgreSQL.' }
    Write-Host "Databases: $result"
    $names = @($result.Trim().Split(','))
    foreach ($db in @('auth_db','tuition_db','payment_db')) {
        if ($names -notcontains $db) { throw "Thiếu database $db." }
    }
}

Invoke-Check 'Phase 3 tables exist in payment_db' {
    $sql = "SELECT to_regclass('public.transactions'), to_regclass('public.outbox_events');"
    $result = docker compose exec -T postgres psql -U postgres -d payment_db -t -A -c $sql
    if ($LASTEXITCODE -ne 0) { throw 'Không truy vấn được payment_db.' }
    Write-Host "Tables: $result"
    if ($result -notmatch 'transactions' -or $result -notmatch 'outbox_events') {
        throw 'Thiếu transactions hoặc outbox_events. Chạy migration Phase 3.'
    }
}

if (-not $SkipSmokeTest) {
    Invoke-Check 'Saga + Transactional Outbox automated smoke test' {
        docker compose exec -T payment-service python -m app.tests.phase3_saga_smoke
        if ($LASTEXITCODE -ne 0) { throw 'Phase 3 smoke test failed. Xem lỗi Python phía trên.' }
    }
}
else {
    Write-Host '[SKIP] Saga/Outbox smoke test theo tham số -SkipSmokeTest.' -ForegroundColor DarkYellow
}

if ($ShowLogs) {
    Write-Section 'Recent Payment Service / Worker logs'
    docker compose logs --tail 60 payment-service payment-worker
}

Write-Section 'TEST SUMMARY'
Write-Host "Passed: $script:Passed" -ForegroundColor Green
Write-Host "Failed: $script:Failed" -ForegroundColor $(if ($script:Failed -eq 0) { 'Green' } else { 'Red' })

if ($script:Failed -gt 0) {
    Write-Host "`nCó test FAIL. Xem log bằng: docker compose logs --tail 100 <service-name>" -ForegroundColor Red
    exit 1
}

Write-Host "`nTất cả kiểm tra tự động đã PASS." -ForegroundColor Green
Write-Host 'Tiếp theo: chạy kiểm thử nghiệp vụ thật trên giao diện http://localhost:5173 (đăng nhập, tra cứu học phí, nhận OTP, xác nhận, kiểm tra số dư/lịch sử/email).' -ForegroundColor Cyan
exit 0
