@echo off
chcp 65001 >nul
echo ========================================
echo    Запуск задачника с поддержкой трея
echo ========================================
echo.

echo Активация виртуального окружения...
if not exist "ToDoLite_venv\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Сначала запустите setup_env.cmd для создания окружения
    echo.
    pause
    exit /b 1
)

call ToDoLite_venv\Scripts\activate.bat

echo.
echo Запуск задачника с поддержкой трея...
echo Иконка появится в системном трее (рядом с часами)
echo.
python tray_app.py
