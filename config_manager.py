#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Упрощенный менеджер конфигурации
"""

import json
import os
from logger import logger

class ConfigManager:
    """
    Упрощенный менеджер конфигурации для ToDoLite
    """
    
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        logger.info("ConfigManager инициализирован", "CONFIG")
    
    def _get_default_config(self):
        """Возвращает конфигурацию по умолчанию"""
        return {
            "version": "1.5.2",
            "version_date": "2025-10-13",
            "version_type": "development",
            "auth": {
                "enabled": False,
                "users": {
                    "admin": "password123"
                }
            },
            "backup": {
                "enabled": True,
                "interval_hours": 1,
                "destinations": [
                    "C:\\Backups\\ToDoLite",
                    "D:\\Backups\\ToDoLite"
                ],
                "max_backups": 10,
                "compress": True
            },
            "notifications": {
                "enabled": True,
                "reminder_times": [15, 30, 60, 1440]
            },
            "statuses_order": [
                "new", "later", "tracking", "working", 
                "waiting", "think", "done", "cancelled"
            ],
            "statuses_labels": {
                "new": "📝 Новые",
                "later": "📅 Завтра", 
                "tracking": "👁️ Отслеживаем",
                "working": "🔥 Сегодня",
                "waiting": "📆 На неделе",
                "think": "🔮 Далекие",
                "done": "✅ Готово",
                "cancelled": "❌ Отменено"
            },
            "auto_migration": {
                "enabled": True,
                "interval_minutes": 30
            },
            "eisenhower_order": [
                "urgent_important",
                "urgent_not_important", 
                "not_urgent_important",
                "not_urgent_not_important"
            ],
            "eisenhower_labels": {
                "urgent_important": "🔥 Важные и срочные",
                "urgent_not_important": "⚡ Срочные не важные",
                "not_urgent_important": "⭐ Важные не срочные",
                "not_urgent_not_important": "📋 Не важные не срочные"
            }
        }
    
    def _merge_configs(self, default_config, user_config):
        """Объединяет конфигурацию по умолчанию с пользовательской"""
        merged = default_config.copy()
        
        for key, value in user_config.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _load_config(self):
        """Загружает конфигурацию из файла"""
        default_config = self._get_default_config()
        
        if not os.path.exists(self.config_path):
            logger.info("Файл конфигурации не найден, создаем с настройками по умолчанию", "CONFIG")
            self._save_config(default_config)
            return default_config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                merged_config = self._merge_configs(default_config, user_config)
                logger.info("Конфигурация загружена успешно", "CONFIG")
                return merged_config
                
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON в конфигурации: {e}", "CONFIG")
            logger.info("Используем конфигурацию по умолчанию", "CONFIG")
            return default_config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации: {e}", "CONFIG")
            logger.info("Используем конфигурацию по умолчанию", "CONFIG")
            return default_config
    
    def _save_config(self, config):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info("Конфигурация сохранена", "CONFIG")
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}", "CONFIG")
    
    def get(self, key, default=None):
        """
        Получает значение конфигурации по ключу
        
        Args:
            key: Ключ в формате 'section.subsection.key'
            default: Значение по умолчанию
        
        Returns:
            Значение конфигурации или default
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key, value):
        """
        Устанавливает значение конфигурации
        
        Args:
            key: Ключ в формате 'section.subsection.key'
            value: Новое значение
        """
        keys = key.split('.')
        config = self.config
        
        # Создаем вложенные словари если нужно
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Устанавливаем значение
        config[keys[-1]] = value
        
        # Сохраняем конфигурацию
        self._save_config(self.config)
        logger.info(f"Конфигурация обновлена: {key} = {value}", "CONFIG")
    
    def get_auth_config(self):
        """Получает конфигурацию аутентификации"""
        return {
            'enabled': self.get('auth.enabled', False),
            'users': self.get('auth.users', {})
        }
    
    def get_backup_config(self):
        """Получает конфигурацию резервного копирования"""
        return {
            'enabled': self.get('backup.enabled', True),
            'interval_hours': self.get('backup.interval_hours', 1),
            'destinations': self.get('backup.destinations', []),
            'max_backups': self.get('backup.max_backups', 10),
            'compress': self.get('backup.compress', True)
        }
    
    def get_notifications_config(self):
        """Получает конфигурацию уведомлений"""
        return {
            'enabled': self.get('notifications.enabled', True),
            'reminder_times': self.get('notifications.reminder_times', [15, 30, 60, 1440])
        }
    
    def get_statuses_config(self):
        """Получает конфигурацию статусов"""
        return {
            'order': self.get('statuses_order', []),
            'labels': self.get('statuses_labels', {})
        }
    
    def get_eisenhower_config(self):
        """Получает конфигурацию матрицы Эйзенхауэра"""
        return {
            'order': self.get('eisenhower_order', []),
            'labels': self.get('eisenhower_labels', {})
        }
    
    def get_auto_migration_config(self):
        """Получает конфигурацию автоматической миграции"""
        return {
            'enabled': self.get('auto_migration.enabled', True),
            'interval_minutes': self.get('auto_migration.interval_minutes', 30)
        }
    
    def get_config(self):
        """Получает полную конфигурацию"""
        return self.config
    
    def enable_auth(self, users=None):
        """Включает аутентификацию"""
        if users is None:
            users = {'admin': 'password123'}
        
        self.set('auth.enabled', True)
        self.set('auth.users', users)
        logger.info("Аутентификация включена", "CONFIG")
    
    def disable_auth(self):
        """Отключает аутентификацию"""
        self.set('auth.enabled', False)
        logger.info("Аутентификация отключена", "CONFIG")
    
    def add_backup_destination(self, path):
        """Добавляет путь для резервного копирования"""
        destinations = self.get('backup.destinations', [])
        if path not in destinations:
            destinations.append(path)
            self.set('backup.destinations', destinations)
            logger.info(f"Добавлен путь резервного копирования: {path}", "CONFIG")
    
    def remove_backup_destination(self, path):
        """Удаляет путь для резервного копирования"""
        destinations = self.get('backup.destinations', [])
        if path in destinations:
            destinations.remove(path)
            self.set('backup.destinations', destinations)
            logger.info(f"Удален путь резервного копирования: {path}", "CONFIG")
    
    def get_version_info(self):
        """Получает информацию о версии"""
        return {
            'version': self.get('version', '1.5.2'),
            'version_date': self.get('version_date', '2025-10-13'),
            'version_type': self.get('version_type', 'development')
        }
    
    def update_version(self, version, version_date, version_type):
        """Обновляет информацию о версии"""
        self.set('version', version)
        self.set('version_date', version_date)
        self.set('version_type', version_type)
        logger.info(f"Версия обновлена: {version} ({version_type})", "CONFIG")
    
    def export_config(self, export_path):
        """Экспортирует конфигурацию в файл"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                logger.info(f"Конфигурация экспортирована: {export_path}", "CONFIG")
                return True
        except Exception as e:
            logger.error(f"Ошибка экспорта конфигурации: {e}", "CONFIG")
            return False
    
    def import_config(self, import_path):
        """Импортирует конфигурацию из файла"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
                self.config = self._merge_configs(self._get_default_config(), imported_config)
                self._save_config(self.config)
                logger.info(f"Конфигурация импортирована: {import_path}", "CONFIG")
                return True
        except Exception as e:
            logger.error(f"Ошибка импорта конфигурации: {e}", "CONFIG")
            return False
    
    def reset_to_defaults(self):
        """Сбрасывает конфигурацию к значениям по умолчанию"""
        self.config = self._get_default_config()
        self._save_config(self.config)
        logger.info("Конфигурация сброшена к значениям по умолчанию", "CONFIG")

# Глобальный экземпляр менеджера конфигурации
_config_manager = None

def get_config_manager():
    """Получает глобальный экземпляр менеджера конфигурации"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
