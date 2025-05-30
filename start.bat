@echo off
echo Starting AutoDubber with Docker...
echo.
echo This will:
echo - Download and install all dependencies
echo - Start the frontend on http://localhost:5173
echo - Start the backend API on http://localhost:8000
echo.
echo Press Ctrl+C to stop the application
echo.
docker-compose up --build 