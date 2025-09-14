@echo off
chcp 65001 >nul

echo Активация виртуального окружения...
if not exist "ToDoLite_venv\Scripts\activate.bat" (
    echo ОШИБКА: Виртуальное окружение не найдено!
    echo Сначала запустите setup_env.cmd для создания окружения
    pause
    exit /b 1
)

call ToDoLite_venv\Scripts\activate.bat

echo Запуск задачника...
start "" pythonw tray_app.py
exit
