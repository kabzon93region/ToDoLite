# ToDoLite - Обновление с GitHub
# PowerShell скрипт для загрузки и обновления проекта

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ToDoLite - Обновление с GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем подключение к интернету
Write-Host "Проверяем подключение к интернету..." -ForegroundColor Yellow
try {
    $ping = Test-Connection -ComputerName "github.com" -Count 1 -Quiet
    if (-not $ping) {
        throw "Нет подключения к интернету"
    }
    Write-Host "Подключение к интернету установлено." -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Проверьте подключение к интернету и попробуйте снова." -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Write-Host ""

# Создаем временную папку для загрузки
$tempDir = "temp_update"
if (Test-Path $tempDir) {
    Remove-Item $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

try {
    # URL для загрузки архива с GitHub
    $downloadUrl = 'https://github.com/kabzon93region/ToDoLite/archive/refs/heads/main.zip'
    
    Write-Host "Загружаем последнюю версию с GitHub..." -ForegroundColor Yellow
    
    # Загружаем архив
    $zipPath = Join-Path $tempDir "ToDoLite-main.zip"
    Write-Host "Загружаем архив с GitHub..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $downloadUrl -OutFile $zipPath -UseBasicParsing
    
    if (Test-Path $zipPath) {
        Write-Host "Архив успешно загружен!" -ForegroundColor Green
        
        # Создаем папку для распаковки
        $extractPath = Join-Path $tempDir "extracted"
        New-Item -ItemType Directory -Path $extractPath | Out-Null
        
        # Распаковываем архив
        Write-Host "Распаковываем архив..." -ForegroundColor Yellow
        Expand-Archive -Path $zipPath -DestinationPath $extractPath -Force
        
        # Находим папку с проектом
        $projectPath = Get-ChildItem -Path $extractPath -Directory | Where-Object { $_.Name -like "ToDoLite-*" } | Select-Object -First 1
        
        if ($projectPath) {
            Write-Host "Найдена папка проекта: $($projectPath.Name)" -ForegroundColor Green
            
            # Список файлов для обновления
            $filesToUpdate = @(
                "app.py",
                "templates",
                "static",
                "config.json",
                "requirements.txt",
                "README.md",
                "docs",
                "*.cmd",
                "*.py"
            )
            
            Write-Host "Обновляем файлы проекта..." -ForegroundColor Yellow
            
            # Обновляем файлы
            foreach ($pattern in $filesToUpdate) {
                if ($pattern.Contains("*")) {
                    # Для паттернов с маской
                    $sourceFiles = Get-ChildItem -Path $projectPath.FullName -Recurse -Include $pattern.Split("\")[-1] | Where-Object { $_.PSIsContainer -eq $false }
                } else {
                    # Для конкретных файлов/папок
                    $sourcePath = Join-Path $projectPath.FullName $pattern
                    if (Test-Path $sourcePath) {
                        if ((Get-Item $sourcePath).PSIsContainer) {
                            # Это папка
                            $sourceFiles = Get-ChildItem -Path $sourcePath -Recurse | Where-Object { $_.PSIsContainer -eq $false }
                        } else {
                            # Это файл
                            $sourceFiles = @(Get-Item $sourcePath)
                        }
                    } else {
                        $sourceFiles = @()
                    }
                }
                
                foreach ($file in $sourceFiles) {
                    $relativePath = $file.FullName.Substring($projectPath.FullName.Length + 1)
                    $targetPath = Join-Path "." $relativePath
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
            
            Write-Host "Обновление завершено успешно!" -ForegroundColor Green
            Write-Host "Файлы базы данных и виртуального окружения сохранены." -ForegroundColor Green
            
        } else {
            Write-Host "ОШИБКА: Не удалось найти папку проекта в архиве!" -ForegroundColor Red
        }
        
    } else {
        Write-Host "ОШИБКА: Не удалось загрузить архив!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Очищаем временные файлы
    if (Test-Path $tempDir) {
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Обновление завершено!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Для запуска обновленного приложения используйте:" -ForegroundColor Yellow
Write-Host "  .\run.bat" -ForegroundColor White
Write-Host ""
Write-Host "Или для запуска в фоновом режиме:" -ForegroundColor Yellow
Write-Host "  .\run_tray.bat" -ForegroundColor White
Write-Host ""
Read-Host "Нажмите Enter для выхода"