#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для исправления старых комментариев с HTML таблицами
Преобразует HTML код таблиц в корректно отображаемые таблицы
"""

import sqlite3
import re
import html
from logger import logger

def find_table_comments():
    """Найти комментарии с HTML таблицами"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Ищем комментарии, которые содержат HTML теги таблиц
    c.execute("""
        SELECT id, task_id, comment, created_at 
        FROM task_comments 
        WHERE comment LIKE '%<table%' 
        OR comment LIKE '%<tr%' 
        OR comment LIKE '%<td%' 
        OR comment LIKE '%<th%'
    """)
    
    comments = c.fetchall()
    conn.close()
    
    logger.info(f"Найдено {len(comments)} комментариев с HTML таблицами", "TABLE_FIX")
    return comments

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

def update_comment(comment_id, new_content):
    """Обновить комментарий в базе данных"""
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    c.execute("""
        UPDATE task_comments 
        SET comment = ? 
        WHERE id = ?
    """, (new_content, comment_id))
    
    conn.commit()
    conn.close()
    
    logger.success(f"Комментарий ID {comment_id} обновлен", "TABLE_FIX")

def main():
    """Основная функция"""
    logger.info("Начинаем исправление комментариев с HTML таблицами", "TABLE_FIX")
    
    # Находим комментарии с таблицами
    comments = find_table_comments()
    
    if not comments:
        logger.info("Комментарии с HTML таблицами не найдены", "TABLE_FIX")
        return
    
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
                update_comment(comment_id, fixed_content)
                fixed_count += 1
                
                logger.info(f"Комментарий ID {comment_id} исправлен", "TABLE_FIX")
                logger.debug(f"Было: {comment_content[:100]}...", "TABLE_FIX")
                logger.debug(f"Стало: {fixed_content[:100]}...", "TABLE_FIX")
            else:
                logger.info(f"Комментарий ID {comment_id} не требует изменений", "TABLE_FIX")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке комментария ID {comment_id}: {e}", "TABLE_FIX")
            error_count += 1
    
    logger.success(f"Исправление завершено. Обработано: {len(comments)}, исправлено: {fixed_count}, ошибок: {error_count}", "TABLE_FIX")

if __name__ == "__main__":
    main()
