#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный скрипт для исправления HTML таблиц
Правильно обрабатывает как старые сложные таблицы, так и новые простые
"""

import sqlite3
import re
import html
from logger import logger

def is_complex_table(html_content):
    """Проверить, является ли таблица сложной (старой)"""
    if not html_content:
        return False
    
    # Проверяем наличие сложных атрибутов
    complex_indicators = [
        r'style="[^"]*"',
        r'class="[^"]*"',
        r'width="[^"]*"',
        r'height="[^"]*"',
        r'cellpadding="[^"]*"',
        r'cellspacing="[^"]*"',
        r'<colgroup',
        r'<col[^>]*>',
        r'<tbody',
        r'<thead',
        r'<tfoot'
    ]
    
    for indicator in complex_indicators:
        if re.search(indicator, html_content, re.IGNORECASE):
            return True
    
    return False

def fix_complex_table(html_content):
    """Исправить сложную (старую) таблицу"""
    if not html_content:
        return html_content
    
    # Убираем лишние пробелы и переносы строк
    fixed = re.sub(r'\s+', ' ', html_content.strip())
    
    # Убираем colgroup и col теги
    fixed = re.sub(r'<colgroup[^>]*>.*?</colgroup>', '', fixed, flags=re.DOTALL | re.IGNORECASE)
    fixed = re.sub(r'<col[^>]*/?>', '', fixed, flags=re.IGNORECASE)
    
    # Убираем tbody, thead, tfoot
    fixed = re.sub(r'<tbody[^>]*>', '', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'</tbody>', '', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'<thead[^>]*>', '', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'</thead>', '', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'<tfoot[^>]*>', '', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'</tfoot>', '', fixed, flags=re.IGNORECASE)
    
    # Очищаем атрибуты, но сохраняем важные для таблиц
    # Для table - сохраняем border, cellpadding, cellspacing, width
    fixed = re.sub(r'<table[^>]*style="[^"]*"[^>]*>', '<table>', fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'<table[^>]*class="[^"]*"[^>]*>', '<table>', fixed, flags=re.IGNORECASE)
    
    # Для tr - убираем все атрибуты
    fixed = re.sub(r'<tr[^>]*>', '<tr>', fixed, flags=re.IGNORECASE)
    
    # Для td и th - сохраняем width, но убираем style, class, height
    def clean_td_th(match):
        tag = match.group(0)
        # Извлекаем width если есть
        width_match = re.search(r'width="([^"]*)"', tag, re.IGNORECASE)
        if width_match:
            width = width_match.group(1)
            return f'<{tag[1:3]} width="{width}">'
        else:
            return f'<{tag[1:3]}>'
    
    fixed = re.sub(r'<td[^>]*>', clean_td_th, fixed, flags=re.IGNORECASE)
    fixed = re.sub(r'<th[^>]*>', clean_td_th, fixed, flags=re.IGNORECASE)
    
    # Убираем лишние пробелы между тегами
    fixed = re.sub(r'>\s+<', '><', fixed)
    
    # Убираем пустые строки
    fixed = re.sub(r'\n\s*\n', '\n', fixed)
    
    return fixed.strip()

def fix_simple_table(html_content):
    """Исправить простую (новую) таблицу - минимальные изменения"""
    if not html_content:
        return html_content
    
    # Только убираем лишние пробелы
    fixed = re.sub(r'\s+', ' ', html_content.strip())
    fixed = re.sub(r'>\s+<', '><', fixed)
    
    return fixed.strip()

def fix_table_html(html_content):
    """Умное исправление HTML таблиц"""
    if not html_content:
        return html_content
    
    # Проверяем, есть ли таблицы в контенте
    if not re.search(r'<table[^>]*>', html_content, re.IGNORECASE):
        return html_content
    
    # Разбиваем контент на части (до таблицы, таблица, после таблицы)
    parts = []
    last_end = 0
    
    for match in re.finditer(r'<table[^>]*>.*?</table>', html_content, re.DOTALL | re.IGNORECASE):
        # Добавляем текст до таблицы
        if match.start() > last_end:
            parts.append(html_content[last_end:match.start()])
        
        # Обрабатываем таблицу
        table_html = match.group(0)
        if is_complex_table(table_html):
            fixed_table = fix_complex_table(table_html)
            logger.debug(f"Исправлена сложная таблица: {table_html[:50]}... -> {fixed_table[:50]}...", "TABLE_FIX")
        else:
            fixed_table = fix_simple_table(table_html)
            logger.debug(f"Обработана простая таблица: {table_html[:50]}...", "TABLE_FIX")
        
        parts.append(fixed_table)
        last_end = match.end()
    
    # Добавляем оставшийся текст
    if last_end < len(html_content):
        parts.append(html_content[last_end:])
    
    return ''.join(parts)

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
    logger.info("=== УМНОЕ ИСПРАВЛЕНИЕ HTML ТАБЛИЦ ===", "TABLE_FIX")
    
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
