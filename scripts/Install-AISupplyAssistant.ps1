<#
.SYNOPSIS
    AI Supply Assistant - Windows Installer Script
    
.DESCRIPTION
    Automated installation script that:
    - Verifies prerequisites (Python, ODBC Driver)
    - Installs Python dependencies
    - Configures Windows Firewall
    - Sets up Windows Service using NSSM
    - Creates configuration files
    
.PARAMETER InstallPath
    Path where the application is installed (default: current directory)
    
.PARAMETER Port
    Port for the web application (default: 8501)
    
.PARAMETER SkipService
    Skip Windows Service installation
    
.PARAMETER SkipFirewall
    Skip firewall configuration
    
.EXAMPLE
    .\Install-AISupplyAssistant.ps1
    
.EXAMPLE
    .\Install-AISupplyAssistant.ps1 -Port 80 -InstallPath "C:\Apps\AISupplyAssistant"
#>

[CmdletBinding()]
param(
    [string]$InstallPath = (Get-Location).Path,
    [int]$Port = 8501,
    [switch]$SkipService,
    [switch]$SkipFirewall
)

# ============================================
# Configuration
# ============================================
$AppName = "AI Supply Assistant"
$ServiceName = "AISupplyAssistant"
$NssmVersion = "2.24"
$NssmUrl = "https://nssm.cc/release/nssm-$NssmVersion.zip"
$MinPythonVersion = [version]"3.9.0"

# Colors for output
function Write-Step { param($Message) Write-Host "`n[$((Get-Date).ToString('HH:mm:ss'))] " -NoNewline; Write-Host $Message -ForegroundColor Cyan }
function Write-OK { param($Message) Write-Host "  [OK] " -NoNewline -ForegroundColor Green; Write-Host $Message }
function Write-Warn { param($Message) Write-Host "  [WARN] " -NoNewline -ForegroundColor Yellow; Write-Host $Message }
function Write-Err { param($Message) Write-Host "  [ERROR] " -NoNewline -ForegroundColor Red; Write-Host $Message }
function Write-Info { param($Message) Write-Host "  [INFO] " -NoNewline -ForegroundColor Gray; Write-Host $Message }

# ============================================
# Header
# ============================================
Clear-Host
Write-Host ""
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host "    $AppName - Installer" -ForegroundColor Cyan
Write-Host "  ============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Install Path: $InstallPath"
Write-Host "  Port: $Port"
Write-Host ""

# ============================================
# Check Administrator Privileges
# ============================================
Write-Step "Checking Administrator privileges..."

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Err "This script requires Administrator privileges!"
    Write-Info "Please run as Administrator."
    exit 1
}
Write-OK "Running as Administrator"

# ============================================
# Check Python Installation
# ============================================
Write-Step "Checking Python installation..."

$pythonPath = $null
$pythonVersion = $null

# Try to find Python
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $versionOutput = & $cmd --version 2>&1
        if ($versionOutput -match "Python (\d+\.\d+\.\d+)") {
            $pythonVersion = [version]$matches[1]
            $pythonPath = (Get-Command $cmd -ErrorAction SilentlyContinue).Source
            break
        }
    } catch { }
}

