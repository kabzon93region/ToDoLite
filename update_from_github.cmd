@echo off
echo ========================================
echo    ToDoLite - Обновление с GitHub
echo ========================================
echo.

REM Проверяем наличие PowerShell
powershell -Command "Get-Host" >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: PowerShell не найден на этом компьютере!
    echo Пожалуйста, установите PowerShell или обновите Windows.
    pause
    exit /b 1
)

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

REM PowerShell скрипт для загрузки и обновления
powershell -Command "& {
    try {
        # URL для загрузки архива с GitHub
        $repoUrl = 'https://api.github.com/repos/kabzon93region/ToDoLite/releases/latest'
        $downloadUrl = 'https://github.com/kabzon93region/ToDoLite/archive/refs/heads/main.zip'
        
        Write-Host 'Получаем информацию о последней версии...' -ForegroundColor Yellow
        
        # Загружаем архив
        $zipPath = 'temp_update\ToDoLite-main.zip'
        Write-Host 'Загружаем архив с GitHub...' -ForegroundColor Yellow
        Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
        
        if (Test-Path $zipPath) {
            Write-Host 'Архив успешно загружен!' -ForegroundColor Green
            
            # Создаем папку для распаковки
            $extractPath = 'temp_update\extracted'
            if (Test-Path $extractPath) {
                Remove-Item $extractPath -Recurse -Force
            }
            New-Item -ItemType Directory -Path $extractPath | Out-Null
            
            # Распаковываем архив
            Write-Host 'Распаковываем архив...' -ForegroundColor Yellow
            Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
            
            # Находим папку с проектом
            $projectPath = Get-ChildItem -Path $extractPath -Directory | Where-Object { $_.Name -like 'ToDoLite-*' } | Select-Object -First 1
            
            if ($projectPath) {
                Write-Host 'Найдена папка проекта: ' $projectPath.Name -ForegroundColor Green
                
                # Список файлов для обновления (исключаем конфиденциальные файлы)
                $filesToUpdate = @(
                    'app.py',
                    'templates\*.html',
                    'static\*',
                    'config.json',
                    'requirements.txt',
                    'README.md',
                    'docs\*',
                    '*.cmd',
                    '*.py'
                )
                
                # Список файлов для сохранения (не обновляем)
                $filesToKeep = @(
                    'tasks.db',
                    'ToDoLite_venv',
                    'temp_update',
                    '*.log'
                )
                
                Write-Host 'Обновляем файлы проекта...' -ForegroundColor Yellow
                
                # Обновляем файлы
                foreach ($pattern in $filesToUpdate) {
                    $sourceFiles = Get-ChildItem -Path $projectPath.FullName -Recurse -Include $pattern.Split('\')[-1] | Where-Object { $_.PSIsContainer -eq $false }
                    
                    foreach ($file in $sourceFiles) {
                        $relativePath = $file.FullName.Substring($projectPath.FullName.Length + 1)
                        $targetPath = Join-Path '.' $relativePath
                        $targetDir = Split-Path $targetPath -Parent
                        
                        # Создаем папку если не существует
                        if ($targetDir -and !(Test-Path $targetDir)) {
                            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                        }
                        
                        # Копируем файл
                        Copy-Item $file.FullName $targetPath -Force
                        Write-Host "  Обновлен: $relativePath" -ForegroundColor Cyan
                    }
                }
                
                Write-Host 'Обновление завершено успешно!' -ForegroundColor Green
                Write-Host 'Файлы базы данных и виртуального окружения сохранены.' -ForegroundColor Green
                
            } else {
                Write-Host 'ОШИБКА: Не удалось найти папку проекта в архиве!' -ForegroundColor Red
            }
            
        } else {
            Write-Host 'ОШИБКА: Не удалось загрузить архив!' -ForegroundColor Red
        }
        
    } catch {
        Write-Host 'ОШИБКА: ' $_.Exception.Message -ForegroundColor Red
    } finally {
        # Очищаем временные файлы
        if (Test-Path 'temp_update') {
            Remove-Item 'temp_update' -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}"

echo.
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
