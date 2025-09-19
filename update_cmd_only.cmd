@echo off
chcp 65001 >nul
echo ========================================
echo    ToDoLite - Обновление с GitHub
echo ========================================
echo.

echo Проверяем подключение к интернету...
ping -n 1 github.com >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Нет подключения к интернету!
    echo Проверьте подключение к интернету и попробуйте снова.
    pause
    exit /b 1
)

echo Подключение к интернету установлено.
echo.

REM Создаем временную папку для загрузки
if not exist "temp_update" mkdir temp_update

echo Загружаем последнюю версию с GitHub...
echo.

REM Используем curl для загрузки (если доступен)
curl --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Используем curl для загрузки...
    curl -L -o "temp_update\ToDoLite-main.zip" "https://github.com/kabzon93region/ToDoLite/archive/refs/heads/main.zip"
) else (
    echo curl не найден, используем PowerShell...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/kabzon93region/ToDoLite/archive/refs/heads/main.zip' -OutFile 'temp_update\ToDoLite-main.zip'"
)

if not exist "temp_update\ToDoLite-main.zip" (
    echo ОШИБКА: Не удалось загрузить архив!
    pause
    exit /b 1
)

echo Архив успешно загружен!
echo.

REM Распаковываем архив
echo Распаковываем архив...
powershell -Command "Expand-Archive -Path 'temp_update\ToDoLite-main.zip' -DestinationPath 'temp_update\extracted' -Force"

if not exist "temp_update\extracted" (
    echo ОШИБКА: Не удалось распаковать архив!
    pause
    exit /b 1
)

echo Архив распакован!
echo.

REM Находим папку проекта
for /d %%i in ("temp_update\extracted\ToDoLite-*") do set PROJECT_PATH=%%i

if not defined PROJECT_PATH (
    echo ОШИБКА: Не удалось найти папку проекта в архиве!
    pause
    exit /b 1
)

echo Найдена папка проекта: %PROJECT_PATH%
echo.

REM Обновляем файлы
echo Обновляем файлы проекта...

REM Копируем основные файлы
if exist "%PROJECT_PATH%\app.py" copy "%PROJECT_PATH%\app.py" "app.py" >nul
if exist "%PROJECT_PATH%\config.json" copy "%PROJECT_PATH%\config.json" "config.json" >nul
if exist "%PROJECT_PATH%\requirements.txt" copy "%PROJECT_PATH%\requirements.txt" "requirements.txt" >nul
if exist "%PROJECT_PATH%\README.md" copy "%PROJECT_PATH%\README.md" "README.md" >nul

REM Копируем папки
if exist "%PROJECT_PATH%\templates" (
    if exist "templates" rmdir /s /q "templates"
    xcopy "%PROJECT_PATH%\templates" "templates\" /e /i /h /y >nul
    echo   Обновлена папка: templates
)

if exist "%PROJECT_PATH%\static" (
    if exist "static" rmdir /s /q "static"
    xcopy "%PROJECT_PATH%\static" "static\" /e /i /h /y >nul
    echo   Обновлена папка: static
)

if exist "%PROJECT_PATH%\docs" (
    if exist "docs" rmdir /s /q "docs"
    xcopy "%PROJECT_PATH%\docs" "docs\" /e /i /h /y >nul
    echo   Обновлена папка: docs
)

REM Копируем CMD и PY файлы
for %%f in ("%PROJECT_PATH%\*.cmd") do (
    copy "%%f" "%%~nxf" >nul
    echo   Обновлен файл: %%~nxf
)

for %%f in ("%PROJECT_PATH%\*.py") do (
    if not "%%~nxf"=="app.py" (
        copy "%%f" "%%~nxf" >nul
        echo   Обновлен файл: %%~nxf
    )
)

echo.
echo Обновление завершено успешно!
echo Файлы базы данных и виртуального окружения сохранены.
echo.

REM Очищаем временные файлы
rmdir /s /q "temp_update" >nul 2>&1

echo ========================================
echo    Обновление завершено!
echo ========================================
echo.
echo Для запуска обновленного приложения используйте:
echo   run.bat
echo.
echo Или для запуска в фоновом режиме:
echo   run_tray.bat
echo.
pause
