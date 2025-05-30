@echo off
echo Starting AutoDubber with Docker...
echo.
echo This will:
echo - Download and install all dependencies
echo - Start the frontend on http://localhost:5173
echo - Start the backend API on http://localhost:8000
echo - Open your browser to the application
echo.
echo Starting containers...
echo.

REM Start the containers in detached mode
docker-compose up -d --build

REM Wait a few seconds for the services to start
echo.
echo Waiting for services to start...
timeout /t 5 /nobreak > nul

REM Open the browser
echo Opening browser...
start http://localhost:5173

echo.
echo AutoDubber is running!
echo.
echo To view logs, run: logs.bat or docker-compose logs -f
echo To stop, run: stop.bat
echo. 