if (-not $pythonPath) {
    Write-Err "Python not found!"
    Write-Info "Please install Python 3.9 or later from https://www.python.org/downloads/"
    Write-Info "Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

if ($pythonVersion -lt $MinPythonVersion) {
    Write-Err "Python $pythonVersion is too old. Minimum required: $MinPythonVersion"
    exit 1
}

Write-OK "Python $pythonVersion found at: $pythonPath"

# ============================================
# Check ODBC Driver
# ============================================
Write-Step "Checking ODBC Driver 17 for SQL Server..."

$odbcDriver = Get-OdbcDriver | Where-Object { $_.Name -like "*ODBC Driver 17*" }
if (-not $odbcDriver) {
    Write-Warn "ODBC Driver 17 for SQL Server not found!"
    Write-Info "Attempting to download and install..."
    
    $odbcUrl = "https://go.microsoft.com/fwlink/?linkid=2249006"
    $odbcInstaller = "$env:TEMP\msodbcsql.msi"
    
    try {
        Invoke-WebRequest -Uri $odbcUrl -OutFile $odbcInstaller -UseBasicParsing
        Start-Process msiexec.exe -ArgumentList "/i `"$odbcInstaller`" /quiet /norestart IACCEPTMSODBCSQLLICENSETERMS=YES" -Wait -NoNewWindow
        Write-OK "ODBC Driver 17 installed successfully"
    } catch {
        Write-Err "Failed to install ODBC Driver automatically."
        Write-Info "Please download manually from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server"
        exit 1
    }
} else {
    Write-OK "ODBC Driver 17 found: $($odbcDriver.Name)"
}

# ============================================
# Install Python Dependencies
# ============================================
Write-Step "Installing Python dependencies..."

$requirementsPath = Join-Path $InstallPath "requirements.txt"
if (-not (Test-Path $requirementsPath)) {
    Write-Err "requirements.txt not found at: $requirementsPath"
    exit 1
}

try {
    Write-Info "This may take several minutes..."
    $pipOutput = & python -m pip install -r $requirementsPath --upgrade --quiet 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed: $pipOutput"
    }
    Write-OK "All dependencies installed successfully"
} catch {
    Write-Err "Failed to install dependencies: $_"
    Write-Info "Try running manually: pip install -r requirements.txt"
    exit 1
}

# ============================================
# Create Configuration File
# ============================================
Write-Step "Checking configuration..."

$envPath = Join-Path $InstallPath ".env"
$envExamplePath = Join-Path $InstallPath ".env.example"

if (-not (Test-Path $envPath)) {
    if (Test-Path $envExamplePath) {
        Copy-Item $envExamplePath $envPath
        Write-OK "Created .env from template"
        Write-Warn "Please edit .env with your database credentials!"
    } else {
        Write-Warn ".env.example not found. You'll need to create .env manually."
    }
} else {
    Write-OK ".env already exists"
}

# ============================================
# Configure Windows Firewall
# ============================================
if (-not $SkipFirewall) {
    Write-Step "Configuring Windows Firewall..."
    
    $ruleName = $AppName
    $existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    
    if ($existingRule) {
        Write-Info "Updating existing firewall rule..."
        Remove-NetFirewallRule -DisplayName $ruleName
    }
    
    try {
        New-NetFirewallRule -DisplayName $ruleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort $Port `
            -Action Allow `
            -Profile Domain,Private `
            -Description "Allow inbound connections to $AppName on port $Port" | Out-Null
        Write-OK "Firewall rule created for port $Port"
    } catch {
        Write-Warn "Failed to create firewall rule: $_"
        Write-Info "You may need to manually allow port $Port in Windows Firewall"
    }
} else {
    Write-Info "Skipping firewall configuration (--SkipFirewall)"
}

# ============================================
# Install Windows Service (NSSM)
# ============================================
if (-not $SkipService) {
    Write-Step "Setting up Windows Service..."
    
    $nssmPath = Join-Path $InstallPath "tools\nssm.exe"
    $toolsDir = Join-Path $InstallPath "tools"
    
    # Download NSSM if not present
    if (-not (Test-Path $nssmPath)) {
        Write-Info "Downloading NSSM (Non-Sucking Service Manager)..."
        
        if (-not (Test-Path $toolsDir)) {
            New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
        }
        
        $nssmZip = "$env:TEMP\nssm.zip"
        try {
            # Use embedded NSSM or download
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $NssmUrl -OutFile $nssmZip -UseBasicParsing
            Expand-Archive -Path $nssmZip -DestinationPath $env:TEMP -Force
            
            # Find and copy the appropriate nssm.exe
            $arch = if ([Environment]::Is64BitOperatingSystem) { "win64" } else { "win32" }
            $nssmExtracted = Get-ChildItem -Path "$env:TEMP\nssm-*\$arch\nssm.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            
            if ($nssmExtracted) {
                Copy-Item $nssmExtracted.FullName $nssmPath
                Write-OK "NSSM downloaded and installed"
            } else {
                throw "Could not find nssm.exe in download"
            }
        } catch {
            Write-Warn "Failed to download NSSM: $_"
            Write-Info "Service installation skipped. You can run the server manually with start_server.bat"
            $SkipService = $true
        }
    }
    
    if (-not $SkipService -and (Test-Path $nssmPath)) {
        # Remove existing service if present
        $existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Info "Removing existing service..."
            & $nssmPath stop $ServiceName 2>&1 | Out-Null
            & $nssmPath remove $ServiceName confirm 2>&1 | Out-Null
            Start-Sleep -Seconds 2
        }
        
        # Install new service
        Write-Info "Installing Windows Service..."
        
        $mainPy = Join-Path $InstallPath "main.py"
        $streamlitArgs = "-m streamlit run `"$mainPy`" --server.address 0.0.0.0 --server.port $Port --server.headless true"
        
        & $nssmPath install $ServiceName $pythonPath $streamlitArgs
        & $nssmPath set $ServiceName AppDirectory $InstallPath
        & $nssmPath set $ServiceName DisplayName $AppName
        & $nssmPath set $ServiceName Description "AI-powered supply chain assistant for ERP systems"
        & $nssmPath set $ServiceName Start SERVICE_AUTO_START
        & $nssmPath set $ServiceName ObjectName "LocalSystem"
        
        # Set up logging
        $logDir = Join-Path $InstallPath "logs"
        if (-not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        & $nssmPath set $ServiceName AppStdout (Join-Path $logDir "service_stdout.log")
        & $nssmPath set $ServiceName AppStderr (Join-Path $logDir "service_stderr.log")
        & $nssmPath set $ServiceName AppRotateFiles 1
        & $nssmPath set $ServiceName AppRotateBytes 1048576
        
        Write-OK "Windows Service '$ServiceName' installed"
        
        # Ask to start service
        $startNow = Read-Host "  Start the service now? (Y/n)"
        if ($startNow -ne 'n' -and $startNow -ne 'N') {
            & $nssmPath start $ServiceName
            Start-Sleep -Seconds 3
            
            $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
            if ($service.Status -eq 'Running') {
                Write-OK "Service started successfully!"
            } else {
                Write-Warn "Service may not have started properly. Check logs in: $logDir"
            }
        }
    }
} else {
    Write-Info "Skipping service installation (--SkipService)"
}

# ============================================
# Create Desktop Shortcut
# ============================================
Write-Step "Creating shortcuts..."

$desktopPath = [Environment]::GetFolderPath('CommonDesktopDirectory')
$shortcutPath = Join-Path $desktopPath "$AppName.url"

try {
    $serverIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
    if (-not $serverIP) { $serverIP = "localhost" }
    
    $shortcutContent = @"
[InternetShortcut]
URL=http://${serverIP}:$Port
IconIndex=0
"@
    $shortcutContent | Out-File -FilePath $shortcutPath -Encoding ASCII
    Write-OK "Desktop shortcut created"
} catch {
    Write-Warn "Failed to create desktop shortcut: $_"
}

# ============================================
# Summary
# ============================================
$serverIP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.*" } | Select-Object -First 1).IPAddress
if (-not $serverIP) { $serverIP = "localhost" }

Write-Host ""
Write-Host "  ============================================" -ForegroundColor Green
Write-Host "    Installation Complete!" -ForegroundColor Green
Write-Host "  ============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Application URL: " -NoNewline; Write-Host "http://${serverIP}:$Port" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Edit configuration: " -NoNewline; Write-Host "$envPath" -ForegroundColor Yellow
Write-Host "  2. Configure database connection in .env file"
Write-Host "  3. Access the application in your browser"
Write-Host ""

if (-not $SkipService) {
    Write-Host "  Service Management:" -ForegroundColor Cyan
    Write-Host "    Start:   " -NoNewline; Write-Host "nssm start $ServiceName" -ForegroundColor Gray
    Write-Host "    Stop:    " -NoNewline; Write-Host "nssm stop $ServiceName" -ForegroundColor Gray  
    Write-Host "    Restart: " -NoNewline; Write-Host "nssm restart $ServiceName" -ForegroundColor Gray
    Write-Host "    Status:  " -NoNewline; Write-Host "Get-Service $ServiceName" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "  Default Login:" -ForegroundColor Cyan
Write-Host "    Username: admin"
Write-Host "    Password: admin123"
Write-Host ""
Write-Host "  IMPORTANT: Change the default password after first login!" -ForegroundColor Yellow
Write-Host ""
