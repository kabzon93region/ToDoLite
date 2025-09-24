#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления старых описаний задач с HTML таблицами
Преобразует HTML код таблиц в корректно отображаемые таблицы
"""

import sqlite3
import re
import html
from logger import logger

def find_table_descriptions():
    """Найти описания задач с HTML таблицами"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Ищем описания, которые содержат HTML теги таблиц
    c.execute("""
        SELECT id, title, full_description 
        FROM tasks 
        WHERE full_description LIKE '%<table%' 
        OR full_description LIKE '%<tr%' 
        OR full_description LIKE '%<td%' 
        OR full_description LIKE '%<th%'
    """)
    
    tasks = c.fetchall()
    conn.close()
    
    logger.info(f"Найдено {len(tasks)} задач с HTML таблицами в описании", "TABLE_FIX")
    return tasks

def fix_table_html(html_content):
    """Исправить HTML таблицы для корректного отображения"""
    if not html_content:
        return html_content
    
    # Убираем лишние пробелы и переносы строк
    fixed = re.sub(r'\s+', ' ', html_content.strip())
    
    # Убираем атрибуты, которые могут мешать отображению
    # Оставляем только основные атрибуты
    fixed = re.sub(r'\s+style="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+class="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+width="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+height="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+border="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+cellpadding="[^"]*"', '', fixed)
    fixed = re.sub(r'\s+cellspacing="[^"]*"', '', fixed)
    
    # Убираем colgroup и col теги, которые могут мешать
    fixed = re.sub(r'<colgroup[^>]*>.*?</colgroup>', '', fixed, flags=re.DOTALL)
    fixed = re.sub(r'<col[^>]*/?>', '', fixed)
    
    # Упрощаем структуру таблицы
    # Убираем tbody если он есть, оставляем только table > tr > td/th
    fixed = re.sub(r'<tbody[^>]*>', '', fixed)
    fixed = re.sub(r'</tbody>', '', fixed)
    fixed = re.sub(r'<thead[^>]*>', '', fixed)
    fixed = re.sub(r'</thead>', '', fixed)
    fixed = re.sub(r'<tfoot[^>]*>', '', fixed)
    fixed = re.sub(r'</tfoot>', '', fixed)
    
    # Убираем лишние атрибуты из tr, td, th
    fixed = re.sub(r'<tr[^>]*>', '<tr>', fixed)
    fixed = re.sub(r'<td[^>]*>', '<td>', fixed)
    fixed = re.sub(r'<th[^>]*>', '<th>', fixed)
    fixed = re.sub(r'<table[^>]*>', '<table>', fixed)
    
    # Убираем лишние пробелы между тегами
    fixed = re.sub(r'>\s+<', '><', fixed)
    
    # Убираем пустые строки
    fixed = re.sub(r'\n\s*\n', '\n', fixed)
    
    return fixed.strip()

def update_task_description(task_id, new_description):
    """Обновить описание задачи в базе данных"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    c.execute("""
        UPDATE tasks 
        SET full_description = ? 
        WHERE id = ?
    """, (new_description, task_id))
    
    conn.commit()
    conn.close()
    
    logger.success(f"Описание задачи ID {task_id} обновлено", "TABLE_FIX")

def main():
    """Основная функция"""
    logger.info("Начинаем исправление описаний задач с HTML таблицами", "TABLE_FIX")
    
    # Находим задачи с таблицами в описании
    tasks = find_table_descriptions()
    
    if not tasks:
        logger.info("Задачи с HTML таблицами в описании не найдены", "TABLE_FIX")
        return
    
    fixed_count = 0
    error_count = 0
    
    for task_id, title, description_content in tasks:
        try:
            logger.info(f"Обрабатываем задачу ID {task_id}: '{title[:30]}...'", "TABLE_FIX")
            
            # Исправляем HTML
            fixed_content = fix_table_html(description_content)
            
            # Проверяем, изменился ли контент
            if fixed_content != description_content:
                # Обновляем в базе данных
                update_task_description(task_id, fixed_content)
                fixed_count += 1
                
                logger.info(f"Описание задачи ID {task_id} исправлено", "TABLE_FIX")
                logger.debug(f"Было: {description_content[:100]}...", "TABLE_FIX")
                logger.debug(f"Стало: {fixed_content[:100]}...", "TABLE_FIX")
            else:
                logger.info(f"Описание задачи ID {task_id} не требует изменений", "TABLE_FIX")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи ID {task_id}: {e}", "TABLE_FIX")
            error_count += 1
    
    logger.success(f"Исправление завершено. Обработано: {len(tasks)}, исправлено: {fixed_count}, ошибок: {error_count}", "TABLE_FIX")

if __name__ == "__main__":
    main()
