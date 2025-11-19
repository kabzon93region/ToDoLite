#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Планировщик резервного копирования
"""

import threading
import time
from datetime import datetime, timedelta
from backup_manager import BackupManager
from logger import logger
from notifications_windows import notify
import os
import subprocess

class BackupScheduler:
    """
    Планировщик для автоматического создания резервных копий базы данных.
    """
    
    def __init__(self, config_path='config.json', db_path='tasks.db'):
        self.backup_manager = BackupManager(config_path=config_path, db_path=db_path)
        self.config = self.backup_manager.get_backup_info()
        self.interval_hours = self.config.get('interval_hours', 1)
        self.enabled = self.config.get('enabled', True)
        self.running = False
        self.thread = None
        self.next_backup_time = None
        
        logger.info(f"BackupScheduler инициализирован (интервал: {self.interval_hours}ч, включен: {self.enabled})", "BACKUP")
    
    def _run_scheduler(self):
        """Основной цикл планировщика."""
        while self.running:
            self.update_config()  # Проверяем актуальность конфигурации
            
            if not self.enabled:
                logger.info("Резервное копирование отключено в конфигурации, планировщик приостановлен", "BACKUP")
                time.sleep(60)  # Ждем минуту перед следующей проверкой
                continue
            
            if self.next_backup_time is None or datetime.now() >= self.next_backup_time:
                logger.info("Время для создания резервной копии (массово)", "BACKUP")
                results = self.backup_manager.create_backup_all()
                if results and len(results) > 0:
                    logger.success(f"Автоматические резервные копии созданы: {len(results)} шт.", "BACKUP")
                else:
                    logger.error("Не удалось создать автоматические резервные копии ни в одном из направлений", "BACKUP")
                    # Пытаемся нативное уведомление из приложения; fallback внутри notify
                    try:
                        notify(
                            "⚠️ ToDoLite: Резервное копирование",
                            "📦 Не удалось создать резервную копию ни в одном из указанных мест"
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось показать уведомление: {e}", "BACKUP")
                
                self.next_backup_time = datetime.now() + timedelta(hours=self.interval_hours)
                logger.info(f"Следующее резервное копирование запланировано на: {self.next_backup_time}", "BACKUP")
            
            # Конвертируем часы в секунды
            sleep_seconds = self.interval_hours * 3600
            logger.debug(f"Ожидание {self.interval_hours} часов до следующего резервного копирования", "BACKUP")
            
            # Ждем с проверкой каждую минуту, чтобы можно было быстро остановить
            minutes_to_wait = int(sleep_seconds // 60)
            for _ in range(minutes_to_wait):
                if not self.running:
                    break
                time.sleep(60)
            
            # Ждем оставшиеся секунды
            remaining_seconds = sleep_seconds % 60
            if remaining_seconds > 0 and self.running:
                time.sleep(remaining_seconds)
    
    def start(self):
        """Запускает планировщик в отдельном потоке."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("BackupScheduler запущен", "BACKUP")
        else:
            logger.warning("BackupScheduler уже запущен", "BACKUP")
    
    def stop(self):
        """Останавливает планировщик."""
        if self.running:
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)  # Ждем завершения потока
                if self.thread.is_alive():
                    logger.warning("Поток BackupScheduler не завершился корректно", "BACKUP")
            logger.info("BackupScheduler остановлен", "BACKUP")
        else:
            logger.warning("BackupScheduler не запущен", "BACKUP")
    
    def force_backup(self):
        """Принудительно создает резервную копию."""
        logger.info("Принудительное создание резервной копии", "BACKUP")
        backup_path = self.backup_manager.create_backup()
        if backup_path:
            self.next_backup_time = datetime.now() + timedelta(hours=self.interval_hours)
            logger.success(f"Принудительная резервная копия создана: {backup_path}", "BACKUP")
        else:
            logger.error("Не удалось создать принудительную резервную копию", "BACKUP")
        return backup_path
    
    def get_status(self):
        """Возвращает текущий статус планировщика."""
        return {
            'running': self.running,
            'enabled': self.enabled,
            'interval_hours': self.interval_hours,
            'next_backup': self.next_backup_time.strftime("%Y-%m-%d %H:%M:%S") if self.next_backup_time else None
        }
    
    def update_config(self):
        """Обновление конфигурации планировщика"""
        try:
            # Перезагружаем конфигурацию из файла
            self.backup_manager.config = self.backup_manager._load_config()
            self.config = self.backup_manager.get_backup_info()
            self.interval_hours = self.config.get('interval_hours', 1)
            self.enabled = self.config.get('enabled', True)
            
            logger.info(f"Конфигурация планировщика обновлена (интервал: {self.interval_hours}ч, включен: {self.enabled})", "BACKUP")
            
            # Если планировщик был отключен, останавливаем его
            if not self.enabled and self.running:
                logger.info("Резервное копирование отключено в конфигурации, останавливаем планировщик", "BACKUP")
                self.stop()
            
        except Exception as e:
            logger.error(f"Ошибка обновления конфигурации планировщика: {e}", "BACKUP")

    def _notify_windows(self, title: str, message: str):
        """Показывает уведомление в Windows 10/11 через PowerShell BalloonTip (без внешних модулей).

        Использует System.Windows.Forms.NotifyIcon. В случае ошибки — не бросает исключение наружу.
        """
        try:
            # Экранируем для PowerShell (используем двойные кавычки и экранирование бектиком)
            def _ps_escape(text: str) -> str:
                return str(text).replace('`', '``').replace('"', '`"')

            ps_title = _ps_escape(title)
            ps_message = _ps_escape(message)

            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$ni = New-Object System.Windows.Forms.NotifyIcon; "
                "$ni.Icon = [System.Drawing.SystemIcons]::Information; "
                "$ni.BalloonTipTitle = \"{title}\"; "
                "$ni.BalloonTipText = \"{message}\"; "
                "$ni.Visible = $true; "
                "$ni.ShowBalloonTip(5000); "
                "Start-Sleep -Seconds 6; "
                "$ni.Dispose();"
            ).format(title=ps_title, message=ps_message)
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=10
            )
        except Exception as e:
            # Не прерываем основной поток работы
            logger.warning(f"Уведомление Windows не показано: {e}", "BACKUP")

# Глобальный экземпляр планировщика
_backup_scheduler = None

def get_backup_scheduler():
    """Получение глобального экземпляра планировщика резервного копирования."""
    global _backup_scheduler
    if _backup_scheduler is None:
        _backup_scheduler = BackupScheduler()
    return _backup_scheduler

def start_backup_scheduler():
    """Запускает глобальный планировщик резервного копирования."""
    scheduler = get_backup_scheduler()
    scheduler.start()

def stop_backup_scheduler():
    """Останавливает глобальный планировщик резервного копирования."""
    scheduler = get_backup_scheduler()
    scheduler.stop()
