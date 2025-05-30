@echo off
echo Restarting the backend container...
echo.
docker-compose restart backend
echo.
echo Backend has been restarted. Check the logs with logs.bat to see if it's running properly.
echo. 