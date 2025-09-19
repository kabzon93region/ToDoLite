@echo off
chcp 65001 >nul
echo ========================================
echo         ToDoLite - Консольный запуск
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
echo Запуск задачника...
echo Откройте браузер и перейдите по адресу: http://localhost:5000
echo.
echo Для остановки нажмите Ctrl+C
echo.
python app.py
pause
