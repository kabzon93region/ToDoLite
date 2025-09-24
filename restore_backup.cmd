@echo off
chcp 65001 >nul
echo ========================================
echo    ToDoLite - Восстановление из резерва
echo ========================================
echo.

echo Доступные резервные копии:
echo.
dir /b tasks_backup_*.db 2>nul
echo.

if not exist "tasks_backup_*.db" (
    echo Резервные копии не найдены!
    echo.
    pause
    exit /b 1
)

set /p backup_file="Введите имя файла резервной копии (например, tasks_backup_20250924_021116.db): "

if not exist "%backup_file%" (
    echo Файл %backup_file% не найден!
    echo.
    pause
    exit /b 1
)

echo.
echo ВНИМАНИЕ: Это действие заменит текущую базу данных!
echo Текущая база данных будет переименована в tasks_old.db
echo.
set /p confirm="Продолжить? (y/N): "

if /i not "%confirm%"=="y" (
    echo Операция отменена.
    echo.
    pause
    exit /b 0
)

echo.
echo Создание резервной копии текущей базы данных...
if exist "tasks.db" (
    ren tasks.db tasks_old.db
    echo tasks.db переименована в tasks_old.db
)

echo.
echo Восстановление из резервной копии...
copy "%backup_file%" tasks.db
echo.

if exist "tasks.db" (
    echo ========================================
    echo     Восстановление завершено успешно!
    echo ========================================
    echo.
    echo Восстановлена база данных: %backup_file%
    echo Старая база данных сохранена как: tasks_old.db
    echo.
    echo Теперь можно запустить приложение.
) else (
    echo ОШИБКА: Не удалось восстановить базу данных!
    echo.
    if exist "tasks_old.db" (
        echo Восстанавливаем исходную базу данных...
        ren tasks_old.db tasks.db
    )
)

echo.
pause
