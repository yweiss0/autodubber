#Requires -Version 5.1
#Requires -RunAsAdministrator # Optional: Uncomment if you want to try and force admin for silent install

# --- Configuration ---
$ShortcutName = "AutoVoiceOver.url" # Or AutoVoiceOver.lnk if using WScript.Shell for .lnk
$ShortcutTargetUrl = "http://localhost:5173"
$RelativeIconPath = "frontend\static\AVO_logo.ico" # Ensure this .ico file exists in script_root\frontend

Function Test-DockerInstalled {
    Write-Host "Checking for Docker command..."
    $dockerPath = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $dockerPath) {
        Write-Warning "Docker command not found."
        return $false
    }
    Write-Host "Docker command found at: $($dockerPath.Source)"
    return $true
}

Function Test-DockerRunning {
    Write-Host "Checking if Docker Desktop service is running..."
    try {
        docker ps > $null # Suppress output of docker ps
        Write-Host "Docker Desktop is running and responsive."
        return $true
    } catch {
        Write-Warning "Docker Desktop is installed, but the Docker daemon is not responding or not accessible."
        return $false
    }
}

Function Install-DockerDesktop {
    $installerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $installerPath = Join-Path $env:TEMP "DockerDesktopInstaller.exe"

    $choice = Read-Host "Docker Desktop not found or not running. Download and install? (Y/N)"
    if ($choice -ne 'Y') {
        Write-Warning "Skipping Docker Desktop installation. Script cannot continue."
        return $false
    }

    Write-Host "Downloading Docker Desktop Installer from $installerUrl..."
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing -ErrorAction Stop
        Write-Host "Download complete: $installerPath"
    } catch {
        Write-Error "Docker Desktop download failed: $($_.Exception.Message)"
        return $false
    }

    Write-Host "Starting Docker Desktop Installer..."
    Start-Process -FilePath $installerPath -Wait 

    Write-Host ""
    Write-Host "================================= IMPORTANT =================================" -ForegroundColor Yellow
    Write-Host "PLEASE COMPLETE THE DOCKER DESKTOP INSTALLATION (REBOOT IF NEEDED)." -ForegroundColor Yellow
    Write-Host "AFTERWARDS, ENSURE DOCKER DESKTOP IS STARTED AND RUNNING." -ForegroundColor Yellow
    Write-Host "THEN, PLEASE RE-RUN THIS SCRIPT (start.ps1) to launch AutoDubber." -ForegroundColor Yellow
    Write-Host "===========================================================================" -ForegroundColor Yellow
    Write-Host ""
    return $false 
}

Function Create-DesktopShortcut {
    param(
        [string]$Name,
        [string]$TargetUrl,
        [string]$IconRelativePath
    )

    $DesktopPath = [System.Environment]::GetFolderPath('Desktop')
    $ShortcutFilePath = Join-Path $DesktopPath $Name
    
    # $PSScriptRoot is the directory containing the currently running script
    $AbsoluteIconPathObject = Resolve-Path (Join-Path $PSScriptRoot $IconRelativePath) -ErrorAction SilentlyContinue
    $AbsoluteIconPath = $AbsoluteIconPathObject.Path # Get string path

    if (Test-Path $ShortcutFilePath) {
        Write-Host "Desktop shortcut '$Name' already exists."
    } else {
        Write-Host "Creating desktop shortcut '$Name'..."
        $ShortcutContent = "[InternetShortcut]`r`nURL=$TargetUrl`r`n"

        if ($AbsoluteIconPathObject -and (Test-Path $AbsoluteIconPath)) {
            $ShortcutContent += "IconFile=$AbsoluteIconPath`r`nIconIndex=0`r`n"
            Write-Host "Using icon: $AbsoluteIconPath"
        } else {
            Write-Warning "Icon file not found at '$((Join-Path $PSScriptRoot $IconRelativePath))'. Shortcut will be created without a custom icon or with a default one."
        }
        
        try {
            Set-Content -Path $ShortcutFilePath -Value $ShortcutContent -Encoding UTF8 -ErrorAction Stop
            Write-Host "Shortcut created successfully: $ShortcutFilePath"
        } catch {
            Write-Error "Failed to create shortcut: $($_.Exception.Message)"
        }
    }
}

Function Start-AutoDubberApp {
    Write-Host ""
    Write-Host "Starting AutoDubber with Docker..." -ForegroundColor Green
    # ... (rest of your messages here)
    Write-Host "Starting containers..."
    
    try {
        docker-compose up -d --build -ErrorAction Stop
    } catch {
        Write-Error "docker-compose command failed: $($_.Exception.Message)"
        return
    }

    Write-Host ""
    Write-Host "Waiting for services to start (10 seconds)..."
    Start-Sleep -Seconds 10

    Write-Host "Checking container status..."
    docker-compose ps
    Write-Host ""

    # Create Desktop Shortcut
    Create-DesktopShortcut -Name $ShortcutName -TargetUrl $ShortcutTargetUrl -IconRelativePath $RelativeIconPath
    Write-Host ""

    Write-Host "Opening browser to $ShortcutTargetUrl ..."
    Start-Process $ShortcutTargetUrl

    Write-Host ""
    Write-Host "AutoDubber should now be running!" -ForegroundColor Green
    # ... (rest of your messages here)
}

# --- Main Script Logic ---
Clear-Host
# ... (initial prompts and Docker checks as before) ...

Write-Host "Starting AutoDubber Setup..." -ForegroundColor Cyan
Write-Host "This script will check for Docker, help install it if missing, and then launch your app."
Read-Host "Press Enter to begin or Ctrl+C to cancel..."
Clear-Host

$dockerInstalled = Test-DockerInstalled
if (-not $dockerInstalled) {
    if (-not (Install-DockerDesktop)) {
        Write-Warning "Exiting script as Docker setup was not completed or was skipped."
        Read-Host "Press Enter to exit."
        exit 1
    }
} else {
    if (-not (Test-DockerRunning)) {
        Write-Warning "Please start Docker Desktop, wait for it to initialize, then re-run this script."
        Read-Host "Press Enter to exit."
        exit 1
    }
}

if ($dockerInstalled -and (Test-DockerRunning -ErrorAction SilentlyContinue)) {
    Start-AutoDubberApp
} else {
    Write-Warning "Docker is not ready. Please ensure Docker Desktop is installed, running, and then re-run this script."
}

Write-Host "Script finished."
Read-Host "Press Enter to close this window."