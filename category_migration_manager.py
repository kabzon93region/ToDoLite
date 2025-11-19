#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Менеджер автоматического перемещения задач по категориям на основе дат
"""

import sqlite3
import threading
from datetime import datetime, timedelta, date
from typing import Optional, Tuple
from logger import logger
from config_manager import get_config_manager


class CategoryMigrationManager:
    """
    Менеджер автоматического перемещения задач между категориями
    на основе дат выполнения/отложенности
    """
    
    def __init__(self, db_path='tasks.db', config_manager=None):
        """
        Инициализация менеджера миграции категорий
        
        Args:
            db_path: Путь к базе данных
            config_manager: Менеджер конфигурации (опционально)
        """
        self.db_path = db_path
        self.config_manager = config_manager or get_config_manager()
        self.scheduler_thread = None
        self.scheduler_running = False
        self.scheduler_lock = threading.Lock()
        
        # Получаем настройки из конфигурации
        config = self.config_manager.get_config()
        auto_migration_config = config.get('auto_migration', {})
        self.enabled = auto_migration_config.get('enabled', True)
        self.interval_minutes = auto_migration_config.get('interval_minutes', 30)
        
        logger.info("CategoryMigrationManager инициализирован", "MIGRATION")
    
    def _parse_date(self, date_value) -> Optional[date]:
        """
        Парсит дату из различных форматов
        
        Args:
            date_value: Дата в виде строки, date объекта или None
            
        Returns:
            Объект date или None
        """
        if date_value is None:
            return None
        
        # Проверяем datetime ПЕРЕД date, т.к. datetime наследуется от date
        if isinstance(date_value, datetime):
            return date_value.date()
        
        if isinstance(date_value, date):
            return date_value
        
        if isinstance(date_value, str):
            # Пропускаем пустые строки
            if not date_value.strip():
                return None
            try:
                # Пробуем разные форматы
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d.%m.%Y', '%d/%m/%Y']:
                    try:
                        return datetime.strptime(date_value.strip(), fmt).date()
                    except ValueError:
                        continue
                logger.warning(f"Не удалось распарсить дату: {date_value}", "MIGRATION")
                return None
            except Exception as e:
                logger.error(f"Ошибка парсинга даты {date_value}: {e}", "MIGRATION")
                return None
        
        return None
    
    def is_overdue(self, date_value) -> bool:
        """
        Проверяет, просрочена ли задача
        
        Args:
            date_value: Дата для проверки
            
        Returns:
            True если дата просрочена, False иначе
        """
        target_date = self._parse_date(date_value)
        if target_date is None:
            return False
        
        today = datetime.now().date()
        return target_date < today
    
    def get_tuesday_next_week(self) -> date:
        """
        Вычисляет дату вторника следующей недели
        
        Returns:
            Дата вторника следующей недели
        """
        today = datetime.now().date()
        # Получаем начало текущей недели (понедельник)
        days_since_monday = today.weekday()  # 0 = понедельник
        week_start = today - timedelta(days=days_since_monday)
        # Конец текущей недели (воскресенье)
        week_end = week_start + timedelta(days=6)
        # Понедельник следующей недели
        next_week_start = week_end + timedelta(days=1)
        # Вторник следующей недели
        next_tuesday = next_week_start + timedelta(days=1)
        return next_tuesday
    
    def is_in_current_week(self, date_value) -> bool:
        """
        Проверяет, находится ли дата в текущей неделе
        Если сегодня пятница, то включает также ближайший понедельник
        
        Args:
            date_value: Дата для проверки
            
        Returns:
            True если дата в текущей неделе (или следующий понедельник если сегодня пятница)
        """
        target_date = self._parse_date(date_value)
        if target_date is None:
            return False
        
        today = datetime.now().date()
        
        # Получаем начало недели (понедельник)
        days_since_monday = today.weekday()  # 0 = понедельник
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)  # Воскресенье
        
        # Если сегодня пятница, включаем следующий понедельник
        if today.weekday() == 4:  # Пятница
            next_monday = week_end + timedelta(days=1)
            return week_start <= target_date <= next_monday
        else:
            return week_start <= target_date <= week_end
    
    def get_category_by_date(self, due_date, scheduled_date) -> Optional[str]:
        """
        Определяет категорию задачи на основе дат
        
        Args:
            due_date: Дата выполнения/дедлайн
            scheduled_date: Дата отложенности/планирования
            
        Returns:
            Код категории ('working', 'later', 'waiting', 'think') или None
        """
        # Определяем используемую дату (приоритет due_date)
        target_date = self._parse_date(due_date) if due_date else self._parse_date(scheduled_date)
        
        if target_date is None:
            return None  # Нет даты - не перемещать
        
        today = datetime.now().date()
        
        # Проверяем просроченность
        if target_date < today:
            return 'working'  # Просроченные → Сегодня
        
        # Сегодня
        if target_date == today:
            return 'working'
        
        # Завтра
        tomorrow = today + timedelta(days=1)
        if target_date == tomorrow:
            return 'later'
        
        # На неделе
        if self.is_in_current_week(target_date):
            return 'waiting'
        
        # Далекие (дальше чем вторник следующей недели)
        next_tuesday = self.get_tuesday_next_week()
        if target_date > next_tuesday:
            return 'think'
        
        # Между завтра и вторником следующей недели - тоже "На неделе"
        if tomorrow < target_date <= next_tuesday:
            return 'waiting'
        
        return None
    
    def should_migrate_task(self, task_status: str, is_overdue: bool, target_category: Optional[str] = None) -> bool:
        """
        Проверяет, можно ли перемещать задачу из текущей категории
        
        Args:
            task_status: Текущий статус задачи
            is_overdue: Просрочена ли задача
            target_category: Целевая категория (опционально, для специальных правил)
            
        Returns:
            True если можно перемещать, False иначе
        """
        # "tracking" и "working" (не просроченные) - НЕ перемещать
        if task_status in ['tracking', 'working']:
            # Просроченные задачи можно перемещать даже из "tracking" и "working"
            if is_overdue:
                return True
            return False
        
        # Из "new" можно перемещать ТОЛЬКО в "later" (Завтра) или "working" (Сегодня)
        if task_status == 'new':
            if target_category is not None:
                return target_category in ['later', 'working']
            # Если целевая категория не указана, разрешаем (будет проверено позже)
            return True
        
        # Из остальных категорий ("think", "waiting", "later") можно перемещать
        migratable_statuses = ['think', 'waiting', 'later']
        if task_status in migratable_statuses:
            return True
        
        return False
    
    def migrate_tasks(self) -> Tuple[int, int]:
        """
        Выполняет миграцию всех задач, которые нужно переместить
        
        Returns:
            Кортеж (количество проверенных задач, количество перемещённых задач)
        """
        if not self.enabled:
            logger.debug("Автоматическая миграция отключена", "MIGRATION")
            return (0, 0)
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Получаем все активные задачи с датами
            c.execute("""
                SELECT id, status, due_date, scheduled_date
                FROM tasks
                WHERE (archived IS NULL OR archived = 0)
                AND (due_date IS NOT NULL OR scheduled_date IS NOT NULL)
                AND status NOT IN ('done', 'cancelled')
            """)
            
            tasks = c.fetchall()
            checked_count = len(tasks)
            migrated_count = 0
            
            for task_id, current_status, due_date, scheduled_date in tasks:
                try:
                    # Определяем целевую категорию
                    target_category = self.get_category_by_date(due_date, scheduled_date)
                    
                    if target_category is None:
                        continue  # Нет даты или не нужно перемещать
                    
                    # Проверяем просроченность
                    target_date = self._parse_date(due_date) if due_date else self._parse_date(scheduled_date)
                    is_overdue = target_date < datetime.now().date() if target_date else False
                    
                    # Проверяем, можно ли перемещать (передаём целевую категорию для проверки правил)
                    if not self.should_migrate_task(current_status, is_overdue, target_category):
                        continue
                    
                    # Если категория не изменилась, пропускаем
                    if current_status == target_category:
                        continue
                    
                    # Дополнительная проверка: из "new" можно перемещать ТОЛЬКО в "later" или "working"
                    if current_status == 'new' and target_category not in ['later', 'working']:
                        continue
                    
                    # Выполняем перемещение
                    c.execute("""
                        UPDATE tasks
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (target_category, task_id))
                    
                    migrated_count += 1
                    logger.info(
                        f"Задача #{task_id} перемещена из '{current_status}' в '{target_category}'",
                        "MIGRATION"
                    )
                    
                except Exception as e:
                    logger.error(f"Ошибка при миграции задачи #{task_id}: {e}", "MIGRATION")
                    continue
            
            conn.commit()
            conn.close()
            
            if migrated_count > 0:
                logger.success(f"Миграция завершена: проверено {checked_count}, перемещено {migrated_count}", "MIGRATION")
            else:
                logger.debug(f"Миграция завершена: проверено {checked_count}, перемещений не требуется", "MIGRATION")
            
            return (checked_count, migrated_count)
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении миграции: {e}", "MIGRATION")
            return (0, 0)
    
    def _scheduler_loop(self):
        """Основной цикл планировщика"""
        logger.info(f"Планировщик миграции запущен (интервал: {self.interval_minutes} мин)", "MIGRATION")
        
        while self.scheduler_running:
            try:
                # Выполняем миграцию
                self.migrate_tasks()
                
                # Ждём указанный интервал
                import time
                sleep_seconds = int(self.interval_minutes * 60)
                for _ in range(sleep_seconds):
                    if not self.scheduler_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Ошибка в планировщике миграции: {e}", "MIGRATION")
                import time
                time.sleep(60)  # Ждём минуту перед повтором при ошибке
    
    def start_scheduler(self, interval_minutes: Optional[int] = None):
        """
        Запускает периодическую проверку
        
        Args:
            interval_minutes: Интервал проверки в минутах (если None, используется из конфига)
        """
        if interval_minutes is not None:
            self.interval_minutes = interval_minutes
        
        if not self.enabled:
            logger.info("Автоматическая миграция отключена в конфигурации", "MIGRATION")
            return
        
        with self.scheduler_lock:
            if self.scheduler_running:
                logger.warning("Планировщик миграции уже запущен", "MIGRATION")
                return
            
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            logger.success("Планировщик миграции запущен", "MIGRATION")
    
    def stop_scheduler(self):
        """Останавливает планировщик"""
        with self.scheduler_lock:
            if not self.scheduler_running:
                return
            
            self.scheduler_running = False
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=5)
            
            logger.info("Планировщик миграции остановлен", "MIGRATION")
    
    def migrate_tasks_async(self, callback=None):
        """
        Запускает миграцию задач в отдельном потоке
        
        Args:
            callback: Функция обратного вызова с результатом (checked_count, migrated_count)
        """
        def run_migration():
            try:
                result = self.migrate_tasks()
                if callback:
                    callback(result)
            except Exception as e:
                logger.error(f"Ошибка при асинхронной миграции: {e}", "MIGRATION")
                if callback:
                    callback((0, 0))
        
        thread = threading.Thread(target=run_migration, daemon=True)
        thread.start()
        return thread


# Глобальный экземпляр
_migration_manager = None

def get_migration_manager(db_path='tasks.db', config_manager=None):
    """Получение глобального экземпляра менеджера миграции"""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = CategoryMigrationManager(db_path, config_manager)
    return _migration_manager

