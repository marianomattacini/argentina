@echo off
setlocal EnableExtensions
title Argentina - Detener

set "PUERTO_API=8000"
set "PUERTO_WEB=5500"

call :matar %PUERTO_API%
call :matar %PUERTO_WEB%

echo  Argentina detenido ^(puertos %PUERTO_API% y %PUERTO_WEB% liberados^).
timeout /t 2 >nul
exit /b 0

:matar
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%1 .*LISTENING"') do taskkill /PID %%P /T /F >nul 2>&1
exit /b 0