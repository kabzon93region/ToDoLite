@echo off
echo Конвертация окончаний строк из Unix (LF) в Windows (CRLF)
echo ========================================================

REM Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не найден. Установите Python для выполнения скрипта.
    pause
    exit /b 1
)

REM Запускаем Python скрипт
echo Запуск конвертации...
python convert_line_endings.py

pause