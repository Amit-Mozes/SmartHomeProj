@echo off
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m smart_home_project.client.main
