#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Менеджер резервного копирования
"""

import sqlite3
import os
import shutil
import gzip
from datetime import datetime
import json
import time
import threading
from logger import logger
import re
import tempfile

class BackupManager:
    """
    Управляет созданием, валидацией и восстановлением резервных копий базы данных ToDoLite.
    """
    
    def __init__(self, config_path='config.json', db_path='tasks.db'):
        self.config_path = config_path
        self.db_path = db_path
        self.config = self._load_config()
        self.backup_settings = self.config.get('backup', {})
        self.lock = threading.Lock()  # Для обеспечения атомарности операций с БД
        logger.info("BackupManager инициализирован", "BACKUP")
    
    def _load_config(self):
        """Загружает конфигурацию из файла."""
        try:
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл конфигурации не найден: {self.config_path}", "BACKUP")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка чтения конфигурации JSON: {e}", "BACKUP")
            return {}
        except Exception as e:
            logger.error(f"Неизвестная ошибка при загрузке конфигурации: {e}", "BACKUP")
            return {}
    
    def _get_backup_paths(self):
        """Возвращает список путей для резервного копирования (устаревший способ).

        Оставлено для обратной совместимости с конфигурациями, где
        используются поля primary_paths + fallback_path.
        """
        primary_paths = self.backup_settings.get('primary_paths', [])
        fallback_path = self.backup_settings.get('fallback_path')

        paths = []
        for p in primary_paths:
            paths.append(os.path.expandvars(p))  # Разворачиваем переменные окружения
        if fallback_path:
            paths.append(os.path.expandvars(fallback_path))

        # Удаляем дубликаты и пустые пути
        paths = list(dict.fromkeys([p for p in paths if p]))

        for p in paths:
            logger.debug(f"Путь для резервного копирования/восстановления (legacy): {p}", "BACKUP")
        return paths

    def get_destinations(self):
        """Возвращает упорядоченный список направлений (директорий) для бэкапа.

        Приоритет определяется порядком перечисления. Поддерживает два формата конфигурации:
        - Новый: backup.destinations = ["C:/...", "D:/...", ...]
        - Старый: backup.primary_paths + backup.fallback_path
        """
        destinations = self.backup_settings.get('destinations')
        if destinations and isinstance(destinations, list):
            paths = [os.path.expandvars(p) for p in destinations if p]
        else:
            # Обратная совместимость
            paths = self._get_backup_paths()

        # Удаляем дубликаты, пустые и нормализуем
        normalized = []
        for p in paths:
            if not p:
                continue
            try:
                full = os.path.normpath(p)
            except Exception:
                full = p
            if full not in normalized:
                normalized.append(full)

        for p in normalized:
            logger.debug(f"Назначение бэкапа: {p}", "BACKUP")
        return normalized
    
    def _ensure_backup_dirs(self, paths):
        """Создает директории для резервных копий, если они не существуют."""
        for path in paths:
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                logger.error(f"Не удалось создать директории для резервных копий {path}: {e}", "BACKUP")
                return False
        return True
    
    def _get_db_size(self):
        """Возвращает размер базы данных в байтах."""
        try:
            return os.path.getsize(self.db_path)
        except FileNotFoundError:
            return 0
        except Exception as e:
            logger.error(f"Ошибка получения размера базы данных {self.db_path}: {e}", "BACKUP")
            return 0
    
    def create_backup(self):
        """
        Создает резервную копию базы данных.
        Пытается сохранить в основные пути, затем в резервный.
        Возвращает путь к созданной копии или None в случае неудачи.
        """
        if not self.backup_settings.get('enabled', False):
            logger.info("Резервное копирование отключено в конфигурации", "BACKUP")
            return None
        
        with self.lock:  # Блокируем доступ к БД на время копирования
            logger.info("Начало создания резервной копии", "BACKUP")
            
            db_size = self._get_db_size()
            if db_size == 0:
                logger.warning("База данных пуста или не существует, резервная копия не создана", "BACKUP")
                return None
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"todolite_backup_{timestamp}.db"
            
            backup_paths = self._get_backup_paths()
            if not backup_paths:
                logger.error("Не настроены пути для резервного копирования", "BACKUP")
                return None
            
            self._ensure_backup_dirs(backup_paths)
            
            for path in backup_paths:
                try:
                    dest_path = os.path.join(path, backup_filename)
                    
                    # Копируем файл базы данных
                    shutil.copy2(self.db_path, dest_path)
                    logger.info(f"Файл базы данных скопирован: {self.db_path} -> {dest_path}", "BACKUP")
                    
                    # Если включено сжатие
                    if self.backup_settings.get('compress', True):
                        compressed_path = dest_path + '.gz'
                        with open(dest_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        os.remove(dest_path)  # Удаляем несжатую копию
                        dest_path = compressed_path
                        logger.info(f"Резервная копия сжата: {dest_path}", "BACKUP")
                    
                    logger.success(f"Резервная копия успешно создана: {dest_path}", "BACKUP")
                    self._cleanup_old_backups(path)  # Очистка старых копий после успешного создания
                    return dest_path
                except Exception as e:
                    logger.error(f"Ошибка при создании резервной копии в {path}: {e}", "BACKUP")
            
            logger.error("Не удалось создать резервную копию ни по одному из путей", "BACKUP")
            return None

    def create_backup_all(self):
        """Создает резервную копию во ВСЕ доступные направления.

        - Генерирует единое имя копии на момент запуска
        - Пытается записать в каждую директорию по очереди
        - Возвращает список успешно созданных путей (включая .gz, если включено сжатие)
        - Если список пуст — значит, бэкап не удалось создать нигде
        """
        if not self.backup_settings.get('enabled', False):
            logger.info("Резервное копирование отключено в конфигурации", "BACKUP")
            return []

        with self.lock:
            logger.info("Начало массового создания резервной копии (во все направления)", "BACKUP")

            db_size = self._get_db_size()
            if db_size == 0:
                logger.warning("База данных пуста или не существует, резервная копия не создана", "BACKUP")
                return []

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"todolite_backup_{timestamp}.db"

            destinations = self.get_destinations()
            if not destinations:
                logger.error("Не настроены пути для резервного копирования", "BACKUP")
                return []

            self._ensure_backup_dirs(destinations)

            successes = []
            for path in destinations:
                try:
                    dest_path = os.path.join(path, backup_filename)
                    shutil.copy2(self.db_path, dest_path)
                    logger.info(f"Файл базы данных скопирован: {self.db_path} -> {dest_path}", "BACKUP")

                    if self.backup_settings.get('compress', True):
                        compressed_path = dest_path + '.gz'
                        with open(dest_path, 'rb') as f_in:
                            with gzip.open(compressed_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        os.remove(dest_path)
                        dest_path = compressed_path
                        logger.info(f"Резервная копия сжата: {dest_path}", "BACKUP")

                    logger.success(f"Резервная копия успешно создана: {dest_path}", "BACKUP")
                    successes.append(dest_path)
                    # Чистим старые копии в ЭТОМ направлении независимо
                    self._cleanup_old_backups(path)
                except Exception as e:
                    logger.error(f"Ошибка при создании резервной копии в {path}: {e}", "BACKUP")

            if not successes:
                logger.error("Не удалось создать резервную копию ни по одному из путей", "BACKUP")

            return successes

    def _is_db_valid(self, db_file: str) -> bool:
        """Проверяет, что файл БД существует, не пустой и проходит integrity_check."""
        try:
            if not os.path.exists(db_file):
                return False
            if os.path.getsize(db_file) <= 0:
                return False
            return self._validate_backup(db_file)
        except Exception:
            return False

    def find_latest_backup(self):
        """Находит самую свежую резервную копию среди всех направлений.

        Возвращает словарь { 'path': str, 'timestamp': datetime } либо None.
        При равенстве времени выбирает по приоритету направлений (раньше в списке — выше приоритет).
        """
        pattern = re.compile(r"^todolite_backup_(\d{8}_\d{6})\.db(\.gz)?$")
        destinations = self.get_destinations()
        candidates = []

        for priority, base in enumerate(destinations):
            try:
                if not os.path.exists(base):
                    continue
                for name in os.listdir(base):
                    m = pattern.match(name)
                    if not m:
                        continue
                    ts_str = m.group(1)
                    try:
                        ts = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                    except Exception:
                        continue
                    full_path = os.path.join(base, name)
                    candidates.append((ts, priority, full_path))
            except Exception as e:
                logger.error(f"Ошибка сканирования каталога бэкапов {base}: {e}", "BACKUP")

        if not candidates:
            return None

        # Сортировка: по времени убыв., затем по приоритету возр.
        candidates.sort(key=lambda x: (-int(x[0].strftime('%Y%m%d%H%M%S')), x[1]))
        ts, _, path = candidates[0]
        return { 'path': path, 'timestamp': ts }

    def restore_latest_on_start(self):
        """Пытается восстановить БД из последней копии при старте.

        Выполняется, если текущая БД отсутствует, пуста или не проходит integrity_check.
        """
        try:
            if self._is_db_valid(self.db_path):
                logger.info("Текущая БД валидна, восстановление на старте не требуется", "BACKUP")
                return False

            latest = self.find_latest_backup()
            if not latest:
                logger.warning("Не найдено ни одной резервной копии для восстановления", "BACKUP")
                return False

            backup_path = latest['path']
            logger.info(f"Попытка восстановления БД из свежей копии: {backup_path}", "BACKUP")
            ok = self.restore_backup(backup_path)
            if ok:
                logger.success(f"БД восстановлена из {backup_path}", "BACKUP")
                return True
            else:
                logger.error(f"Не удалось восстановить БД из {backup_path}", "BACKUP")
                return False
        except Exception as e:
            logger.error(f"Ошибка восстановления БД на старте: {e}", "BACKUP")
            return False
    
    def _cleanup_old_backups(self, path):
        """Удаляет старые резервные копии, оставляя только max_backups."""
        max_backups = self.backup_settings.get('max_backups', 10)
        if max_backups <= 0:
            return
        
        try:
            backup_files = []
            for f in os.listdir(path):
                if f.startswith('todolite_backup_') and (f.endswith('.db') or f.endswith('.db.gz')):
                    file_path = os.path.join(path, f)
                    backup_files.append((os.path.getmtime(file_path), file_path))
            
            backup_files.sort(key=lambda x: x[0], reverse=True)  # Сортируем по дате изменения (новые в начале)
            
            for i in range(max_backups, len(backup_files)):
                os.remove(backup_files[i][1])
                logger.info(f"Удалена старая резервная копия: {backup_files[i][1]}", "BACKUP")
        except Exception as e:
            logger.error(f"Ошибка при очистке старых резервных копий в {path}: {e}", "BACKUP")
    
    def restore_backup(self, backup_file):
        """
        Восстанавливает базу данных из указанной резервной копии.
        Создает временную копию текущей БД перед восстановлением.
        """
        with self.lock:  # Блокируем доступ к БД на время восстановления
            logger.info(f"Начало восстановления из резервной копии: {backup_file}", "BACKUP")
            
            if not os.path.exists(backup_file):
                logger.error(f"Файл резервной копии не найден: {backup_file}", "BACKUP")
                return False
            
            if not self.validate_backup(backup_file):
                logger.error(f"Резервная копия {backup_file} не прошла валидацию, восстановление отменено", "BACKUP")
                return False
            
            # Создаем временную копию текущей БД перед восстановлением
            current_db_backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(self.db_path, current_db_backup_path)
                logger.info(f"Создана временная копия текущей БД: {current_db_backup_path}", "BACKUP")
            except Exception as e:
                logger.error(f"Не удалось создать временную копию текущей БД: {e}", "BACKUP")
                return False
            
            try:
                # Если файл сжат, распаковываем во временный файл
                if backup_file.endswith('.gz'):
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                        temp_path = temp_file.name
                    
                    with gzip.open(backup_file, 'rb') as f_in:
                        with open(temp_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    shutil.copy2(temp_path, self.db_path)
                    os.unlink(temp_path)
                else:
                    shutil.copy2(backup_file, self.db_path)
                
                logger.success(f"База данных успешно восстановлена из: {backup_file}", "BACKUP")
                return True
            except Exception as e:
                logger.error(f"Ошибка при восстановлении базы данных: {e}", "BACKUP")
                # Попытка восстановить из временной копии, если что-то пошло не так
                try:
                    shutil.copy2(current_db_backup_path, self.db_path)
                    logger.warning(f"Восстановлена предыдущая версия БД из временной копии: {current_db_backup_path}", "BACKUP")
                except Exception as rollback_e:
                    logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: Не удалось восстановить БД и откат не удался: {rollback_e}", "BACKUP")
                return False
            finally:
                # Удаляем временную копию текущей БД
                try:
                    os.remove(current_db_backup_path)
                    logger.debug(f"Удалена временная копия текущей БД: {current_db_backup_path}", "BACKUP")
                except Exception as e:
                    logger.warning(f"Не удалось удалить временную копию текущей БД {current_db_backup_path}: {e}", "BACKUP")
    
    def _validate_backup(self, db_file):
        """Внутренняя функция для проверки целостности файла SQLite."""
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            if result == 'ok':
                logger.info(f"Резервная копия {db_file} валидна", "BACKUP")
                return True
            else:
                logger.error(f"Резервная копия {db_file} повреждена: {result}", "BACKUP")
                return False
        except sqlite3.Error as e:
            logger.error(f"Ошибка валидации резервной копии: {e}", "BACKUP")
            return False
        finally:
            if conn:
                conn.close()
    
    def validate_backup(self, backup_file):
        """Проверка целостности резервной копии"""
        try:
            # Если файл сжат, распаковываем во временный файл
            if backup_file.endswith('.gz'):
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                    temp_path = temp_file.name
                
                with gzip.open(backup_file, 'rb') as f_in:
                    with open(temp_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                try:
                    result = self._validate_backup(temp_path)
                finally:
                    os.unlink(temp_path)
                
                return result
            else:
                return self._validate_backup(backup_file)
                
        except Exception as e:
            logger.error(f"Ошибка валидации резервной копии: {e}", "BACKUP")
            return False
    
    def get_backup_info(self):
        """Получение информации о настройках резервного копирования"""
        backup_config = self.config.get('backup', {})
        return {
            'enabled': backup_config.get('enabled', False),
            'interval_hours': backup_config.get('interval_hours', 1),
            'primary_paths': [os.path.expandvars(p) for p in backup_config.get('primary_paths', [])],
            'fallback_path': os.path.expandvars(backup_config.get('fallback_path', '')),
            'max_backups': backup_config.get('max_backups', 10),
            'compress': backup_config.get('compress', True)
        }
    
    def get_backup_list(self):
        """Возвращает список доступных резервных копий."""
        all_backups = []
        for path in self._get_backup_paths():
            try:
                if os.path.exists(path):
                    for f in os.listdir(path):
                        if f.startswith('todolite_backup_') and (f.endswith('.db') or f.endswith('.db.gz')):
                            file_path = os.path.join(path, f)
                            try:
                                timestamp_str = f.replace('todolite_backup_', '').split('.')[0]
                                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                                all_backups.append({
                                    'name': f,
                                    'path': file_path,
                                    'size': os.path.getsize(file_path),
                                    'timestamp': timestamp
                                })
                            except ValueError:
                                logger.warning(f"Не удалось разобрать метку времени для файла: {f}", "BACKUP")
            except Exception as e:
                logger.error(f"Ошибка получения списка резервных копий из {path}: {e}", "BACKUP")
        
        # Сортируем по убыванию даты
        all_backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_backups
