#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный скрипт для исправления всех HTML таблиц в приложении
Исправляет таблицы в комментариях и описаниях задач
"""

import sqlite3
import re
import html
from logger import logger

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

def fix_comments():
    """Исправить комментарии с HTML таблицами"""
    logger.info("Исправляем комментарии с HTML таблицами", "TABLE_FIX")
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Ищем комментарии с таблицами
    c.execute("""
        SELECT id, task_id, comment, created_at 
        FROM task_comments 
        WHERE comment LIKE '%<table%' 
        OR comment LIKE '%<tr%' 
        OR comment LIKE '%<td%' 
        OR comment LIKE '%<th%'
    """)
    
    comments = c.fetchall()
    
    fixed_count = 0
    error_count = 0
    
    for comment_id, task_id, comment_content, created_at in comments:
        try:
            logger.info(f"Обрабатываем комментарий ID {comment_id} (задача {task_id})", "TABLE_FIX")
            
            # Исправляем HTML
            fixed_content = fix_table_html(comment_content)
            
            # Проверяем, изменился ли контент
            if fixed_content != comment_content:
                # Обновляем в базе данных
                c.execute("""
                    UPDATE task_comments 
                    SET comment = ? 
                    WHERE id = ?
                """, (fixed_content, comment_id))
                
                fixed_count += 1
                logger.info(f"Комментарий ID {comment_id} исправлен", "TABLE_FIX")
            else:
                logger.info(f"Комментарий ID {comment_id} не требует изменений", "TABLE_FIX")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке комментария ID {comment_id}: {e}", "TABLE_FIX")
            error_count += 1
    
    conn.commit()
    conn.close()
    
    logger.success(f"Комментарии: обработано {len(comments)}, исправлено {fixed_count}, ошибок {error_count}", "TABLE_FIX")
    return len(comments), fixed_count, error_count

def fix_descriptions():
    """Исправить описания задач с HTML таблицами"""
    logger.info("Исправляем описания задач с HTML таблицами", "TABLE_FIX")
    
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Ищем задачи с таблицами в описании
    c.execute("""
        SELECT id, title, full_description 
        FROM tasks 
        WHERE full_description LIKE '%<table%' 
        OR full_description LIKE '%<tr%' 
        OR full_description LIKE '%<td%' 
        OR full_description LIKE '%<th%'
    """)
    
    tasks = c.fetchall()
    
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
                c.execute("""
                    UPDATE tasks 
                    SET full_description = ? 
                    WHERE id = ?
                """, (fixed_content, task_id))
                
                fixed_count += 1
                logger.info(f"Описание задачи ID {task_id} исправлено", "TABLE_FIX")
            else:
                logger.info(f"Описание задачи ID {task_id} не требует изменений", "TABLE_FIX")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке задачи ID {task_id}: {e}", "TABLE_FIX")
            error_count += 1
    
    conn.commit()
    conn.close()
    
    logger.success(f"Описания: обработано {len(tasks)}, исправлено {fixed_count}, ошибок {error_count}", "TABLE_FIX")
    return len(tasks), fixed_count, error_count

def create_backup():
    """Создать резервную копию базы данных"""
    import shutil
    import datetime
    
    backup_name = f"tasks_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2('tasks.db', backup_name)
    logger.success(f"Создана резервная копия: {backup_name}", "TABLE_FIX")
    return backup_name

def main():
    """Основная функция"""
    logger.info("=== ИСПРАВЛЕНИЕ HTML ТАБЛИЦ ===", "TABLE_FIX")
    
    # Создаем резервную копию
    backup_name = create_backup()
    
    # Исправляем комментарии
    comments_total, comments_fixed, comments_errors = fix_comments()
    
    # Исправляем описания
    descriptions_total, descriptions_fixed, descriptions_errors = fix_descriptions()
    
    # Итоговая статистика
    total_processed = comments_total + descriptions_total
    total_fixed = comments_fixed + descriptions_fixed
    total_errors = comments_errors + descriptions_errors
    
    logger.success("=== ИСПРАВЛЕНИЕ ЗАВЕРШЕНО ===", "TABLE_FIX")
    logger.info(f"Резервная копия: {backup_name}", "TABLE_FIX")
    logger.info(f"Всего обработано: {total_processed}", "TABLE_FIX")
    logger.info(f"Исправлено: {total_fixed}", "TABLE_FIX")
    logger.info(f"Ошибок: {total_errors}", "TABLE_FIX")
    
    if total_fixed > 0:
        logger.info("Перезапустите приложение для применения изменений", "TABLE_FIX")

if __name__ == "__main__":
    main()
