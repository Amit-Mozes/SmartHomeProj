@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m smart_home_project.server.main --host 127.0.0.1 --port 8820
