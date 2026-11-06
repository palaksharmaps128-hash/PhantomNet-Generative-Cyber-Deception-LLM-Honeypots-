@echo off
rem Double-click to start the PhantomNet demo (API + dashboard).
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0start_demo.ps1"