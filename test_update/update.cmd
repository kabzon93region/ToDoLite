@echo off
chcp 65001 >nul
echo Запуск обновления ToDoLite...
echo.

REM Проверяем наличие PowerShell
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: PowerShell не найден на этом компьютере!
    echo Пожалуйста, установите PowerShell или обновите Windows.
    pause
    exit /b 1
)

REM Запускаем PowerShell скрипт
powershell -ExecutionPolicy Bypass -File "update_from_github.ps1"

pause