# Простое обновление ToDoLite
Write-Host "ToDoLite - Простое обновление" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# Проверка интернета
Write-Host "Проверка подключения..." -ForegroundColor Yellow
try {
    $ping = Test-Connection -ComputerName "github.com" -Count 1 -Quiet
    if (-not $ping) {
        throw "Нет интернета"
    }
    Write-Host "Подключение OK" -ForegroundColor Green
} catch {
    Write-Host "ОШИБКА: Нет интернета!" -ForegroundColor Red
    Read-Host "Нажмите Enter"
    exit 1
}

# Создаем папку
$temp = "temp_update"
if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
New-Item -ItemType Directory -Path $temp | Out-Null

try {
    # Загружаем архив
    $url = 'https://github.com/kabzon93region/ToDoLite/archive/refs/heads/main.zip'
    $zip = "$temp\ToDoLite-main.zip"
    
    Write-Host "Загрузка архива..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    
    if (Test-Path $zip) {
        Write-Host "Архив загружен!" -ForegroundColor Green
        
        # Распаковываем
        $extract = "$temp\extracted"
        New-Item -ItemType Directory -Path $extract | Out-Null
        Expand-Archive -Path $zip -DestinationPath $extract -Force
        
        # Находим папку проекта
        $project = Get-ChildItem -Path $extract -Directory | Where-Object { $_.Name -like "ToDoLite-*" } | Select-Object -First 1
        
        if ($project) {
            Write-Host "Найдена папка: $($project.Name)" -ForegroundColor Green
            
            # Обновляем файлы
            Write-Host "Обновление файлов..." -ForegroundColor Yellow
            
            # Список файлов для обновления
            $files = @(
                "app.py",
                "templates\*",
                "static\*", 
                "config.json",
                "requirements.txt",
                "README.md",
                "docs\*",
                "*.cmd",
                "*.py"
            )
            
            foreach ($pattern in $files) {
                if ($pattern.Contains("*")) {
                    $sourceFiles = Get-ChildItem -Path $project.FullName -Recurse -Include $pattern.Split("\")[-1] | Where-Object { $_.PSIsContainer -eq $false }
                } else {
                    $sourcePath = Join-Path $project.FullName $pattern
                    if (Test-Path $sourcePath) {
                        if ((Get-Item $sourcePath).PSIsContainer) {
                            $sourceFiles = Get-ChildItem -Path $sourcePath -Recurse | Where-Object { $_.PSIsContainer -eq $false }
                        } else {
                            $sourceFiles = @(Get-Item $sourcePath)
                        }
                    } else {
                        $sourceFiles = @()
                    }
                }
                
                foreach ($file in $sourceFiles) {
                    $relativePath = $file.FullName.Substring($project.FullName.Length + 1)
                    $targetPath = Join-Path "." $relativePath
                    $targetDir = Split-Path $targetPath -Parent
                    
                    if ($targetDir -and !(Test-Path $targetDir)) {
                        New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                    }
                    
                    Copy-Item $file.FullName $targetPath -Force
                    Write-Host "  Обновлен: $relativePath" -ForegroundColor Cyan
                }
            }
            
            Write-Host "Обновление завершено!" -ForegroundColor Green
            Write-Host "Данные сохранены." -ForegroundColor Green
            
        } else {
            Write-Host "ОШИБКА: Папка проекта не найдена!" -ForegroundColor Red
        }
        
    } else {
        Write-Host "ОШИБКА: Не удалось загрузить архив!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "ОШИБКА: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if (Test-Path $temp) {
        Remove-Item $temp -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "Готово!" -ForegroundColor Cyan
Write-Host "Запуск: run.bat" -ForegroundColor Yellow
Write-Host "Фон: run_tray.bat" -ForegroundColor Yellow
Write-Host ""
Read-Host "Нажмите Enter"
