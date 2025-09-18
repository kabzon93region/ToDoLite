@echo off
chcp 65001 >nul
echo Запуск простого обновления ToDoLite...
echo.

REM Проверяем PowerShell
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: PowerShell не найден!
    pause
    exit /b 1
)

REM Запускаем упрощенный скрипт
powershell -ExecutionPolicy Bypass -File "update_simple.ps1"

pause
