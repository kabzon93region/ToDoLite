#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Менеджер экспорта задач
"""

import sqlite3
import json
import csv
import xml.etree.ElementTree as ET
from datetime import datetime
import os
from logger import logger

class ExportManager:
    """
    Управляет экспортом задач в различных форматах.
    """
    
    def __init__(self, db_path='tasks.db'):
        self.db_path = db_path
        logger.info("ExportManager инициализирован", "EXPORT")
    
    def get_all_tasks(self):
        """Получает все задачи из базы данных."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT t.*, 
                       GROUP_CONCAT(tc.comment, '|||') as comments
                FROM tasks t
                LEFT JOIN task_comments tc ON t.id = tc.task_id
                GROUP BY t.id
                ORDER BY t.created_at DESC
            """)
            
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                # Обрабатываем комментарии
                if task.get('comments'):
                    task['comments'] = task['comments'].split('|||')
                else:
                    task['comments'] = []
                
                # Обрабатываем теги
                if task.get('tags'):
                    task['tags'] = [tag.strip() for tag in task['tags'].split(',') if tag.strip()]
                else:
                    task['tags'] = []
                
                tasks.append(task)
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка получения задач для экспорта: {e}", "EXPORT")
            return []
    
    def get_tasks_by_ids(self, task_ids):
        """Получает задачи по списку ID."""
        if not task_ids:
            return []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            placeholders = ','.join('?' * len(task_ids))
            cursor.execute(f"""
                SELECT t.*, 
                       GROUP_CONCAT(tc.comment, '|||') as comments
                FROM tasks t
                LEFT JOIN task_comments tc ON t.id = tc.task_id
                WHERE t.id IN ({placeholders})
                GROUP BY t.id
                ORDER BY t.created_at DESC
            """, task_ids)
            
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                # Обрабатываем комментарии
                if task.get('comments'):
                    task['comments'] = task['comments'].split('|||')
                else:
                    task['comments'] = []
                
                # Обрабатываем теги
                if task.get('tags'):
                    task['tags'] = [tag.strip() for tag in task['tags'].split(',') if tag.strip()]
                else:
                    task['tags'] = []
                
                tasks.append(task)
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Ошибка получения задач по ID для экспорта: {e}", "EXPORT")
            return []
    
    def export_to_json(self, tasks, output_path=None):
        """Экспортирует задачи в JSON формат."""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"todolite_export_{timestamp}.json"
            
            # Подготавливаем данные для экспорта
            export_data = {
                'export_info': {
                    'export_date': datetime.now().isoformat(),
                    'total_tasks': len(tasks),
                    'version': '1.0'
                },
                'tasks': tasks
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.success(f"Экспорт в JSON завершен: {output_path}", "EXPORT")
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}", "EXPORT")
            return None
    
    def export_to_csv(self, tasks, output_path=None):
        """Экспортирует задачи в CSV формат."""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"todolite_export_{timestamp}.csv"
            
            if not tasks:
                logger.warning("Нет задач для экспорта в CSV", "EXPORT")
                return None
            
            # Определяем все возможные поля
            all_fields = set()
            for task in tasks:
                all_fields.update(task.keys())
            
            # Убираем поля, которые не нужно экспортировать
            exclude_fields = {'id', 'created_at', 'updated_at'}
            export_fields = [field for field in sorted(all_fields) if field not in exclude_fields]
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=export_fields)
                writer.writeheader()
                
                for task in tasks:
                    # Подготавливаем строку для записи
                    row = {}
                    for field in export_fields:
                        value = task.get(field, '')
                        
                        # Обрабатываем специальные поля
                        if field == 'comments' and isinstance(value, list):
                            row[field] = ' | '.join(value)
                        elif field == 'tags' and isinstance(value, list):
                            row[field] = ', '.join(value)
                        elif field in ['due_date', 'reminder_time'] and value:
                            # Форматируем даты
                            try:
                                if isinstance(value, str):
                                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                    row[field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                                else:
                                    row[field] = str(value)
                            except:
                                row[field] = str(value)
                        else:
                            row[field] = str(value) if value is not None else ''
                    
                    writer.writerow(row)
            
            logger.success(f"Экспорт в CSV завершен: {output_path}", "EXPORT")
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в CSV: {e}", "EXPORT")
            return None
    
    def export_to_xml(self, tasks, output_path=None):
        """Экспортирует задачи в XML формат."""
        try:
            if output_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = f"todolite_export_{timestamp}.xml"
            
            # Создаем корневой элемент
            root = ET.Element("todolite_export")
            root.set("export_date", datetime.now().isoformat())
            root.set("total_tasks", str(len(tasks)))
            root.set("version", "1.0")
            
            # Добавляем задачи
            tasks_element = ET.SubElement(root, "tasks")
            
            for task in tasks:
                task_element = ET.SubElement(tasks_element, "task")
                
                # Добавляем основные поля
                for key, value in task.items():
                    if key in ['comments', 'tags']:
                        continue  # Обработаем отдельно
                    
                    if value is not None:
                        field_element = ET.SubElement(task_element, key)
                        field_element.text = str(value)
                
                # Добавляем комментарии
                if task.get('comments'):
                    comments_element = ET.SubElement(task_element, "comments")
                    for comment in task['comments']:
                        comment_element = ET.SubElement(comments_element, "comment")
                        comment_element.text = comment
                
                # Добавляем теги
                if task.get('tags'):
                    tags_element = ET.SubElement(task_element, "tags")
                    for tag in task['tags']:
                        tag_element = ET.SubElement(tags_element, "tag")
                        tag_element.text = tag
            
            # Записываем XML
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)  # Форматируем XML
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            logger.success(f"Экспорт в XML завершен: {output_path}", "EXPORT")
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в XML: {e}", "EXPORT")
            return None
    
    def export_tasks(self, task_ids=None, format='json', output_path=None):
        """
        Экспортирует задачи в указанном формате.
        
        Args:
            task_ids: Список ID задач для экспорта (None = все задачи)
            format: Формат экспорта ('json', 'csv', 'xml')
            output_path: Путь к файлу экспорта (None = автогенерация)
        
        Returns:
            str: Путь к созданному файлу или None при ошибке
        """
        try:
            # Получаем задачи
            if task_ids:
                tasks = self.get_tasks_by_ids(task_ids)
                logger.info(f"Экспорт {len(tasks)} задач по ID", "EXPORT")
            else:
                tasks = self.get_all_tasks()
                logger.info(f"Экспорт всех задач ({len(tasks)} шт.)", "EXPORT")
            
            if not tasks:
                logger.warning("Нет задач для экспорта", "EXPORT")
                return None
            
            # Экспортируем в нужном формате
            if format.lower() == 'json':
                return self.export_to_json(tasks, output_path)
            elif format.lower() == 'csv':
                return self.export_to_csv(tasks, output_path)
            elif format.lower() == 'xml':
                return self.export_to_xml(tasks, output_path)
            else:
                logger.error(f"Неподдерживаемый формат экспорта: {format}", "EXPORT")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка экспорта задач: {e}", "EXPORT")
            return None
