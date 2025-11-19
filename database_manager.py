#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Унифицированный менеджер базы данных
"""

import sqlite3
import threading
import os
from contextlib import contextmanager
from logger import logger

class DatabaseManager:
    """
    Унифицированный менеджер для работы с базой данных SQLite
    """
    
    def __init__(self, db_path='tasks.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        # Thread-local storage для переиспользования соединений в рамках одного потока
        self._local = threading.local()
        self._ensure_database_exists()
        logger.info("DatabaseManager инициализирован", "DATABASE")
    
    def _ensure_database_exists(self):
        """Проверяет существование базы данных и создает если нужно"""
        if not os.path.exists(self.db_path):
            logger.info("База данных не найдена, создаем новую", "DATABASE")
            self._create_database()
    
    def _create_database(self):
        """Создает новую базу данных с таблицами"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Создаем таблицу задач
            c.execute('''CREATE TABLE tasks
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         title TEXT NOT NULL,
                         short_description TEXT,
                         full_description TEXT,
                         status TEXT DEFAULT 'new',
                         priority TEXT DEFAULT 'medium',
                         eisenhower_priority TEXT DEFAULT 'not_urgent_not_important',
                         assigned_to TEXT,
                         related_threads TEXT,
                         scheduled_date DATE,
                         due_date DATE,
                         reminder_time DATETIME,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         completed_at TIMESTAMP,
                         tags TEXT,
                         archived BOOLEAN DEFAULT 0,
                         archived_at TIMESTAMP,
                         archived_from_status TEXT)''')
            
            # Создаем таблицу комментариев
            c.execute('''CREATE TABLE comments
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         task_id INTEGER,
                         comment TEXT NOT NULL,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (task_id) REFERENCES tasks (id))''')
            
            conn.commit()
            logger.success("База данных создана успешно", "DATABASE")
            
        except Exception as e:
            logger.error(f"Ошибка создания базы данных: {e}", "DATABASE")
            raise
        finally:
            conn.close()
    
    def get_connection(self, reuse=True):
        """
        Получает соединение с базой данных
        
        Args:
            reuse: Если True, пытается переиспользовать соединение из thread-local storage
        """
        if reuse:
            # Пытаемся переиспользовать соединение из текущего потока
            if hasattr(self._local, 'connection'):
                conn = self._local.connection
                # Проверяем, что соединение еще валидно
                try:
                    conn.execute("SELECT 1")
                    return conn
                except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                    # Соединение закрыто, создаем новое
                    pass
        
        # Создаем новое соединение
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        if reuse:
            self._local.connection = conn
        return conn
    
    @contextmanager
    def get_connection_context(self):
        """
        Контекстный менеджер для получения соединения
        Автоматически закрывает соединение при выходе из контекста
        """
        conn = self.get_connection(reuse=False)
        try:
            yield conn
        finally:
            conn.close()
    
    def _check_column_exists(self, table_name, column_name):
        """
        Проверяет наличие колонки в таблице
        
        Args:
            table_name: Имя таблицы
            column_name: Имя колонки
            
        Returns:
            True если колонка существует, False иначе
        """
        try:
            conn = self.get_connection(reuse=True)
            c = conn.cursor()
            c.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in c.fetchall()]
            return column_name in columns
        except Exception:
            return False
    
    def execute_query(self, query, params=None, fetch=False, fetchone=False):
        """
        Выполняет SQL запрос с параметрами
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch: Возвращать все результаты
            fetchone: Возвращать один результат
        
        Returns:
            Результат запроса или None при ошибке
        """
        with self.lock:
            conn = self.get_connection()
            try:
                c = conn.cursor()
                c.execute(query, params or ())
                
                if fetch:
                    result = c.fetchall()
                elif fetchone:
                    result = c.fetchone()
                else:
                    result = c.lastrowid
                
                conn.commit()
                return result
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения запроса: {e}", "DATABASE")
                logger.error(f"Запрос: {query}", "DATABASE")
                logger.error(f"Параметры: {params}", "DATABASE")
                raise
            finally:
                conn.close()
    
    def execute_many(self, query, params_list):
        """
        Выполняет запрос с множественными параметрами
        
        Args:
            query: SQL запрос
            params_list: Список параметров
        
        Returns:
            Количество обработанных строк
        """
        with self.lock:
            conn = self.get_connection()
            try:
                c = conn.cursor()
                c.executemany(query, params_list)
                conn.commit()
                return c.rowcount
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения множественного запроса: {e}", "DATABASE")
                raise
            finally:
                conn.close()
    
    def get_tasks(self, **filters):
        """
        Получает задачи с фильтрами
        
        Args:
            **filters: Фильтры для поиска задач
        
        Returns:
            Список задач
        """
        query = "SELECT * FROM tasks WHERE "
        conditions = []
        params = []
        
        for key, value in filters.items():
            if value is not None:
                if key == 'status' and isinstance(value, list):
                    # Для статусов поддерживаем список
                    placeholders = ','.join(['?' for _ in value])
                    conditions.append(f"{key} IN ({placeholders})")
                    params.extend(value)
                else:
                    conditions.append(f"{key} = ?")
                    params.append(value)
        
        if conditions:
            query += " AND ".join(conditions)
        else:
            query = "SELECT * FROM tasks"
        
        query += " ORDER BY created_at DESC"
        
        return self.execute_query(query, params, fetch=True)
    
    def get_task_by_id(self, task_id):
        """Получает задачу по ID"""
        return self.execute_query(
            "SELECT * FROM tasks WHERE id = ?", 
            (task_id,), 
            fetchone=True
        )
    
    def add_task(self, **task_data):
        """
        Добавляет новую задачу
        
        Args:
            **task_data: Данные задачи
        
        Returns:
            ID созданной задачи
        """
        # Подготавливаем поля и значения
        fields = list(task_data.keys())
        values = list(task_data.values())
        placeholders = ','.join(['?' for _ in fields])
        
        query = f"INSERT INTO tasks ({','.join(fields)}) VALUES ({placeholders})"
        
        return self.execute_query(query, values)
    
    def update_task(self, task_id, **task_data):
        """
        Обновляет задачу
        
        Args:
            task_id: ID задачи
            **task_data: Данные для обновления
        
        Returns:
            Количество обновленных строк
        """
        if not task_data:
            return 0
        
        # Добавляем updated_at
        task_data['updated_at'] = 'CURRENT_TIMESTAMP'
        
        fields = list(task_data.keys())
        values = list(task_data.values())
        set_clause = ','.join([f"{field} = ?" for field in fields])
        
        query = f"UPDATE tasks SET {set_clause} WHERE id = ?"
        values.append(task_id)
        
        return self.execute_query(query, values)
    
    def delete_task(self, task_id):
        """Удаляет задачу"""
        return self.execute_query("DELETE FROM tasks WHERE id = ?", (task_id,))
    
    def get_comments(self, task_id):
        """Получает комментарии к задаче"""
        return self.execute_query(
            "SELECT * FROM comments WHERE task_id = ? ORDER BY created_at DESC",
            (task_id,),
            fetch=True
        )
    
    def add_comment(self, task_id, comment):
        """Добавляет комментарий к задаче"""
        return self.execute_query(
            "INSERT INTO comments (task_id, comment) VALUES (?, ?)",
            (task_id, comment)
        )
    
    def backup_database(self, backup_path):
        """
        Создает резервную копию базы данных
        
        Args:
            backup_path: Путь для сохранения резервной копии
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            logger.success(f"Резервная копия создана: {backup_path}", "DATABASE")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания резервной копии: {e}", "DATABASE")
            return False
    
    def restore_database(self, backup_path):
        """
        Восстанавливает базу данных из резервной копии
        
        Args:
            backup_path: Путь к резервной копии
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            import shutil
            shutil.copy2(backup_path, self.db_path)
            logger.success(f"База данных восстановлена из: {backup_path}", "DATABASE")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления базы данных: {e}", "DATABASE")
            return False
    
    def get_tasks_base_query(self, mode='kanban', include_comments=False):
        """
        Генерирует базовый SQL запрос для получения задач по режиму
        Совместим со старыми БД, где могут отсутствовать некоторые колонки
        
        Args:
            mode: Режим отображения ('kanban', 'eisenhower', или другой)
            include_comments: Включать ли комментарии через JOIN
            
        Returns:
            SQL запрос (строка)
        """
        # Проверяем наличие колонок для обратной совместимости
        has_short_desc = self._check_column_exists('tasks', 'short_description')
        has_full_desc = self._check_column_exists('tasks', 'full_description')
        has_eisenhower = self._check_column_exists('tasks', 'eisenhower_priority')
        has_assigned = self._check_column_exists('tasks', 'assigned_to')
        has_threads = self._check_column_exists('tasks', 'related_threads')
        has_scheduled = self._check_column_exists('tasks', 'scheduled_date')
        has_due = self._check_column_exists('tasks', 'due_date')
        has_completed = self._check_column_exists('tasks', 'completed_at')
        has_tags = self._check_column_exists('tasks', 'tags')
        
        # Базовые поля для выборки (только существующие колонки)
        if include_comments:
            select_fields = ["t.id", "t.title"]
            if has_short_desc:
                select_fields.append("t.short_description")
            else:
                select_fields.append("'' as short_description")
            if has_full_desc:
                select_fields.append("t.full_description")
            else:
                select_fields.append("'' as full_description")
            select_fields.append("t.status")
            select_fields.append("t.priority")
            if has_eisenhower:
                select_fields.append("t.eisenhower_priority")
            else:
                select_fields.append("'not_urgent_not_important' as eisenhower_priority")
            if has_assigned:
                select_fields.append("t.assigned_to")
            else:
                select_fields.append("'' as assigned_to")
            if has_threads:
                select_fields.append("t.related_threads")
            else:
                select_fields.append("'' as related_threads")
            if has_scheduled:
                select_fields.append("t.scheduled_date")
            else:
                select_fields.append("NULL as scheduled_date")
            if has_due:
                select_fields.append("t.due_date")
            else:
                select_fields.append("NULL as due_date")
            select_fields.append("t.created_at")
            select_fields.append("t.updated_at")
            if has_completed:
                select_fields.append("t.completed_at")
            else:
                select_fields.append("NULL as completed_at")
            if has_tags:
                select_fields.append("t.tags")
            else:
                select_fields.append("'' as tags")
            select_fields.append("GROUP_CONCAT(tc.comment, ' ') as comments")
            
            from_clause = "FROM tasks t LEFT JOIN task_comments tc ON t.id = tc.task_id"
            group_by = "GROUP BY t.id"
        else:
            select_fields = ["id", "title"]
            if has_short_desc:
                select_fields.append("short_description")
            else:
                select_fields.append("'' as short_description")
            if has_full_desc:
                select_fields.append("full_description")
            else:
                select_fields.append("'' as full_description")
            select_fields.append("status")
            select_fields.append("priority")
            if has_eisenhower:
                select_fields.append("eisenhower_priority")
            else:
                select_fields.append("'not_urgent_not_important' as eisenhower_priority")
            if has_assigned:
                select_fields.append("assigned_to")
            else:
                select_fields.append("'' as assigned_to")
            if has_threads:
                select_fields.append("related_threads")
            else:
                select_fields.append("'' as related_threads")
            if has_scheduled:
                select_fields.append("scheduled_date")
            else:
                select_fields.append("NULL as scheduled_date")
            if has_due:
                select_fields.append("due_date")
            else:
                select_fields.append("NULL as due_date")
            select_fields.append("created_at")
            select_fields.append("updated_at")
            if has_completed:
                select_fields.append("completed_at")
            else:
                select_fields.append("NULL as completed_at")
            if has_tags:
                select_fields.append("tags")
            else:
                select_fields.append("'' as tags")
            
            from_clause = "FROM tasks"
            group_by = ""
        
        # WHERE условие для активных задач
        # Проверяем наличие колонки archived для обратной совместимости
        # Используем кэшированную информацию о структуре БД
        has_archived = self._check_column_exists('tasks', 'archived')
        if has_archived:
            where_clause = "WHERE (archived = 0 OR archived IS NULL)"
            if include_comments:
                where_clause = "WHERE (t.archived = 0 OR t.archived IS NULL)"
        else:
            # Колонка отсутствует - не фильтруем по archived
            where_clause = ""
            if include_comments:
                where_clause = ""
        
        # ORDER BY в зависимости от режима
        if mode == 'eisenhower' or mode == 'kanban':
            order_by = """
                ORDER BY 
                    CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                    COALESCE(due_date, '') ASC
            """
            if include_comments:
                order_by = """
                    ORDER BY 
                        CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                        COALESCE(t.due_date, '') ASC
                """
        else:
            order_by = "ORDER BY created_at DESC"
            if include_comments:
                order_by = "ORDER BY t.created_at DESC"
        
        # Собираем запрос
        select_str = ", ".join(select_fields)
        query_parts = [f"SELECT {select_str}", from_clause]
        if where_clause:
            query_parts.append(where_clause)
        if group_by:
            query_parts.append(group_by)
        query_parts.append(order_by)
        
        query = " ".join(query_parts)
        return query
    
    def get_database_info(self):
        """Получает информацию о базе данных"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # Количество задач
            c.execute("SELECT COUNT(*) FROM tasks")
            task_count = c.fetchone()[0]
            
            # Количество комментариев
            c.execute("SELECT COUNT(*) FROM comments")
            comment_count = c.fetchone()[0]
            
            # Размер файла
            file_size = os.path.getsize(self.db_path)
            
            conn.close()
            
            return {
                'task_count': task_count,
                'comment_count': comment_count,
                'file_size': file_size,
                'file_path': self.db_path
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о БД: {e}", "DATABASE")
            return None

# Глобальный экземпляр менеджера БД
_db_manager = None

def get_db_manager():
    """Получает глобальный экземпляр менеджера БД"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
