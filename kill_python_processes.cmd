@echo off
chcp 65001 >nul
echo ========================================
echo Закрытие процессов Python
echo ========================================
echo.

echo Поиск процессов pythonw.exe...
tasklist /FI "IMAGENAME eq pythonw.exe" 2>nul | find /I "pythonw.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Найдены процессы pythonw.exe:
    tasklist /FI "IMAGENAME eq pythonw.exe"
    echo.
    echo Закрытие процессов...
    taskkill /F /IM pythonw.exe
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Процессы pythonw.exe успешно закрыты
    ) else (
        echo ✗ Ошибка при закрытии процессов
    )
) else (
    echo ℹ Процессы pythonw.exe не найдены
)

echo.
echo Поиск процессов python.exe...
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Найдены процессы python.exe:
    tasklist /FI "IMAGENAME eq python.exe"
    echo.
    echo Закрытие процессов...
    taskkill /F /IM python.exe
    if %ERRORLEVEL% EQU 0 (
        echo ✓ Процессы python.exe успешно закрыты
    ) else (
        echo ✗ Ошибка при закрытии процессов
    )
) else (
    echo ℹ Процессы python.exe не найдены
)

echo.
echo ========================================
echo Проверка завершена
echo ========================================
pause
