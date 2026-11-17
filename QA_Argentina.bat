@echo off
setlocal
title Argentina - QA
set "RAIZ=%~dp0"
set "PY=%RAIZ%backend\.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%RAIZ%QA_Argentina.py"
echo.
echo  El informe tambien quedo guardado en qa_resultado.txt
pause
