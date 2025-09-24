@echo off
chcp 65001 >nul
echo ========================================
echo    ToDoLite - Исправление HTML таблиц
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
echo Запуск исправления HTML таблиц...
echo.
echo ВНИМАНИЕ: Будет создана резервная копия базы данных!
echo.

python fix_tables_smart.py

echo.
echo ========================================
echo        Исправление завершено!
echo ========================================
echo.
echo Рекомендации:
echo 1. Проверьте результат в приложении
echo 2. Если что-то пошло не так, восстановите из резервной копии
echo 3. Резервная копия создана автоматически
echo.
pause
