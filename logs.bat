@echo off
echo Showing logs for AutoDubber containers...
echo.
echo Use Ctrl+C to exit log view
echo.
echo To view only backend logs: docker-compose logs --follow backend
echo To view only frontend logs: docker-compose logs --follow frontend
echo.
docker-compose logs --follow 