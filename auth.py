#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Простая система аутентификации
"""

import hashlib
import json
import os
from functools import wraps
from flask import request, Response, session, redirect, url_for
from logger import logger

class SimpleAuth:
    """
    Простая система аутентификации для ToDoLite
    """
    
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.users = self._load_users()
        self.session_timeout = 3600  # 1 час
        
    def _load_users(self):
        """Загружает пользователей из конфигурации"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                auth_config = config.get('auth', {})
                
                if not auth_config.get('enabled', False):
                    return {}
                
                users = auth_config.get('users', {})
                # Проверяем, хешированы ли пароли или это plaintext
                hashed_users = {}
                for username, password in users.items():
                    # Если пароль уже хеширован (bcrypt начинается с $2b$ или $2a$), используем как есть
                    if isinstance(password, str) and (password.startswith('$2b$') or password.startswith('$2a$')):
                        hashed_users[username] = password
                    else:
                        # Иначе хешируем (для обратной совместимости со старыми конфигурациями)
                        hashed_users[username] = self._hash_password(password)
                
                logger.info(f"Загружено {len(hashed_users)} пользователей", "AUTH")
                return hashed_users
                
        except FileNotFoundError:
            logger.warning("Файл конфигурации не найден, аутентификация отключена", "AUTH")
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки пользователей: {e}", "AUTH")
            return {}
    
    def _hash_password(self, password):
        """Хеширует пароль с использованием bcrypt"""
        try:
            import bcrypt
            # Генерируем соль и хешируем пароль
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except ImportError:
            # Fallback на SHA-256 если bcrypt не установлен (для обратной совместимости)
            logger.warning("bcrypt не установлен, используется SHA-256 (небезопасно!)", "AUTH")
            return hashlib.sha256(password.encode()).hexdigest()
    
    def check_auth(self, username, password):
        """Проверяет аутентификацию пользователя"""
        if not self.users:
            return True  # Аутентификация отключена
        
        if username not in self.users:
            logger.warning(f"Попытка входа с несуществующим пользователем: {username}", "AUTH")
            return False
        
        stored_hash = self.users[username]
        
        # Проверяем, является ли хеш bcrypt (начинается с $2b$)
        if stored_hash.startswith('$2b$') or stored_hash.startswith('$2a$'):
            try:
                import bcrypt
                # Проверяем пароль с bcrypt
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    logger.info(f"Успешная аутентификация пользователя: {username}", "AUTH")
                    return True
                else:
                    logger.warning(f"Неверный пароль для пользователя: {username}", "AUTH")
                    return False
            except ImportError:
                logger.error("bcrypt не установлен, невозможно проверить пароль", "AUTH")
                return False
        else:
            # Старый формат SHA-256 (для обратной совместимости)
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == hashed_password:
                logger.info(f"Успешная аутентификация пользователя: {username} (SHA-256)", "AUTH")
                # Мигрируем на bcrypt при следующем входе
                try:
                    import bcrypt
                    new_hash = self._hash_password(password)
                    self._update_user_password(username, new_hash)
                except ImportError:
                    pass
                return True
            else:
                logger.warning(f"Неверный пароль для пользователя: {username}", "AUTH")
                return False
    
    def require_auth(self, f):
        """Декоратор для защиты маршрутов"""
        @wraps(f)
        def decorated(*args, **kwargs):
            # Если аутентификация отключена, пропускаем
            if not self.users:
                return f(*args, **kwargs)
            
            # Проверяем сессию
            if 'authenticated' in session and session['authenticated']:
                return f(*args, **kwargs)
            
            # Проверяем HTTP Basic Auth
            auth = request.authorization
            if auth and self.check_auth(auth.username, auth.password):
                session['authenticated'] = True
                session['username'] = auth.username
                return f(*args, **kwargs)
            
            # Требуем аутентификацию
            logger.warning(f"Попытка доступа к защищенному маршруту без аутентификации: {request.endpoint}", "AUTH")
            return Response(
                'Требуется аутентификация для доступа к ToDoLite',
                401,
                {'WWW-Authenticate': 'Basic realm="ToDoLite"'}
            )
        return decorated
    
    def login_required(self, f):
        """Декоратор для защиты маршрутов (альтернативный)"""
        @wraps(f)
        def decorated(*args, **kwargs):
            if not self.users:
                return f(*args, **kwargs)
            
            if 'authenticated' not in session or not session['authenticated']:
                return redirect(url_for('login'))
            
            return f(*args, **kwargs)
        return decorated
    
    def logout(self):
        """Выход из системы"""
        if 'authenticated' in session:
            username = session.get('username', 'unknown')
            session.clear()
            logger.info(f"Пользователь {username} вышел из системы", "AUTH")
    
    def is_authenticated(self):
        """Проверяет, аутентифицирован ли пользователь"""
        if not self.users:
            return True
        return 'authenticated' in session and session['authenticated']
    
    def get_current_user(self):
        """Возвращает текущего пользователя"""
        if not self.users:
            return 'admin'
        return session.get('username', 'unknown')
    
    def _update_user_password(self, username, new_hash):
        """Обновляет пароль пользователя в конфигурации (для миграции на bcrypt)"""
        try:
            # Загружаем конфигурацию
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Обновляем хеш пароля
            if 'auth' in config and 'users' in config['auth']:
                # Если пользователь существует, обновляем его хеш
                if username in config['auth']['users']:
                    # Сохраняем новый хеш (если это bcrypt, сохраняем как есть)
                    config['auth']['users'][username] = new_hash
                    
                    # Сохраняем конфигурацию
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    
                    # Обновляем в памяти
                    self.users[username] = new_hash
                    logger.info(f"Пароль пользователя {username} мигрирован на bcrypt", "AUTH")
        except Exception as e:
            logger.error(f"Ошибка обновления пароля пользователя {username}: {e}", "AUTH")

# Глобальный экземпляр аутентификации
_auth_instance = None

def get_auth():
    """Получает глобальный экземпляр аутентификации"""
    global _auth_instance
    if _auth_instance is None:
        _auth_instance = SimpleAuth()
    return _auth_instance

def require_auth(f):
    """Декоратор для защиты маршрутов"""
    return get_auth().require_auth(f)

def login_required(f):
    """Декоратор для защиты маршрутов (альтернативный)"""
    return get_auth().login_required(f)
