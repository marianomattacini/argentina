@echo off
setlocal EnableExtensions
title Argentina - Lanzador
chcp 65001 >nul

rem ============================================================
rem  Argentina - Lanzador (backend + frontend en un click)
rem  Poner este archivo en la RAIZ del repo (junto a backend\ y frontend\)
rem ============================================================

set "RAIZ=%~dp0"
set "BACKEND=%RAIZ%backend"
set "FRONT=%RAIZ%frontend\frontend"
set "VENV=%BACKEND%\.venv"
set "PY=%VENV%\Scripts\python.exe"
set "PUERTO_API=8000"
set "PUERTO_WEB=5500"
set "URL=http://127.0.0.1:%PUERTO_WEB%/index.html"

echo.
echo  =====================================================
echo    ARGENTINA - iniciando...
echo  =====================================================
echo.

if not exist "%BACKEND%\manage.py" (
    echo  [ERROR] No encuentro "%BACKEND%\manage.py".
    echo          Este .bat tiene que estar en la carpeta raiz del proyecto.
    pause
    exit /b 1
)
if not exist "%FRONT%\index.html" (
    echo  [ERROR] No encuentro "%FRONT%\index.html".
    pause
    exit /b 1
)

rem ---------- 1. Buscar un Python que funcione de verdad ----------
rem (se prueba que tenga tempfile, sqlite3, venv y ensurepip; hay instalaciones danadas)
set "PYBASE="
for %%V in (3.13 3.12 3.14 3) do (
    if not defined PYBASE (
        py -%%V -c "import tempfile,sqlite3,ensurepip,venv" >nul 2>&1
        if not errorlevel 1 set "PYBASE=py -%%V"
    )
)
if not defined PYBASE (
    python -c "import tempfile,sqlite3,ensurepip,venv" >nul 2>&1
    if not errorlevel 1 set "PYBASE=python"
)
if not defined PYBASE (
    echo  [ERROR] No hay un Python 3.12 o superior que funcione en esta PC.
    echo          Si tenias uno, esta danado ^(le faltan modulos como tempfile^).
    echo          Instala Python 3.13 desde https://www.python.org/downloads/
    echo          marcando "Add python.exe to PATH" y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)
echo  Usando Python: %PYBASE%

rem ---------- 2. Entorno virtual local (se crea solo la primera vez) ----------
set "VENV_OK=0"
if exist "%PY%" (
    "%PY%" -c "import tempfile,sqlite3" >nul 2>&1
    if not errorlevel 1 set "VENV_OK=1"
)
if "%VENV_OK%"=="0" (
    echo  [1/4] Creando entorno virtual ^(solo la primera vez^)...
    if exist "%VENV%" rmdir /s /q "%VENV%"
    %PYBASE% -m venv --without-pip "%VENV%"
    if errorlevel 1 (
        echo  [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo  [1/4] Entorno virtual OK.
)

rem ---------- 3. Dependencias ----------
rem Si existe backend\requirements.txt se usa; si no, se instalan por nombre.
set "REQARGS=Django djangorestframework django-cors-headers"
if exist "%BACKEND%\requirements.txt" set "REQARGS=-r "%BACKEND%\requirements.txt""
"%PY%" -c "import django, rest_framework, corsheaders" >nul 2>&1
if not errorlevel 1 (
    echo  [2/4] Dependencias OK.
    goto deps_listas
)

echo  [2/4] Instalando dependencias ^(requiere internet, solo la primera vez^)...
"%PY%" -m pip --version >nul 2>&1
if errorlevel 1 goto deps_con_pip_base

"%PY%" -m pip install --disable-pip-version-check %REQARGS%
if errorlevel 1 goto deps_error
goto deps_listas

:deps_con_pip_base
rem El entorno no trae pip: se usa el pip del Python base apuntando al entorno.
%PYBASE% -m pip --disable-pip-version-check --python "%PY%" install %REQARGS%
if errorlevel 1 goto deps_error
goto deps_listas

:deps_error
echo.
echo  [ERROR] Fallo la instalacion de dependencias.
echo          Revisa que haya internet y mandame el mensaje de arriba.
pause
exit /b 1

:deps_listas

rem ---------- 4. Base de datos ----------
echo  [3/4] Actualizando base de datos...
"%PY%" "%BACKEND%\manage.py" migrate --noinput >nul
if errorlevel 1 (
    echo  [ERROR] Fallo "manage.py migrate". Ejecutalo a mano para ver el detalle.
    pause
    exit /b 1
)

rem ---------- 5. Levantar servidores ----------
echo  [4/4] Levantando servidores...

rem Se cierran servidores viejos que hayan quedado abiertos, para no usar una version anterior.
call :matar %PUERTO_API%
call :matar %PUERTO_WEB%

rem El backend guarda sus mensajes en backend\servidor.log (sirve para ver errores).
start "Argentina - Backend" /min cmd /c ""%PY%" "%BACKEND%\manage.py" runserver 127.0.0.1:%PUERTO_API% --noreload >"%BACKEND%\servidor.log" 2>&1"
start "Argentina - Frontend" /min cmd /c ""%PY%" -m http.server %PUERTO_WEB% --bind 127.0.0.1 --directory "%FRONT%""

rem ---------- 6. Esperar a que el backend responda (maximo ~30 s) ----------
set /a INTENTOS=0
:esperar
curl -s -o nul http://127.0.0.1:%PUERTO_API%/api/partidas/X/ >nul 2>&1
if not errorlevel 1 goto listo
set /a INTENTOS+=1
if %INTENTOS% GEQ 30 goto listo
ping -n 2 127.0.0.1 >nul
goto esperar
:listo

rem ---------- 7. Abrir como ventana de aplicacion (Chrome / Edge) ----------
set "NAV="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "NAV=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "NAV=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%LocalAppData%\Google\Chrome\Application\chrome.exe" set "NAV=%LocalAppData%\Google\Chrome\Application\chrome.exe"
if not defined NAV if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "NAV=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined NAV if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "NAV=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if defined NAV goto abrir_app
start "" "%URL%"
goto abierto
:abrir_app
start "" "%NAV%" --app=%URL%
:abierto

echo.
echo  =====================================================
echo    Argentina esta corriendo:
echo      Juego : %URL%
echo      API   : http://127.0.0.1:%PUERTO_API%/api/
echo.
echo    PARA APAGAR TODO: presiona cualquier tecla en esta
echo    ventana ^(o ejecuta Detener_Argentina.bat^).
echo  =====================================================
pause >nul

call :matar %PUERTO_API%
call :matar %PUERTO_WEB%
echo  Servidores detenidos. Hasta la proxima!
timeout /t 2 >nul
exit /b 0

:matar
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%1 .*LISTENING"') do taskkill /PID %%P /T /F >nul 2>&1
exit /b 0