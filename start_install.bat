@echo off
setlocal
cls

echo Starting AutoDubber Setup...
echo.
echo This script will:
echo 1. Check if Docker Desktop is installed and running.
echo 2. If not installed, download and help you start the Docker Desktop installation.
echo 3. Once Docker is ready, it will start the AutoDubber application.
echo 4. Create a desktop shortcut for AutoVoiceOver if it doesn't exist.
echo.
echo Press any key to begin or Ctrl+C to cancel...
pause > nul
cls

REM --- Configuration ---
set "DOCKER_INSTALLER_URL=https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
set "DOWNLOAD_PATH=%TEMP%\DockerDesktopInstaller.exe"
set "SHORTCUT_NAME=AutoVoiceOver.url"
set "SHORTCUT_TARGET_URL=http://localhost:5173"
set "RELATIVE_ICON_PATH=frontend\static\AVO_logo.ico" REM Ensure this .ico file exists

REM --- Check if Docker command is available ---
echo Checking for Docker command...
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Docker command not found.
    goto InstallDocker
)
echo Docker command found.
echo.
goto CheckDockerRunning

REM --- Docker Installation ---
:InstallDocker
echo Docker Desktop appears to be not installed or not in your system PATH.
echo.
choice /C YN /N /M "Do you want to download and start the Docker Desktop installer now? (Y/N)"
if errorlevel 2 (
    echo Skipping Docker Desktop installation.
    echo The script cannot continue without Docker.
    goto EndScript
)
if errorlevel 1 (
    echo.
    echo Downloading Docker Desktop Installer from %DOCKER_INSTALLER_URL%...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%DOCKER_INSTALLER_URL%' -OutFile '%DOWNLOAD_PATH%' } catch { Write-Error ('Download failed: ' + $_.Exception.Message); exit 1 }"
    
    if %errorlevel% neq 0 (
        echo ERROR: Docker Desktop download failed.
        goto EndScript
    )
    echo Download complete: %DOWNLOAD_PATH%
    echo.
    echo Starting Docker Desktop Installer...
    echo Please follow the on-screen instructions.
    start "" /WAIT "%DOWNLOAD_PATH%"
    
    echo.
    echo ================================= IMPORTANT =================================
    echo PLEASE COMPLETE THE DOCKER DESKTOP INSTALLATION (REBOOT IF NEEDED).
    echo AFTERWARDS, ENSURE DOCKER DESKTOP IS STARTED AND RUNNING.
    echo THEN, PLEASE RE-RUN THIS SCRIPT (start.bat) to launch AutoDubber.
    echo ===========================================================================
    echo.
    goto EndScript
)

REM --- Check if Docker Daemon is Running ---
:CheckDockerRunning
echo Checking if Docker Desktop service is running...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo Docker Desktop is installed, but the Docker daemon is not responding.
    echo Please start Docker Desktop and wait for it to initialize, then re-run this script.
    goto EndScript
)
echo Docker Desktop is running and responsive.
echo.
goto StartApp

REM --- Start Application ---
:StartApp
echo.
echo Starting AutoDubber with Docker...
echo.
echo This will:
echo - Download and install all dependencies (if not already built)
echo - Start the frontend on http://localhost:5173
echo - Start the backend API on http://localhost:8000
echo - Create a Desktop Shortcut if needed
echo - Open your browser to the application
echo.
echo Starting containers...
echo.

docker-compose up -d --build

if %errorlevel% neq 0 (
    echo ERROR: docker-compose command failed.
    echo Please check the output above for errors.
    goto EndScript
)

REM Wait a few seconds for the services to start
echo.
echo Waiting for services to start (10 seconds)...
timeout /t 10 /nobreak > nul

echo Checking container status...
docker-compose ps
echo.

REM --- Create Desktop Shortcut ---
set "DESKTOP_PATH=%USERPROFILE%\Desktop"
set "SHORTCUT_FILE_PATH=%DESKTOP_PATH%\%SHORTCUT_NAME%"
set "ABSOLUTE_ICON_PATH=%~dp0%RELATIVE_ICON_PATH%"

REM Replace backslashes with forward slashes for IconFile if necessary, though absolute path should work
REM For IconFile, absolute path is generally more robust.
REM Windows typically handles backslashes fine in .ini style files.

if exist "%SHORTCUT_FILE_PATH%" (
    echo Desktop shortcut '%SHORTCUT_NAME%' already exists.
) else (
    echo Creating desktop shortcut '%SHORTCUT_NAME%'...
    if not exist "%~dp0%RELATIVE_ICON_PATH%" (
        echo WARNING: Icon file not found at '%ABSOLUTE_ICON_PATH%'. Shortcut will be created without a custom icon or with a default one.
        (
            echo [InternetShortcut]
            echo URL=%SHORTCUT_TARGET_URL%
        ) > "%SHORTCUT_FILE_PATH%"
    ) else (
        (
            echo [InternetShortcut]
            echo URL=%SHORTCUT_TARGET_URL%
            echo IconFile=%ABSOLUTE_ICON_PATH%
            echo IconIndex=0
        ) > "%SHORTCUT_FILE_PATH%"
    )
    if exist "%SHORTCUT_FILE_PATH%" (
        echo Shortcut created successfully.
    ) else (
        echo ERROR: Failed to create shortcut.
    )
)
echo.

REM Open the browser
echo Opening browser to %SHORTCUT_TARGET_URL% ...
start %SHORTCUT_TARGET_URL%

echo.
echo AutoDubber should now be running!
echo.
echo To view logs, run: logs.bat or docker-compose logs -f
echo To stop, run: stop.bat
echo.
goto Cleanup

:EndScript
echo.
echo Script finished or user exited.
:Cleanup
endlocal
echo Press any key to close this window...
pause > nul