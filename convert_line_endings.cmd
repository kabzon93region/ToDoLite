@echo off
setlocal enabledelayedexpansion

echo Конвертация окончаний строк из Unix (LF) в Windows (CRLF)
echo ========================================================

REM Проверяем наличие PowerShell
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: PowerShell не найден. Установите PowerShell для выполнения скрипта.
    pause
    exit /b 1
)

REM Создаем временный PowerShell скрипт
set "ps_script=%temp%\convert_line_endings.ps1"

(
echo $extensions = @('.cmd', '.bat', '.txt', '.cfg', '.json', '.config', '.conf'^)
echo $converted = 0
echo $skipped = 0
echo $errors = 0
echo.
echo Write-Host "Поиск файлов для конвертации..." -ForegroundColor Yellow
echo.
echo foreach ($ext in $extensions^) {
echo     $files = Get-ChildItem -Path . -Filter "*$ext" -Recurse -File
echo     foreach ($file in $files^) {
echo         try {
echo             $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
echo             if ($content -and $content -notmatch "`r`n"^) {
echo                 $content = $content -replace "`n", "`r`n"
echo                 Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
echo                 Write-Host "Конвертирован: $($file.FullName^)" -ForegroundColor Green
echo                 $converted++
echo             } else {
echo                 Write-Host "Пропущен (уже CRLF^): $($file.FullName^)" -ForegroundColor Gray
echo                 $skipped++
echo             }
echo         } catch {
echo             Write-Host "Ошибка при обработке: $($file.FullName^) - $($_.Exception.Message^)" -ForegroundColor Red
echo             $errors++
echo         }
echo     }
echo }
echo.
echo Write-Host ""
echo Write-Host "Результаты конвертации:" -ForegroundColor Cyan
echo Write-Host "Конвертировано файлов: $converted" -ForegroundColor Green
echo Write-Host "Пропущено файлов: $skipped" -ForegroundColor Gray
echo Write-Host "Ошибок: $errors" -ForegroundColor Red
echo.
echo if ($converted -gt 0^) {
echo     Write-Host "Конвертация завершена успешно!" -ForegroundColor Green
echo } else {
echo     Write-Host "Нет файлов для конвертации." -ForegroundColor Yellow
echo }
) > "%ps_script%"

REM Выполняем PowerShell скрипт
echo Запуск конвертации...
powershell -ExecutionPolicy Bypass -File "%ps_script%"

REM Удаляем временный файл
del "%ps_script%" >nul 2>&1

echo.
echo Нажмите любую клавишу для выхода...
pause >nul
