#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер напоминаний для ToDoLite.
Проверяет задачи с установленными датами и отправляет уведомления.
"""

import sqlite3
import threading
import time
from datetime import datetime, timedelta
from logger import logger
from notifications_windows import notify

class ReminderManager:
    """
    Менеджер напоминаний для задач с установленными датами.
    """
    
    def __init__(self, db_path='tasks.db'):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.check_interval = 60  # Проверка каждую минуту
        self.reminder_times = [15, 30, 60, 1440]  # За 15 мин, 30 мин, 1 час, 1 день до дедлайна
        
        logger.info("ReminderManager инициализирован", "REMINDER")
    
    def get_tasks_with_reminders(self):
        """
        Получает задачи, для которых нужно отправить напоминания.
        Возвращает список задач с информацией о времени до дедлайна.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Получаем задачи с установленными датами или напоминаниями, которые не выполнены и не архивированы
        c.execute("""
            SELECT id, title, short_description, due_date, scheduled_date, reminder_time, status, priority
            FROM tasks 
            WHERE (due_date IS NOT NULL OR scheduled_date IS NOT NULL OR reminder_time IS NOT NULL)
            AND status NOT IN ('done', 'cancelled')
            AND (archived IS NULL OR archived = 0)
        """)
        
        tasks = c.fetchall()
        conn.close()
        
        reminder_tasks = []
        now = datetime.now()
        
        for task in tasks:
            task_id, title, short_desc, due_date, scheduled_date, reminder_time, status, priority = task
            
            # Определяем дату для напоминания (приоритет: reminder_time > due_date > scheduled_date)
            target_datetime = None
            target_date = None
            reminder_type = None
            
            if reminder_time:
                # Используем точное время напоминания
                try:
                    # Пробуем разные форматы времени
                    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
                        try:
                            target_datetime = datetime.strptime(reminder_time, fmt)
                            target_date = reminder_time
                            reminder_type = 'reminder'
                            break
                        except ValueError:
                            continue
                    else:
                        logger.warning(f"Неверный формат времени напоминания для задачи {task_id}: {reminder_time}", "REMINDER")
                        continue
                except Exception as e:
                    logger.warning(f"Ошибка парсинга времени напоминания для задачи {task_id}: {e}", "REMINDER")
                    continue
            elif due_date:
                # Используем дату дедлайна
                try:
                    target_datetime = datetime.strptime(due_date, '%Y-%m-%d')
                    target_date = due_date
                    reminder_type = 'due'
                except ValueError:
                    logger.warning(f"Неверный формат даты дедлайна для задачи {task_id}: {due_date}", "REMINDER")
                    continue
            elif scheduled_date:
                # Используем дату взятия в работу
                try:
                    target_datetime = datetime.strptime(scheduled_date, '%Y-%m-%d')
                    target_date = scheduled_date
                    reminder_type = 'scheduled'
                except ValueError:
                    logger.warning(f"Неверный формат даты взятия в работу для задачи {task_id}: {scheduled_date}", "REMINDER")
                    continue
            
            if target_datetime:
                # Вычисляем разность во времени
                time_diff = target_datetime - now
                minutes_until = int(time_diff.total_seconds() / 60)
                
                # Для точного времени напоминания отправляем за 5 минут до
                if reminder_type == 'reminder':
                    if -5 <= minutes_until <= 0:  # В течение 5 минут после времени напоминания
                        if not self._was_reminder_sent(task_id, 5):
                            reminder_tasks.append({
                                'task_id': task_id,
                                'title': title,
                                'short_description': short_desc,
                                'target_date': target_date,
                                'minutes_until': minutes_until,
                                'reminder_minutes': 5,
                                'status': status,
                                'priority': priority,
                                'reminder_type': reminder_type
                            })
                else:
                    # Для дат дедлайна/взятия в работу используем стандартные интервалы
                    for reminder_minutes in self.reminder_times:
                        if 0 <= minutes_until <= reminder_minutes:
                            if not self._was_reminder_sent(task_id, reminder_minutes):
                                reminder_tasks.append({
                                    'task_id': task_id,
                                    'title': title,
                                    'short_description': short_desc,
                                    'target_date': target_date,
                                    'minutes_until': minutes_until,
                                    'reminder_minutes': reminder_minutes,
                                    'status': status,
                                    'priority': priority,
                                    'reminder_type': reminder_type
                                })
                                break  # Отправляем только одно напоминание за раз
        
        return reminder_tasks
    
    def _was_reminder_sent(self, task_id, reminder_minutes):
        """
        Проверяет, было ли уже отправлено напоминание для задачи.
        Использует поле updated_at для отслеживания последнего напоминания.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Получаем время последнего обновления задачи
        c.execute("SELECT updated_at FROM tasks WHERE id = ?", (task_id,))
        result = c.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return False
        
        try:
            last_updated = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            
            # Если задача обновлялась в последние 2 минуты, считаем что напоминание уже отправлено
            if (now - last_updated).total_seconds() < 120:
                return True
                
        except ValueError as e:
            logger.debug(f"Ошибка парсинга даты в напоминании: {e}", "REMINDER")
        
        return False
    
    def send_reminder(self, task_info):
        """
        Отправляет напоминание о задаче.
        """
        task_id = task_info['task_id']
        title = task_info['title']
        minutes_until = task_info['minutes_until']
        reminder_minutes = task_info['reminder_minutes']
        target_date = task_info['target_date']
        reminder_type = task_info.get('reminder_type', 'due')
        
        # Формируем текст напоминания в зависимости от типа
        if reminder_type == 'reminder':
            # Точное время напоминания
            if minutes_until <= 0:
                reminder_title = "⏰ ToDoLite: Время напоминания"
                reminder_text = f"📋 Задача '{title}' - время напоминания наступило!"
            else:
                reminder_title = "⏰ ToDoLite: Скоро напоминание"
                reminder_text = f"📋 Задача '{title}' - напоминание через {minutes_until} мин."
        else:
            # Дедлайн или дата взятия в работу
            if minutes_until <= 0:
                # Дедлайн уже прошел
                if reminder_type == 'due':
                    reminder_title = "⏰ ToDoLite: Дедлайн прошел"
                    reminder_text = f"📋 Задача '{title}' должна была быть выполнена {target_date}"
                else:
                    reminder_title = "⏰ ToDoLite: Время взятия в работу"
                    reminder_text = f"📋 Задача '{title}' - время взятия в работу: {target_date}"
            elif minutes_until <= 60:
                # Менее часа
                reminder_title = "⏰ ToDoLite: Скоро дедлайн"
                reminder_text = f"📋 Задача '{title}' - осталось {minutes_until} мин. (до {target_date})"
            elif minutes_until <= 1440:
                # Менее дня
                hours = minutes_until // 60
                reminder_title = "⏰ ToDoLite: Напоминание"
                reminder_text = f"📋 Задача '{title}' - осталось {hours} ч. (до {target_date})"
            else:
                # Более дня
                days = minutes_until // 1440
                reminder_title = "⏰ ToDoLite: Напоминание"
                reminder_text = f"📋 Задача '{title}' - осталось {days} дн. (до {target_date})"
        
        # Отправляем уведомление
        try:
            notify(reminder_title, reminder_text)
            logger.info(f"Напоминание отправлено для задачи {task_id}: '{title}' (тип: {reminder_type})", "REMINDER")
            
            # Обновляем время последнего обновления задачи, чтобы не дублировать напоминания
            self._mark_reminder_sent(task_id)
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания для задачи {task_id}: {e}", "REMINDER")
    
    def _mark_reminder_sent(self, task_id):
        """
        Отмечает, что напоминание было отправлено (обновляет updated_at).
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
    
    def check_reminders(self):
        """
        Проверяет и отправляет напоминания для всех подходящих задач.
        """
        try:
            reminder_tasks = self.get_tasks_with_reminders()
            
            if reminder_tasks:
                logger.info(f"Найдено {len(reminder_tasks)} задач для напоминания", "REMINDER")
                
                for task_info in reminder_tasks:
                    self.send_reminder(task_info)
            else:
                logger.debug("Задач для напоминания не найдено", "REMINDER")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}", "REMINDER")
    
    def _run_scheduler(self):
        """
        Основной цикл планировщика напоминаний.
        """
        while self.running:
            try:
                self.check_reminders()
                
                # Ждем до следующей проверки
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Ошибка в планировщике напоминаний: {e}", "REMINDER")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def start(self):
        """
        Запускает планировщик напоминаний в отдельном потоке.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("Планировщик напоминаний запущен", "REMINDER")
        else:
            logger.warning("Планировщик напоминаний уже запущен", "REMINDER")
    
    def stop(self):
        """
        Останавливает планировщик напоминаний.
        """
        if self.running:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
                if self.thread.is_alive():
                    logger.warning("Поток планировщика напоминаний не завершился корректно", "REMINDER")
            logger.info("Планировщик напоминаний остановлен", "REMINDER")
        else:
            logger.warning("Планировщик напоминаний не запущен", "REMINDER")
    
    def force_check(self):
        """
        Принудительно проверяет напоминания.
        """
        logger.info("Принудительная проверка напоминаний", "REMINDER")
        self.check_reminders()
    
    def get_status(self):
        """
        Возвращает текущий статус планировщика напоминаний.
        """
        return {
            'running': self.running,
            'check_interval': self.check_interval,
            'reminder_times': self.reminder_times
        }

# Глобальный экземпляр менеджера напоминаний
_reminder_manager = None

def get_reminder_manager():
    """Получение глобального экземпляра менеджера напоминаний."""
    global _reminder_manager
    if _reminder_manager is None:
        _reminder_manager = ReminderManager()
    return _reminder_manager

def start_reminder_scheduler():
    """Запускает глобальный планировщик напоминаний."""
    manager = get_reminder_manager()
    manager.start()

def stop_reminder_scheduler():
    """Останавливает глобальный планировщик напоминаний."""
    manager = get_reminder_manager()
    manager.stop()
