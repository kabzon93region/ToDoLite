@echo off
chcp 65001 >nul
title ToDoLite - Запуск в фоне

echo Активация виртуального окружения...
if not exist "ToDoLite_venv\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Сначала запустите setup_env.cmd для создания окружения
    pause
    exit /b 1
)

call ToDoLite_venv\Scripts\activate.bat

echo.
echo [INFO] Проверка порта 5000...
netstat -an | find ":5000" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Порт 5000 занят. Возможно, ToDoLite уже запущен.
    echo [INFO] Если программа не отвечает, используйте kill_python_processes.cmd
    echo.
    pause
    exit /b 1
)

echo [OK] Порт 5000 свободен
echo.
echo Запуск задачника с поддержкой трея...
start "" pythonw tray_app.py
exit
