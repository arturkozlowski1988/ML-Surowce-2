<#
.SYNOPSIS
    AI Supply Assistant - Windows Uninstaller Script

.DESCRIPTION
    Removes the Windows Service and cleans up firewall rules.
    Does NOT remove application files or configuration.

.PARAMETER ServiceName
    Name of the Windows Service to remove (default: AISupplyAssistant)

.PARAMETER RemoveFirewall
    Also remove the firewall rule

.EXAMPLE
    .\Uninstall-AISupplyAssistant.ps1
#>

[CmdletBinding()]
param(
    [string]$ServiceName = "AISupplyAssistant",
    [switch]$RemoveFirewall
)

$AppName = "AI Supply Assistant"

# Colors
function Write-Step { param($Message) Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] " -NoNewline; Write-Host $Message -ForegroundColor Cyan }
function Write-OK { param($Message) Write-Host "  [OK] " -NoNewline -ForegroundColor Green; Write-Host $Message }
function Write-Warn { param($Message) Write-Host "  [WARN] " -NoNewline -ForegroundColor Yellow; Write-Host $Message }
function Write-Err { param($Message) Write-Host "  [ERROR] " -NoNewline -ForegroundColor Red; Write-Host $Message }
function Write-Info { param($Message) Write-Host "  [INFO] " -NoNewline -ForegroundColor Gray; Write-Host $Message }

# Header
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Yellow
Write-Host "    $AppName - Uninstaller" -ForegroundColor Yellow
Write-Host "  ============================================" -ForegroundColor Yellow
Write-Host ""

# Check Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Err "This script requires Administrator privileges!"
    exit 1
}

# Stop and Remove Service
Write-Step "Removing Windows Service..."

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    Write-Info "Stopping service..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    # Try NSSM first
    $nssmPath = Join-Path (Get-Location).Path "tools\nssm.exe"
    if (Test-Path $nssmPath) {
        & $nssmPath stop $ServiceName 2>&1 | Out-Null
        & $nssmPath remove $ServiceName confirm 2>&1 | Out-Null
        Write-OK "Service removed using NSSM"
    } else {
        # Fallback to sc.exe
        & sc.exe delete $ServiceName 2>&1 | Out-Null
        Write-OK "Service removed using sc.exe"
    }
} else {
    Write-Info "Service '$ServiceName' not found"
}

# Remove Firewall Rule
if ($RemoveFirewall) {
    Write-Step "Removing firewall rule..."

    $rule = Get-NetFirewallRule -DisplayName $AppName -ErrorAction SilentlyContinue
    if ($rule) {
        Remove-NetFirewallRule -DisplayName $AppName
        Write-OK "Firewall rule removed"
    } else {
        Write-Info "Firewall rule not found"
    }
} else {
    Write-Info "Keeping firewall rule. Use -RemoveFirewall to remove it."
}

# Remove Desktop Shortcut
Write-Step "Removing shortcuts..."

$desktopPath = [Environment]::GetFolderPath('CommonDesktopDirectory')
$shortcutPath = Join-Path $desktopPath "$AppName.url"

if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-OK "Desktop shortcut removed"
} else {
    Write-Info "Desktop shortcut not found"
}

# Summary
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Uninstallation Complete" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  The following items were NOT removed:" -ForegroundColor Yellow
Write-Host "    - Application files and folders"
Write-Host "    - Configuration files (.env)"
Write-Host "    - Log files"
Write-Host "    - Python packages"
Write-Host ""
Write-Host "  To completely remove, delete the application folder manually."
Write-Host ""
