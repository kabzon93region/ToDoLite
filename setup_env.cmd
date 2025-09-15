@echo off
chcp 65001 >nul
echo ========================================
echo    Настройка виртуального окружения
echo ========================================
echo.

echo Создание виртуального окружения ToDoLite_venv...
python -m venv ToDoLite_venv
if errorlevel 1 (
    echo ОШИБКА: Не удалось создать виртуальное окружение
    echo Убедитесь, что Python установлен и добавлен в PATH
    pause
    exit /b 1
)

echo.
echo Активация виртуального окружения...
call ToDoLite_venv\Scripts\activate.bat

echo.
echo Обновление pip...
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.org:443 --trusted-host files.pythonhosted.org:443 --upgrade pip

echo.
echo Установка зависимостей...
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.org:443 --trusted-host files.pythonhosted.org:443 -r requirements.txt
if errorlevel 1 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Настройка завершена успешно!
echo ========================================
echo.
echo Виртуальное окружение создано: ToDoLite_venv
echo Зависимости установлены
echo.
echo Теперь можно запускать:
echo   run.bat          - обычный запуск
echo   run_tray.bat     - запуск с треем
echo.
pause