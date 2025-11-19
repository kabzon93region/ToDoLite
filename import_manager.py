#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Менеджер импорта задач
"""

import sqlite3
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from logger import logger

class ImportManager:
    """
    Управляет импортом задач из различных форматов.
    """
    
    def __init__(self, db_path='tasks.db'):
        self.db_path = db_path
        logger.info("ImportManager инициализирован", "IMPORT")
    
    def _validate_task_data(self, task_data):
        """Валидирует данные задачи."""
        required_fields = ['title']
        
        for field in required_fields:
            if field not in task_data or not task_data[field]:
                return False, f"Отсутствует обязательное поле: {field}"
        
        # Проверяем типы данных
        if not isinstance(task_data['title'], str):
            return False, "Поле 'title' должно быть строкой"
        
        # description не обязательное поле
        
        # Проверяем статус
        valid_statuses = ['new', 'later', 'tracking', 'working', 'waiting', 'think', 'done', 'cancelled']
        if 'status' in task_data and task_data['status'] not in valid_statuses:
            return False, f"Недопустимый статус: {task_data['status']}"
        
        # Проверяем приоритет
        valid_priorities = ['low', 'medium', 'high', 'urgent']
        if 'priority' in task_data and task_data['priority'] not in valid_priorities:
            return False, f"Недопустимый приоритет: {task_data['priority']}"
        
        # Проверяем Eisenhower приоритет
        valid_eisenhower = ['urgent_important', 'urgent_not_important', 'not_urgent_important', 'not_urgent_not_important']
        if 'eisenhower' in task_data and task_data['eisenhower'] not in valid_eisenhower:
            return False, f"Недопустимый Eisenhower приоритет: {task_data['eisenhower']}"
        
        return True, "OK"
    
    def _parse_import_file(self, file_path):
        """Парсит файл импорта и возвращает список задач."""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.json':
                return self._parse_json(file_path)
            elif file_ext == '.csv':
                return self._parse_csv(file_path)
            elif file_ext == '.xml':
                return self._parse_xml(file_path)
            else:
                logger.error(f"Неподдерживаемый формат файла: {file_ext}", "IMPORT")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка парсинга файла {file_path}: {e}", "IMPORT")
            return None
    
    def _parse_json(self, file_path):
        """Парсит JSON файл."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Проверяем структуру файла
            if isinstance(data, dict) and 'tasks' in data:
                tasks = data['tasks']
                logger.info(f"Найдено {len(tasks)} задач в JSON файле", "IMPORT")
                return tasks
            elif isinstance(data, list):
                logger.info(f"Найдено {len(data)} задач в JSON файле", "IMPORT")
                return data
            else:
                logger.error("Некорректная структура JSON файла", "IMPORT")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка чтения JSON файла: {e}", "IMPORT")
            return None
    
    def _parse_csv(self, file_path):
        """Парсит CSV файл."""
        try:
            tasks = []
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Обрабатываем специальные поля
                    if 'comments' in row and row['comments']:
                        row['comments'] = [comment.strip() for comment in row['comments'].split('|') if comment.strip()]
                    else:
                        row['comments'] = []
                    
                    if 'tags' in row and row['tags']:
                        row['tags'] = [tag.strip() for tag in row['tags'].split(',') if tag.strip()]
                    else:
                        row['tags'] = []
                    
                    # Преобразуем пустые строки в None
                    for key, value in row.items():
                        if value == '':
                            row[key] = None
                    
                    tasks.append(row)
            
            logger.info(f"Найдено {len(tasks)} задач в CSV файле", "IMPORT")
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка чтения CSV файла: {e}", "IMPORT")
            return None
    
    def _parse_xml(self, file_path):
        """Парсит XML файл."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            tasks = []
            
            # Ищем задачи в XML
            for task_element in root.findall('.//task'):
                task = {}
                
                # Обрабатываем основные поля
                for child in task_element:
                    if child.tag == 'comments':
                        # Обрабатываем комментарии
                        comments = []
                        for comment_elem in child.findall('comment'):
                            if comment_elem.text:
                                comments.append(comment_elem.text.strip())
                        task['comments'] = comments
                    elif child.tag == 'tags':
                        # Обрабатываем теги
                        tags = []
                        for tag_elem in child.findall('tag'):
                            if tag_elem.text:
                                tags.append(tag_elem.text.strip())
                        task['tags'] = tags
                    else:
                        # Обычные поля
                        if child.text:
                            task[child.tag] = child.text.strip()
                
                tasks.append(task)
            
            logger.info(f"Найдено {len(tasks)} задач в XML файле", "IMPORT")
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка чтения XML файла: {e}", "IMPORT")
            return None
    
    def _create_task(self, task_data):
        """Создает задачу в базе данных."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Подготавливаем данные для вставки
            task_fields = {
                'title': task_data.get('title', ''),
                'short_description': task_data.get('description', ''),
                'full_description': task_data.get('description', ''),
                'status': task_data.get('status', 'new'),
                'priority': task_data.get('priority', 'medium'),
                'eisenhower_priority': task_data.get('eisenhower', 'not_urgent_not_important'),
                'assigned_to': task_data.get('assigned_to'),
                'due_date': task_data.get('due_date'),
                'related_threads': task_data.get('related_threads'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Вставляем задачу
            cursor.execute("""
                INSERT INTO tasks (title, short_description, full_description, status, priority, eisenhower_priority, 
                                 assigned_to, due_date, related_threads, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tuple(task_fields.values()))
            
            task_id = cursor.lastrowid
            
            # Добавляем комментарии
            if task_data.get('comments'):
                for comment_text in task_data['comments']:
                    if comment_text.strip():
                        cursor.execute("""
                            INSERT INTO task_comments (task_id, comment, created_at)
                            VALUES (?, ?, ?)
                        """, (task_id, comment_text.strip(), datetime.now().isoformat()))
            
            # Добавляем теги (хранятся как строка в поле tags)
            if task_data.get('tags'):
                tags_string = ', '.join([tag.strip() for tag in task_data['tags'] if tag.strip()])
                cursor.execute("""
                    UPDATE tasks SET tags = ? WHERE id = ?
                """, (tags_string, task_id))
            
            conn.commit()
            conn.close()
            
            return task_id
            
        except Exception as e:
            logger.error(f"Ошибка создания задачи: {e}", "IMPORT")
            return None
    
    def import_tasks(self, file_path, conflict_resolution='skip'):
        """
        Импортирует задачи из файла.
        
        Args:
            file_path: Путь к файлу импорта
            conflict_resolution: Стратегия разрешения конфликтов ('skip', 'overwrite', 'rename')
        
        Returns:
            dict: Результат импорта с статистикой
        """
        try:
            logger.info(f"Начало импорта из файла: {file_path}", "IMPORT")
            
            # Парсим файл
            tasks_data = self._parse_import_file(file_path)
            if not tasks_data:
                return {
                    'success': False,
                    'error': 'Не удалось прочитать файл импорта',
                    'imported': 0,
                    'skipped': 0,
                    'errors': 0
                }
            
            # Статистика импорта
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # Импортируем каждую задачу
            for i, task_data in enumerate(tasks_data):
                try:
                    # Валидируем данные
                    is_valid, error_msg = self._validate_task_data(task_data)
                    if not is_valid:
                        error_count += 1
                        errors.append(f"Задача {i+1}: {error_msg}")
                        continue
                    
                    # Проверяем конфликты (по заголовку)
                    if conflict_resolution == 'skip':
                        conn = sqlite3.connect(self.db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT id FROM tasks WHERE title = ?", (task_data['title'],))
                        if cursor.fetchone():
                            skipped_count += 1
                            conn.close()
                            continue
                        conn.close()
                    
                    # Создаем задачу
                    task_id = self._create_task(task_data)
                    if task_id:
                        imported_count += 1
                        logger.debug(f"Импортирована задача: {task_data['title']}", "IMPORT")
                    else:
                        error_count += 1
                        errors.append(f"Задача {i+1}: Ошибка создания в БД")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Задача {i+1}: {str(e)}")
                    logger.error(f"Ошибка импорта задачи {i+1}: {e}", "IMPORT")
            
            result = {
                'success': True,
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': error_count,
                'total': len(tasks_data),
                'error_details': errors
            }
            
            logger.success(f"Импорт завершен: {imported_count} импортировано, {skipped_count} пропущено, {error_count} ошибок", "IMPORT")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка импорта: {e}", "IMPORT")
            return {
                'success': False,
                'error': str(e),
                'imported': 0,
                'skipped': 0,
                'errors': 0
            }
    
    def preview_import(self, file_path):
        """
        Предварительный просмотр импорта без сохранения в БД.
        
        Returns:
            dict: Информация о задачах для импорта
        """
        try:
            tasks_data = self._parse_import_file(file_path)
            if not tasks_data:
                return None
            
            preview_data = {
                'total_tasks': len(tasks_data),
                'valid_tasks': 0,
                'invalid_tasks': 0,
                'tasks_preview': [],
                'errors': []
            }
            
            # Анализируем первые 10 задач
            for i, task_data in enumerate(tasks_data[:10]):
                is_valid, error_msg = self._validate_task_data(task_data)
                
                if is_valid:
                    preview_data['valid_tasks'] += 1
                    preview_data['tasks_preview'].append({
                        'title': task_data.get('title', ''),
                        'description': task_data.get('description', '')[:100] + '...' if len(task_data.get('description', '')) > 100 else task_data.get('description', ''),
                        'status': task_data.get('status', 'new'),
                        'priority': task_data.get('priority', 'medium'),
                        'tags': task_data.get('tags', []),
                        'comments_count': len(task_data.get('comments', []))
                    })
                else:
                    preview_data['invalid_tasks'] += 1
                    preview_data['errors'].append(f"Задача {i+1}: {error_msg}")
            
            # Подсчитываем общую статистику
            for task_data in tasks_data:
                is_valid, _ = self._validate_task_data(task_data)
                if is_valid:
                    preview_data['valid_tasks'] += 1
                else:
                    preview_data['invalid_tasks'] += 1
            
            return preview_data
            
        except Exception as e:
            logger.error(f"Ошибка предварительного просмотра: {e}", "IMPORT")
            return None
