@echo off
chcp 65001 >nul
echo ========================================
echo    ToDoLite - Запуск в системном трее
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
echo Запуск задачника в системном трее...
echo Иконка появится в системном трее (рядом с часами)
echo.
echo Программа запущена! Окно можно закрыть.
echo Для управления используйте правую кнопку мыши на иконке в трее.
echo.
start "" python tray_app.py
timeout /t 3 /nobreak >nul
exit
