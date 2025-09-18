#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для конвертации окончаний строк из Unix (LF) в Windows (CRLF)
"""

import os
import sys

def convert_file(file_path):
    """Конвертирует файл из LF в CRLF"""
    try:
        # Читаем файл в бинарном режиме
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Проверяем, есть ли LF без CR
        if b'\n' in content and b'\r\n' not in content:
            # Заменяем LF на CRLF
            content = content.replace(b'\n', b'\r\n')
            
            # Записываем обратно
            with open(file_path, 'wb') as f:
                f.write(content)
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Ошибка при обработке {file_path}: {e}")
        return False

def main():
    """Основная функция"""
    print("Конвертация окончаний строк из Unix (LF) в Windows (CRLF)")
    print("=" * 60)
    
    # Расширения файлов для обработки
    extensions = ['.cmd', '.bat', '.txt', '.cfg', '.json', '.config', '.conf', '.py', '.html', '.css', '.js']
    
    converted = 0
    skipped = 0
    errors = 0
    
    print("Поиск файлов для конвертации (текущая папка без рекурсии)...")

    # Папка, где лежит сам скрипт
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Обрабатываем только файлы в текущей папке (без захода в подкаталоги и *env)
    for name in os.listdir(base_dir):
        file_path = os.path.join(base_dir, name)

        # Пропускаем папки
        if os.path.isdir(file_path):
            continue

        # Фильтруем по разрешённым расширениям
        _, ext = os.path.splitext(name)
        if ext.lower() not in extensions:
            continue

        print(f"Обработка: {file_path}")

        if convert_file(file_path):
            print(f"  ✓ Конвертирован")
            converted += 1
        else:
            print(f"  - Пропущен (уже CRLF или нет LF)")
            skipped += 1
    
    print("\n" + "=" * 60)
    print("Результаты конвертации:")
    print(f"Конвертировано файлов: {converted}")
    print(f"Пропущено файлов: {skipped}")
    print(f"Ошибок: {errors}")
    
    if converted > 0:
        print("\n✓ Конвертация завершена успешно!")
    else:
        print("\n- Нет файлов для конвертации.")
    
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
