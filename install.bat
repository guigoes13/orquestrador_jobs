@echo off
setlocal
cd /d "%~dp0"

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permissao de administrador...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup.ps1"
set "INSTALL_EXIT=%errorlevel%"

echo.
if "%INSTALL_EXIT%"=="2" (
    echo Preencha o ConfigApp.ini e execute install.bat novamente.
) else if not "%INSTALL_EXIT%"=="0" (
    echo A instalacao falhou. Consulte as mensagens acima.
) else (
    echo Instalacao concluida com sucesso.
)
pause
exit /b %INSTALL_EXIT%
