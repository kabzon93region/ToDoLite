@echo off
chcp 65001 >nul

echo ========================================
echo    ToDoLite - Установка зависимостей
echo ========================================
echo.

echo Определение интерпретатора Python...
set "PYEXE="
set "PYFOUND=0"

rem 1) Python из PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYEXE=python"
    set "PYFOUND=1"
)

rem 2) Прямые пути
if %PYFOUND% equ 0 if exist "C:\Python\python.exe" (
    set "PYEXE=C:\Python\python.exe"
    set "PYFOUND=1"
)
if %PYFOUND% equ 0 if exist "C:\python\python.exe" (
    set "PYEXE=C:\python\python.exe"
    set "PYFOUND=1"
)

rem 3) Семейство C:\Python\Python3*\python.exe
if %PYFOUND% equ 0 (
    for /d %%D in (C:\Python\Python3*) do (
        if exist "%%D\python.exe" (
            set "PYEXE=%%D\python.exe"
            set "PYFOUND=1"
            goto :foundPy
        )
    )
)

rem 4) Семейство C:\python\Python3*\python.exe
if %PYFOUND% equ 0 (
    for /d %%D in (C:\python\Python3*) do (
        if exist "%%D\python.exe" (
            set "PYEXE=%%D\python.exe"
            set "PYFOUND=1"
            goto :foundPy
        )
    )
)

rem 5) Python Launcher (py -3)
if %PYFOUND% equ 0 (
    where py >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "usebackq delims=" %%E in (`py -3 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%E"
        if defined PYEXE set "PYFOUND=1"
    )
)

:foundPy
echo Используем Python: %PYEXE%

if %PYFOUND% equ 0 (
    echo ОШИБКА: Не найден Python ни в PATH, ни по путям C:\Python\python.exe / C:\python\python.exe или C:\Python\Python3*\python.exe
    echo Установите Python ^(например, в C:\Python\Python310\^) или добавьте его в PATH
    pause
    exit /b 1
)
echo.

:: Проверяем наличие requirements.txt
if not exist "requirements.txt" (
    echo ОШИБКА: Файл requirements.txt не найден!
    pause
    exit /b 1
)

echo Создание виртуального окружения ToDoLite_venv...
"%PYEXE%" -m venv ToDoLite_venv
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось создать виртуальное окружение
    pause
    exit /b 1
)

echo.
echo Активация виртуального окружения...
call ToDoLite_venv\Scripts\activate.bat

echo.
echo Обновление pip...
set "VENV_PY=ToDoLite_venv\Scripts\python.exe"
"%VENV_PY%" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.org:443 --trusted-host files.pythonhosted.org:443 --upgrade pip

echo.
echo Установка зависимостей...
"%VENV_PY%" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --trusted-host pypi.org:443 --trusted-host files.pythonhosted.org:443 -r requirements.txt
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось установить зависимости
    pause
    exit /b 1
)

echo.
echo Проверка установки...
"%VENV_PY%" -c "import flask, pystray, PIL, markdown; print('Все модули импортированы успешно')" 2>nul
if %errorlevel% equ 0 (
    echo Все модули работают корректно
) else (
    echo ПРЕДУПРЕЖДЕНИЕ: Возможны проблемы с модулями
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
echo   run_tray.bat     - запуск в трее
echo.
pause
