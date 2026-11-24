<#
.SYNOPSIS
Diagnose or restart the VLSMatic Django development server safely.

.EXAMPLE
  .\scripts\dev-server.ps1
  Shows the configured mode, fresh Django database target, users, and port owner.

.EXAMPLE
  .\scripts\dev-server.ps1 -Restart -Environment remote
  Stops a verified Django runserver on port 8000 and starts Supabase mode.

.EXAMPLE
  .\scripts\dev-server.ps1 -Environment remote -CheckUser rafreen
  Securely prompts for a password and checks it against the selected database.

The restarted server remains attached to this terminal. Press Ctrl+C to stop it.
#>

[CmdletBinding()]
param(
    [ValidateSet("local", "remote")]
    [string]$Environment,
    [ValidateRange(1024, 65535)]
    [int]$Port = 8000,
    [string]$CheckUser,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

if (-not (Test-Path -LiteralPath (Join-Path $projectRoot "manage.py"))) {
    throw "manage.py was not found in $projectRoot"
}

function Get-ConfiguredMode {
    if (-not (Test-Path -LiteralPath $envFile)) { return $null }
    $line = Get-Content -LiteralPath $envFile |
        Where-Object { $_ -match '^\s*APP_ENV\s*=' } |
        Select-Object -Last 1
    if (-not $line) { return $null }
    return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'").ToLowerInvariant()
}

function Get-PortListener {
    Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-ProcessCommandLine([int]$ProcessId) {
    (Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue).CommandLine
}

$configuredMode = Get-ConfiguredMode
$selectedMode = if ($Environment) {
    $Environment
} elseif ($configuredMode) {
    $configuredMode
} else {
    "remote"
}

Write-Host "VLSMatic development-server diagnostic" -ForegroundColor Cyan
Write-Host "Project:      $projectRoot"
Write-Host "Python:       $python"
Write-Host "Configured:   $(if ($configuredMode) { $configuredMode } else { 'not set; defaults to remote' })"
Write-Host "Selected:     $selectedMode"
Write-Host "URL:          http://127.0.0.1:$Port/"

$previousMode = $env:APP_ENV
$env:APP_ENV = $selectedMode
try {
    Write-Host ""
    Write-Host "Fresh Django connection" -ForegroundColor Cyan
    Push-Location $projectRoot
    & $python manage.py shell -c @"
from django.conf import settings
from django.contrib.auth import get_user_model
db = settings.DATABASES['default']
target = 'SQLite: ' + str(db.get('NAME')) if settings.APP_ENV == 'local' else 'PostgreSQL: ' + str(db.get('HOST'))
print('APP_ENV:      ' + settings.APP_ENV)
print('Database:     ' + target)
print('Users:')
for user in get_user_model().objects.order_by('username'):
    print(f'  - {user.username} | active={user.is_active} | role={user.role} | password_usable={user.has_usable_password()}')
"@
    if ($LASTEXITCODE -ne 0) {
        throw "Django could not connect using APP_ENV=$selectedMode."
    }
    if ($CheckUser) {
        Write-Host ""
        Write-Host "Credential check for $CheckUser" -ForegroundColor Cyan
        $env:VLSMATIC_DIAG_USERNAME = $CheckUser
        & $python manage.py shell -c @"
import os
from getpass import getpass
from django.contrib.auth import get_user_model
username = os.environ['VLSMATIC_DIAG_USERNAME']
user = get_user_model().objects.filter(username=username).first()
if user is None:
    print('Result: user does not exist in this database')
else:
    print('Result: correct password' if user.check_password(getpass('Password: ')) else 'Result: incorrect password')
"@
        Remove-Item Env:VLSMATIC_DIAG_USERNAME -ErrorAction SilentlyContinue
    }
}
finally {
    Pop-Location
    if ($null -eq $previousMode) {
        Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue
    } else {
        $env:APP_ENV = $previousMode
    }
}

$listener = Get-PortListener
if ($listener) {
    $commandLine = Get-ProcessCommandLine -ProcessId $listener.OwningProcess
    Write-Host ""
    Write-Host "Port $Port is in use" -ForegroundColor Yellow
    Write-Host "PID:          $($listener.OwningProcess)"
    Write-Host "Command:      $commandLine"
    if ($commandLine -notmatch '(?i)manage\.py\s+runserver') {
        Write-Warning "The listener is not a verified Django runserver. This script will not stop it."
        if ($Restart) {
            throw "Cannot restart safely while another application owns port $Port."
        }
    }
} else {
    Write-Host ""
    Write-Host "Port $Port is free." -ForegroundColor Green
}

if (-not $Restart) {
    Write-Host ""
    Write-Host "Diagnostic complete. To restart safely:" -ForegroundColor Green
    Write-Host ".\scripts\dev-server.ps1 -Restart -Environment $selectedMode -Port $Port"
    exit 0
}

if ($listener) {
    $commandLine = Get-ProcessCommandLine -ProcessId $listener.OwningProcess
    if ($commandLine -match '(?i)manage\.py\s+runserver') {
        Write-Host "Stopping verified Django server PID $($listener.OwningProcess)..." -ForegroundColor Yellow
        Stop-Process -Id $listener.OwningProcess -Force
        Start-Sleep -Milliseconds 500
        if (Get-PortListener) {
            throw "Port $Port is still occupied after stopping PID $($listener.OwningProcess)."
        }
    }
}

Write-Host ""
Write-Host "Starting VLSMatic with APP_ENV=$selectedMode" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server cleanly."
Write-Host ""
$env:APP_ENV = $selectedMode
Set-Location $projectRoot
& $python manage.py runserver "127.0.0.1:$Port"
