from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import lru_cache
import json
import re
import sqlite3
import os
import signal
import sys
from datetime import datetime
import html
import re as _re
from logger import logger
from markdown_utils import markdown_to_html, validate_markdown
from auth import require_auth, get_auth
from database_manager import get_db_manager
from config_manager import get_config_manager

app = Flask(__name__)
# Генерируем секретный ключ для сессий и CSRF
app.secret_key = os.environ.get('SECRET_KEY', 'todolite_secret_key_2025_change_in_production')

# Загружаем конфигурацию для проверки настроек безопасности
# ВАЖНО: Для обратной совместимости со старыми версиями CSRF защита отключена по умолчанию
# Включите её в config.json, добавив "security": {"csrf_enabled": true}
try:
    config_manager = get_config_manager()
    security_config = config_manager.get('security', {})
    csrf_enabled = security_config.get('csrf_enabled', False)  # По умолчанию ОТКЛЮЧЕНО для совместимости
except Exception as e:
    logger.warning(f"Ошибка загрузки конфигурации безопасности: {e}. CSRF защита отключена.", "CONFIG")
    csrf_enabled = False

app.config['WTF_CSRF_ENABLED'] = csrf_enabled
app.config['WTF_CSRF_TIME_LIMIT'] = None  # Без ограничения времени

# Настройка безопасности сессий
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Защита от XSS через JavaScript
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Защита от CSRF
# SESSION_COOKIE_SECURE устанавливается только для HTTPS (в production)
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True

# Инициализируем CSRF защиту только если она включена
csrf = None
if csrf_enabled:
    csrf = CSRFProtect(app)
    logger.info("CSRF защита включена", "SECURITY")
else:
    logger.warning("CSRF защита ОТКЛЮЧЕНА для обратной совместимости со старыми версиями. Для включения добавьте в config.json: \"security\": {\"csrf_enabled\": true}", "SECURITY")
    # Добавляем функцию-заглушку для шаблонов, чтобы избежать ошибок
    @app.context_processor
    def inject_csrf_token():
        """Добавляет функцию csrf_token в контекст шаблонов"""
        def csrf_token():
            return ""  # Возвращаем пустую строку, когда CSRF отключен
        return dict(csrf_token=csrf_token)

# Настройка rate limiting для защиты от DoS
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour", "50 per minute"],
    storage_uri="memory://"
)

# Настройка security headers
@app.after_request
def set_security_headers(response):
    """Устанавливает заголовки безопасности для всех ответов"""
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Content Security Policy (базовая)
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

# Добавляем фильтр markdown в Jinja2
@app.template_filter('markdown')
def markdown_filter(text):
    """Фильтр для конвертации Markdown в HTML в шаблонах"""
    if not text:
        return ""
    return markdown_to_html(text)

# Переменная для отслеживания состояния сервера
server_running = True

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global server_running
    logger.warning(f"Получен сигнал {signum}. Завершение работы...", "SIGNAL")
    server_running = False
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Проверяем существование таблицы и обновляем схему
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
    table_exists = c.fetchone()
    
    if table_exists:
        # Проверяем существование новых колонок
        c.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in c.fetchall()]
        
        # Добавляем недостающие колонки
        new_columns = [
            ('short_description', 'TEXT'),
            ('full_description', 'TEXT'),
            ('eisenhower_priority', 'TEXT DEFAULT "not_urgent_not_important"'),
            ('assigned_to', 'TEXT'),
            ('related_threads', 'TEXT'),
            ('scheduled_date', 'DATE'),
            ('due_date', 'DATE'),
            ('reminder_time', 'DATETIME'),
            ('tags', 'TEXT'),
            ('completed_at', 'TIMESTAMP')
        ]
        
        for col_name, col_type in new_columns:
            if col_name not in columns:
                c.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
        
        # Обновляем статус по умолчанию если нужно
        if 'status' in columns:
            c.execute("UPDATE tasks SET status = 'new' WHERE status = 'todo'")
    else:
        # Создаем новую таблицу
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
                      tags TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      completed_at TIMESTAMP,
                      archived BOOLEAN DEFAULT 0,
                      archived_at TIMESTAMP,
                      archived_from_status TEXT)''')
    
    # Создаем таблицу комментариев
    c.execute('''CREATE TABLE IF NOT EXISTS task_comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task_id INTEGER NOT NULL,
                  comment TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE)''')
    
    # Проверяем и добавляем новые поля для архивирования (если таблица уже существует)
    if table_exists:
        # Обновляем список колонок после добавления новых
        c.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in c.fetchall()]
        
        # Добавляем поля для архивирования, если их нет
        archive_columns = [
            ('archived', 'BOOLEAN DEFAULT 0'),
            ('archived_at', 'TIMESTAMP'),
            ('archived_from_status', 'TEXT')
        ]
        
        for col_name, col_type in archive_columns:
            if col_name not in columns:
                try:
                    c.execute(f"ALTER TABLE tasks ADD COLUMN {col_name} {col_type}")
                    logger.database(f"Добавлено поле {col_name} в таблицу tasks", "MIGRATION")
                except sqlite3.OperationalError as e:
                    logger.warning(f"Не удалось добавить поле {col_name}: {e}", "MIGRATION")
    
    # Создаем индексы для оптимизации запросов (только если колонки существуют)
    if table_exists:
        c.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in c.fetchall()]
        
        # Создаем индексы только для существующих колонок
        indexes = []
        if 'archived' in columns:
            indexes.append(("idx_tasks_archived", "tasks", "archived"))
        if 'status' in columns:
            indexes.append(("idx_tasks_status", "tasks", "status"))
        if 'due_date' in columns:
            indexes.append(("idx_tasks_due_date", "tasks", "due_date"))
        if 'scheduled_date' in columns:
            indexes.append(("idx_tasks_scheduled_date", "tasks", "scheduled_date"))
        if 'created_at' in columns:
            indexes.append(("idx_tasks_created_at", "tasks", "created_at"))
        
        # Проверяем существование таблицы комментариев
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_comments'")
        if c.fetchone():
            indexes.append(("idx_task_comments_task_id", "task_comments", "task_id"))
        
        for index_name, table_name, column_name in indexes:
            try:
                c.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})")
                logger.database(f"Создан индекс {index_name} на {table_name}.{column_name}", "MIGRATION")
            except sqlite3.OperationalError as e:
                logger.warning(f"Ошибка создания индекса {index_name}: {e}", "MIGRATION")
    
    conn.commit()
    conn.close()

# Получить все задачи (исключая архивированные)
def get_tasks():
    db = get_db_manager()
    # Проверяем наличие колонки archived для обратной совместимости
    try:
        # Пытаемся выполнить запрос с проверкой archived
        tasks = db.execute_query(
            "SELECT * FROM tasks WHERE (archived = 0 OR archived IS NULL) ORDER BY created_at DESC",
            fetch=True
        )
    except sqlite3.OperationalError:
        # Если колонка archived отсутствует, получаем все задачи
        logger.warning("Колонка 'archived' отсутствует, получаем все задачи", "MIGRATION")
        tasks = db.execute_query(
            "SELECT * FROM tasks ORDER BY created_at DESC",
            fetch=True
        )
    return tasks

# Получить задачи по режиму отображения
def get_tasks_by_mode(mode):
    db = get_db_manager()
    query = db.get_tasks_base_query(mode=mode, include_comments=False)
    tasks = db.execute_query(query, fetch=True)
    return tasks

# Получить задачи по режиму отображения с комментариями для поиска
def get_tasks_by_mode_with_comments(mode):
    db = get_db_manager()
    # Получаем все задачи с комментариями одним запросом (исправление N+1 проблемы)
    query = db.get_tasks_base_query(mode=mode, include_comments=True)
    tasks = db.execute_query(query, fetch=True)
    
    # Преобразуем результаты: заменяем NULL на пустую строку для комментариев
    tasks_with_comments = []
    for task in tasks:
        # Последний элемент - это комментарии (может быть None)
        task_list = list(task)
        if task_list[-1] is None:
            task_list[-1] = ''
        tasks_with_comments.append(tuple(task_list))
    
    return tasks_with_comments


def _clean_json(text: str) -> str:
    # Remove BOM
    text = text.lstrip('\ufeff')
    # Remove // comments
    text = re.sub(r"(^|\s)//.*$", "", text, flags=re.MULTILINE)
    # Remove /* */ comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove trailing commas before } or ]
    text = re.sub(r",\s*(\}|\])", r"\1", text)
    return text

def load_config():
    """Загружает конфигурацию из config.json"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            raw = f.read()
            try:
                return json.loads(raw)
            except Exception:
                # Пытаемся почистить и распарсить с мягкой толерантностью к комментам/висячим запятым
                cleaned = _clean_json(raw)
                return json.loads(cleaned)
    except Exception:
        return {
            "statuses_order": ["new","think","later","waiting","working","tracking","done","cancelled"],
            "statuses_labels": {
                "new": "🆕 Новая","think": "🤔 На подумать","later": "⏰ На потом","waiting": "⏳ Ждем кого-то","working": "⚡ В работе","tracking": "👀 Отслеживаем","done": "✅ Готово","cancelled": "❌ Отменено"
            },
            "eisenhower_order": ["urgent_important","urgent_not_important","not_urgent_important","not_urgent_not_important"],
            "eisenhower_labels": {
                "urgent_important": "🔥 Важные и срочные","urgent_not_important": "⚡ Срочные не важные","not_urgent_important": "⭐ Важные не срочные","not_urgent_not_important": "📋 Не важные не срочные"
            }
        }


# Фильтр Jinja для форматирования даты в российском формате (ДД.ММ.ГГГГ)
def format_date_ru(value: str):
    if not value:
        return ''
    try:
        # Попытка ISO с временем
        # Обрезаем возможные микросекунды/таймзону
        cleaned = str(value).strip()
        # Если только дата
        try:
            dt = datetime.strptime(cleaned[:10], '%Y-%m-%d')
            return dt.strftime('%d.%m.%Y')
        except Exception as e:
            logger.debug(f"Ошибка форматирования даты: {e}", "FORMAT")
        # Дата+время
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                dt = datetime.strptime(cleaned[:26], fmt)
                return dt.strftime('%d.%m.%Y')
            except Exception:
                continue
        # Последняя попытка: fromisoformat если доступно
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt.strftime('%d.%m.%Y')
        except Exception:
            return cleaned
    except Exception:
        return ''


def format_datetime_ru(value: str):
    """Форматирует дату и время в русском формате"""
    if not value:
        return ''
    try:
        cleaned = str(value).strip()
        # Попытка ISO с временем
        for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S.%f'):
            try:
                dt = datetime.strptime(cleaned[:26], fmt)
                return dt.strftime('%d.%m.%Y %H:%M')
            except Exception:
                continue
        # Последняя попытка: fromisoformat если доступно
        try:
            dt = datetime.fromisoformat(cleaned)
            return dt.strftime('%d.%m.%Y %H:%M')
        except Exception:
            return cleaned
    except Exception:
        return ''

# Регистрируем фильтры в Jinja
app.jinja_env.filters['ru_date'] = format_date_ru
app.jinja_env.filters['ru_datetime'] = format_datetime_ru


# Безопасная очистка HTML: убираем опасные теги и атрибуты
_ALLOWED_TAGS = {
    'b','strong','i','em','u','s','strike','span','div','p','br','hr',
    'ul','ol','li','blockquote','pre','code','a','h1','h2','h3','h4','h5','h6',
    'table','tr','td','th','tbody','thead','tfoot','colgroup','col'
}
_ALLOWED_ATTRS = {
    'a': {'href','title','target','rel'},
    'span': {'style'},
    'div': {'style'},
    'p': {'style'},
    'code': {'class'},
    'table': {'style','border','cellpadding','cellspacing','width'},
    'tr': {'style','height'},
    'td': {'style','width','height','colspan','rowspan','class'},
    'th': {'style','width','height','colspan','rowspan','class'},
    'tbody': {'style'},
    'thead': {'style'},
    'tfoot': {'style'},
    'colgroup': {'style'},
    'col': {'style','width'},
    '*': {'style'}
}

_STYLE_WHITELIST = _re.compile(r"^(color|background-color|text-align|font-weight|font-style|text-decoration|border|border-collapse|width|height|padding|margin):", _re.I)

def sanitize_html(raw: str) -> str:
    if not raw:
        return ''
    # Убираем опасные теги целиком
    cleaned = _re.sub(r"<(script|style)[\s\S]*?>[\s\S]*?<\/\1>", "", raw, flags=_re.I)
    # Удаляем on* обработчики и javascript: ссылки
    cleaned = _re.sub(r"\son\w+\s*=\s*\"[\s\S]*?\"", "", cleaned, flags=_re.I)
    cleaned = _re.sub(r"\son\w+\s*=\s*'[^']*'", "", cleaned, flags=_re.I)
    cleaned = _re.sub(r"\son\w+\s*=\s*[^\s>]+", "", cleaned, flags=_re.I)
    cleaned = _re.sub(r"(href|src)\s*=\s*(['\"])javascript:[^\2]*\2", r"\1=\2#\2", cleaned, flags=_re.I)

    # Разрешаем только whitelisted теги; остальные заменяем на текст
    def _replace_tag(match):
        groups = match.groups()
        if len(groups) < 3:
            return html.escape(match.group(0))
        
        closing = groups[0]
        name = groups[1].lower()
        attrs = groups[2] if len(groups) > 2 else ''
        
        if name not in _ALLOWED_TAGS:
            # Экранируем весь тег
            return html.escape(match.group(0))
        
        # Фильтруем атрибуты
        allowed_for_tag = _ALLOWED_ATTRS.get(name, set()) | _ALLOWED_ATTRS.get('*', set())
        def _attr_filter(attr_match):
            attr_groups = attr_match.groups()
            if len(attr_groups) < 3:
                return ''
            attr_name = attr_groups[0].lower()
            quote = attr_groups[1]
            val = attr_groups[2]
            if attr_name not in allowed_for_tag:
                return ''
            if attr_name == 'style':
                # Оставляем только разрешенные CSS свойства
                safe_parts = []
                for part in val.split(';'):
                    p = part.strip()
                    if p and _STYLE_WHITELIST.match(p):
                        safe_parts.append(p)
                val = '; '.join(safe_parts)
            if attr_name == 'href' and val.strip().lower().startswith('javascript:'):
                val = '#'
            return f" {attr_name}={quote}{html.escape(val, quote=True)}{quote}"

        safe_attrs = _re.sub(r"\s*(\w+)\s*=\s*([\"'])([\s\S]*?)\2", _attr_filter, attrs)
        return f"<{closing}{name}{safe_attrs}>"

    cleaned = _re.sub(r"<(\/?)([A-Za-z0-9]+)([^>]*)>", _replace_tag, cleaned)
    return cleaned

# Получить задачу по ID с комментариями
def get_task_with_comments(task_id):
    db = get_db_manager()
    
    # Получаем задачу
    task = db.execute_query("""
        SELECT 
            id,
            title,
            short_description,
            full_description,
            status,
            priority,
            eisenhower_priority,
            assigned_to,
            related_threads,
            scheduled_date,
            due_date,
            reminder_time,
            created_at,
            updated_at,
            completed_at,
            tags,
            archived,
            archived_at,
            archived_from_status
        FROM tasks WHERE id = ?
    """, (task_id,), fetchone=True)
    
    # Получаем комментарии
    # Новые комментарии первыми
    comments = db.execute_query(
        "SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at DESC",
        (task_id,),
        fetch=True
    )
    
    return task, comments

# Добавить новую задачу
def add_task(title, short_description, full_description, status, priority, eisenhower_priority, 
             assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags):
    logger.task(f"Создание новой задачи: '{title[:30]}...'", "CREATE")
    logger.database(f"Сохранение в БД: assigned_to='{assigned_to}', threads='{related_threads}'", "DB_WRITE")
    
    db = get_db_manager()
    db.execute_query("""INSERT INTO tasks (title, short_description, full_description, status, priority, 
                 eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (title, short_description, full_description, status, priority, eisenhower_priority,
               assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags))
    
    # Очищаем кэш тегов при изменении задач
    _get_cached_tags.cache_clear()
    
    logger.success(f"Задача успешно создана: '{title[:30]}...'", "CREATE")

# Обновить задачу
def update_task(task_id, title, short_description, full_description, status, priority, 
                eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags):
    logger.task(f"Обновление задачи ID {task_id}: '{title[:30]}...'", "UPDATE")
    logger.database(f"Обновление в БД: status='{status}', threads='{related_threads}', reminder_time='{reminder_time}'", "DB_WRITE")
    
    db = get_db_manager()
    # Если статус переводится в 'done', проставляем completed_at только один раз
    db.execute_query("""
        UPDATE tasks SET 
            title=?, 
            short_description=?, 
            full_description=?, 
            status=?, 
            priority=?, 
            eisenhower_priority=?, 
            assigned_to=?, 
            related_threads=?, 
            tags=?,
            scheduled_date=?, 
            due_date=?, 
            reminder_time=?,
            updated_at=CURRENT_TIMESTAMP,
            completed_at=CASE 
                WHEN ?='done' AND (completed_at IS NULL OR completed_at='') THEN CURRENT_TIMESTAMP 
                ELSE completed_at 
            END
        WHERE id=?
    """,
        (
            title, short_description, full_description, status, priority, eisenhower_priority,
            assigned_to, related_threads, tags, scheduled_date, due_date, reminder_time, status, task_id
        )
    )
    
    # Очищаем кэш тегов при изменении задач
    _get_cached_tags.cache_clear()
    
    logger.success(f"Задача ID {task_id} успешно обновлена", "UPDATE")

# Добавить комментарий к задаче
def add_comment(task_id, comment):
    db = get_db_manager()
    db.execute_query("INSERT INTO task_comments (task_id, comment) VALUES (?, ?)", (task_id, comment))

# Удалить задачу
def delete_task(task_id):
    db = get_db_manager()
    db.execute_query("DELETE FROM tasks WHERE id = ?", (task_id,))
    # Очищаем кэш тегов при изменении задач
    _get_cached_tags.cache_clear()

# Архивировать задачу
def archive_task(task_id):
    db = get_db_manager()
    
    # Проверяем наличие колонки archived для обратной совместимости
    if not db._check_column_exists('tasks', 'archived'):
        logger.warning("Колонка 'archived' отсутствует. Архивирование недоступно для старых БД.", "MIGRATION")
        return False
    
    # Получаем текущий статус задачи
    result = db.execute_query("SELECT status FROM tasks WHERE id = ?", (task_id,), fetchone=True)
    if not result:
        return False
    
    current_status = result[0]
    
    # Архивируем задачу (с проверкой наличия колонок)
    if db._check_column_exists('tasks', 'archived_from_status'):
        db.execute_query("""
            UPDATE tasks 
            SET archived = 1, 
                archived_at = CURRENT_TIMESTAMP,
                archived_from_status = ?
            WHERE id = ?
        """, (current_status, task_id))
    else:
        # Старая БД без archived_from_status
        if db._check_column_exists('tasks', 'archived_at'):
            db.execute_query("""
                UPDATE tasks 
                SET archived = 1, 
                    archived_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (task_id,))
        else:
            # Самая старая БД - только archived
            db.execute_query("""
                UPDATE tasks 
                SET archived = 1
                WHERE id = ?
            """, (task_id,))
    
    # Очищаем кэш тегов при изменении задач
    _get_cached_tags.cache_clear()
    
    return True

# Восстановить задачу из архива
def restore_task(task_id):
    db = get_db_manager()
    
    # Проверяем наличие колонки archived для обратной совместимости
    if not db._check_column_exists('tasks', 'archived'):
        logger.warning("Колонка 'archived' отсутствует. Восстановление недоступно для старых БД.", "MIGRATION")
        return False
    
    # Получаем статус, из которого была архивирована задача (если колонка существует)
    original_status = 'new'
    if db._check_column_exists('tasks', 'archived_from_status'):
        result = db.execute_query("SELECT archived_from_status FROM tasks WHERE id = ? AND archived = 1", (task_id,), fetchone=True)
        if result and result[0]:
            original_status = result[0]
    
    # Восстанавливаем задачу (с проверкой наличия колонок)
    if db._check_column_exists('tasks', 'archived_from_status') and db._check_column_exists('tasks', 'archived_at'):
        db.execute_query("""
            UPDATE tasks 
            SET archived = 0, 
                archived_at = NULL,
                archived_from_status = NULL,
                status = ?
            WHERE id = ?
        """, (original_status, task_id))
    elif db._check_column_exists('tasks', 'archived_at'):
        db.execute_query("""
            UPDATE tasks 
            SET archived = 0, 
                archived_at = NULL,
                status = ?
            WHERE id = ?
        """, (original_status, task_id))
    else:
        # Самая старая БД - только archived
        db.execute_query("""
            UPDATE tasks 
            SET archived = 0,
                status = ?
            WHERE id = ?
        """, (original_status, task_id))
    
    # Очищаем кэш тегов при изменении задач
    _get_cached_tags.cache_clear()
    
    return True

# Получить архивированные задачи
def get_archived_tasks():
    """Получает архивированные задачи с комментариями"""
    db = get_db_manager()
    
    # Проверяем наличие колонки archived для обратной совместимости
    if not db._check_column_exists('tasks', 'archived'):
        logger.warning("Колонка 'archived' отсутствует. Архив недоступен для старых БД.", "MIGRATION")
        return []
    
    # Проверяем наличие колонки archived_at для сортировки
    if db._check_column_exists('tasks', 'archived_at'):
        tasks = db.execute_query("""
            SELECT 
                t.*,
                GROUP_CONCAT(tc.comment, ' ') as comments
            FROM tasks t 
            LEFT JOIN task_comments tc ON t.id = tc.task_id
            WHERE t.archived = 1 
            GROUP BY t.id
            ORDER BY t.archived_at DESC
        """, fetch=True)
    else:
        # Старая БД без archived_at - сортируем по created_at
        tasks = db.execute_query("""
            SELECT 
                t.*,
                GROUP_CONCAT(tc.comment, ' ') as comments
            FROM tasks t 
            LEFT JOIN task_comments tc ON t.id = tc.task_id
            WHERE t.archived = 1 
            GROUP BY t.id
            ORDER BY t.created_at DESC
        """, fetch=True)
    return tasks

@app.route('/')
@require_auth
def index():
    mode = request.args.get('mode', 'kanban')
    logger.http(f"Запрос главной страницы, режим: {mode}", "HTTP_GET")
    tasks = get_tasks_by_mode_with_comments(mode)
    cfg = load_config()
    logger.info(f"Загружено {len(tasks)} задач для режима '{mode}'", "PAGE_LOAD")
    return render_template('index.html', tasks=tasks, current_mode=mode, cfg=cfg)

@app.route('/task/<int:task_id>')
@require_auth
def view_task(task_id):
    logger.http(f"Запрос деталей задачи ID {task_id}", "HTTP_GET")
    task, comments = get_task_with_comments(task_id)
    if not task:
        logger.error(f"Задача ID {task_id} не найдена", "TASK_NOT_FOUND")
        return "Задача не найдена", 404
    cfg = load_config()
    logger.info(f"Загружены детали задачи ID {task_id}, комментариев: {len(comments)}", "TASK_VIEW")
    return render_template('task_detail.html', task=task, comments=comments, cfg=cfg)

@app.route('/archive')
@require_auth
def archive():
    logger.http("Запрос страницы архива", "HTTP_GET")
    tasks = get_archived_tasks()
    cfg = load_config()
    logger.info(f"Загружено {len(tasks)} архивированных задач", "ARCHIVE_VIEW")
    return render_template('archive.html', tasks=tasks, cfg=cfg)

@app.route('/add_task', methods=['POST'])
@limiter.limit("10 per minute")
@require_auth
def add_task_route():
    logger.http("Запрос создания новой задачи", "HTTP_POST")
    
    title = request.form['title']
    short_description = request.form.get('short_description', '')
    full_description = request.form.get('full_description', '')
    status = request.form.get('status', 'new')
    priority = request.form.get('priority', 'medium')
    eisenhower_priority = request.form.get('eisenhower_priority', 'not_urgent_not_important')
    assigned_to = request.form.get('assigned_to', '')
    related_threads = request.form.get('related_threads', '')
    tags = request.form.get('tags', '')
    scheduled_date = request.form.get('scheduled_date', '')
    due_date = request.form.get('due_date', '')
    reminder_time = request.form.get('reminder_time', '')
    
    # Отладочная информация
    logger.form(f"related_threads = '{related_threads}'", "FORM_DATA")
    logger.form(f"assigned_to = '{assigned_to}'", "FORM_DATA")
    logger.form(f"scheduled_date = '{scheduled_date}'", "FORM_DATA")
    logger.form(f"due_date = '{due_date}'", "FORM_DATA")
    logger.form(f"reminder_time = '{reminder_time}'", "FORM_DATA")
    
    add_task(title, short_description, full_description, status, priority, eisenhower_priority,
             assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags)
    return redirect(url_for('index'))

@app.route('/update_task/<int:task_id>', methods=['POST'])
@limiter.limit("20 per minute")
@require_auth
def update_task_route(task_id):
    logger.http(f"Запрос обновления задачи ID {task_id}", "HTTP_POST")
    
    title = request.form['title']
    short_description = request.form.get('short_description', '')
    full_description = request.form.get('full_description', '')
    status = request.form.get('status', 'new')
    priority = request.form.get('priority', 'medium')
    eisenhower_priority = request.form.get('eisenhower_priority', 'not_urgent_not_important')
    assigned_to = request.form.get('assigned_to', '')
    related_threads = request.form.get('related_threads', '')
    tags = request.form.get('tags', '')
    scheduled_date = request.form.get('scheduled_date', '')
    due_date = request.form.get('due_date', '')
    reminder_time = request.form.get('reminder_time', '')
    
    # Отладочная информация
    logger.form(f"UPDATE - reminder_time = '{reminder_time}'", "FORM_DATA")
    logger.form(f"UPDATE - scheduled_date = '{scheduled_date}'", "FORM_DATA")
    logger.form(f"UPDATE - due_date = '{due_date}'", "FORM_DATA")
    
    update_task(task_id, title, short_description, full_description, status, priority,
                eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date, reminder_time, tags)
    return redirect(url_for('view_task', task_id=task_id))

@app.route('/add_comment/<int:task_id>', methods=['POST'])
@limiter.limit("30 per minute")
@require_auth
def add_comment_route(task_id):
    logger.http(f"Запрос добавления комментария к задаче ID {task_id}", "HTTP_POST")
    
    comment = request.form.get('comment', '').strip()
    if not comment:
        logger.warning(f"Пустой комментарий для задачи ID {task_id}", "EMPTY_COMMENT")
        return redirect(url_for('view_task', task_id=task_id, open_edit=1))
    
    # Валидируем Markdown
    is_valid, error_msg = validate_markdown(comment)
    if not is_valid:
        logger.warning(f"Невалидный Markdown в комментарии для задачи ID {task_id}: {error_msg}", "INVALID_MARKDOWN")
        return redirect(url_for('view_task', task_id=task_id, open_edit=1))
    
    # Конвертируем Markdown в HTML
    comment_html = markdown_to_html(comment)
    
    # Сохраняем оригинальный Markdown текст
    add_comment(task_id, comment)
    logger.success(f"Комментарий добавлен к задаче ID {task_id}", "COMMENT_ADD")
    # После добавления комментария раскрываем блок редактирования
    return redirect(url_for('view_task', task_id=task_id, open_edit=1))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """Страница входа в систему"""
    auth = get_auth()
    
    # Если аутентификация отключена, перенаправляем на главную
    if not auth.users:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if auth.check_auth(username, password):
            session['authenticated'] = True
            session['username'] = username
            logger.info(f"Пользователь {username} вошел в систему", "AUTH")
            return redirect(url_for('index'))
        else:
            logger.warning(f"Неудачная попытка входа: {username}", "AUTH")
            return render_template('login.html', error="Неверное имя пользователя или пароль")
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Выход из системы"""
    auth = get_auth()
    auth.logout()
    return redirect(url_for('login'))

@app.route('/markdown_preview', methods=['POST'])
@limiter.limit("60 per minute")
def markdown_preview_route():
    """API для предпросмотра Markdown"""
    try:
        markdown_text = request.json.get('markdown', '')
        
        # Валидируем Markdown
        is_valid, error_msg = validate_markdown(markdown_text)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg,
                'html': ''
            })
        
        # Конвертируем в HTML
        html = markdown_to_html(markdown_text)
        
        return jsonify({
            'success': True,
            'html': html,
            'error': ''
        })
        
    except Exception as e:
        logger.error(f"Ошибка предпросмотра Markdown: {e}", "MARKDOWN_PREVIEW")
        return jsonify({
            'success': False,
            'error': str(e),
            'html': ''
        })

@app.route('/delete_task/<int:task_id>')
def delete_task_route(task_id):
    logger.http(f"Запрос удаления задачи ID {task_id}", "HTTP_GET")
    logger.task(f"Удаление задачи ID {task_id}", "DELETE")
    delete_task(task_id)
    logger.success(f"Задача ID {task_id} успешно удалена", "DELETE")
    return redirect(url_for('index'))

@app.route('/archive_task/<int:task_id>')
def archive_task_route(task_id):
    logger.http(f"Запрос архивирования задачи ID {task_id}", "HTTP_GET")
    logger.task(f"Архивирование задачи ID {task_id}", "ARCHIVE")
    if archive_task(task_id):
        logger.success(f"Задача ID {task_id} успешно архивирована", "ARCHIVE")
    else:
        logger.error(f"Ошибка архивирования задачи ID {task_id}", "ARCHIVE")
    return redirect(url_for('index'))

@app.route('/restore_task/<int:task_id>')
def restore_task_route(task_id):
    logger.http(f"Запрос восстановления задачи ID {task_id}", "HTTP_GET")
    logger.task(f"Восстановление задачи ID {task_id}", "RESTORE")
    if restore_task(task_id):
        logger.success(f"Задача ID {task_id} успешно восстановлена", "RESTORE")
    else:
        logger.error(f"Ошибка восстановления задачи ID {task_id}", "RESTORE")
    return redirect(url_for('archive'))

@app.route('/mark_done/<int:task_id>')
def mark_done_route(task_id):
    """Отметить задачу как выполненную"""
    logger.http(f"Запрос отметки задачи ID {task_id} как выполненной", "HTTP_GET")
    logger.task(f"Отметка задачи ID {task_id} как выполненной", "MARK_DONE")

    db = get_db_manager()
    db.execute_query("""
        UPDATE tasks SET 
            status = 'done',
            completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (task_id,))

    logger.success(f"Задача ID {task_id} отмечена как выполненная", "MARK_DONE")
    return redirect(url_for('view_task', task_id=task_id))


@app.route('/mark_cancel/<int:task_id>')
def mark_cancel_route(task_id):
    """Отметить задачу как отменённую"""
    logger.http(f"Запрос отметки задачи ID {task_id} как отменённой", "HTTP_GET")
    logger.task(f"Отметка задачи ID {task_id} как отменённой", "MARK_CANCEL")

    db = get_db_manager()
    db.execute_query("""
        UPDATE tasks SET 
            status = 'cancelled',
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (task_id,))

    logger.success(f"Задача ID {task_id} отмечена как отменённая", "MARK_CANCEL")
    return redirect(url_for('view_task', task_id=task_id))

@app.route('/update_task_status', methods=['POST'])
@limiter.limit("30 per minute")
def update_task_status():
    """API endpoint для обновления статуса задачи через drag&drop"""
    logger.http("API запрос обновления статуса задачи", "API_POST")
    
    data = request.get_json()
    task_id = data.get('task_id')
    new_status = data.get('status')
    
    if not task_id or not new_status:
        logger.error(f"Неверные данные API: task_id={task_id}, status={new_status}", "API_ERROR")
        return {'success': False, 'error': 'Missing task_id or status'}, 400
    
    logger.task(f"Обновление статуса задачи ID {task_id} на '{new_status}'", "STATUS_UPDATE")
    
    db = get_db_manager()
    
    # Обновляем только статус задачи
    db.execute_query("""
        UPDATE tasks SET 
            status = ?, 
            updated_at = CURRENT_TIMESTAMP,
            completed_at = CASE 
                WHEN ? = 'done' AND (completed_at IS NULL OR completed_at = '') THEN CURRENT_TIMESTAMP 
                ELSE completed_at 
            END
        WHERE id = ?
    """, (new_status, new_status, task_id))
    
    # Очищаем кэш тегов при изменении задач (на случай если изменились теги)
    _get_cached_tags.cache_clear()
    
    logger.success(f"Статус задачи ID {task_id} обновлен на '{new_status}'", "STATUS_UPDATE")
    return {'success': True}


@app.route('/api/update_priority', methods=['POST'])
@limiter.limit("30 per minute")
def api_update_priority():
    """API endpoint для обновления приоритета задачи"""
    logger.http("API запрос обновления приоритета задачи", "API_POST")

    data = request.get_json()
    task_id = data.get('task_id')
    new_priority = data.get('priority')

    if not task_id or new_priority not in ('low', 'medium', 'high'):
        logger.error(f"Неверные данные API: task_id={task_id}, priority={new_priority}", "API_ERROR")
        return {'success': False, 'error': 'Missing or invalid task_id/priority'}, 400

    db = get_db_manager()
    db.execute_query("""
        UPDATE tasks SET 
            priority = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_priority, task_id))

    _get_cached_tags.cache_clear()

    logger.success(f"Приоритет задачи ID {task_id} обновлён на '{new_priority}'", "PRIORITY_UPDATE")
    return {'success': True}


@app.route('/api/update_eisenhower', methods=['POST'])
@limiter.limit("30 per minute")
def api_update_eisenhower():
    """API endpoint для обновления категории Эйзенхауэра"""
    logger.http("API запрос обновления категории Эйзенхауэра", "API_POST")

    data = request.get_json()
    task_id = data.get('task_id')
    new_eisenhower = data.get('eisenhower')

    allowed = {
        'urgent_important',
        'urgent_not_important',
        'not_urgent_important',
        'not_urgent_not_important',
    }
    if not task_id or new_eisenhower not in allowed:
        logger.error(f"Неверные данные API: task_id={task_id}, eisenhower={new_eisenhower}", "API_ERROR")
        return {'success': False, 'error': 'Missing or invalid task_id/eisenhower'}, 400

    db = get_db_manager()
    db.execute_query("""
        UPDATE tasks SET 
            eisenhower_priority = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_eisenhower, task_id))

    _get_cached_tags.cache_clear()

    logger.success(f"Категория Эйзенхауэра задачи ID {task_id} обновлена на '{new_eisenhower}'", "EISENHOWER_UPDATE")
    return {'success': True}

@lru_cache(maxsize=128)
def _get_cached_tags():
    """
    Получает теги из БД с кэшированием
    Кэш очищается при изменении задач
    """
    db = get_db_manager()
    tags_data = db.execute_query("""
        SELECT tags, COUNT(*) as count 
        FROM tasks 
        WHERE tags IS NOT NULL AND tags != '' 
        GROUP BY tags
        ORDER BY count DESC, tags ASC
    """, fetch=True)
    return tags_data

@app.route('/api/tags')
def get_tags():
    """API для получения всех тегов с количеством задач"""
    logger.http("API запрос получения тегов", "API_GET")
    
    # Используем кэшированные теги
    tags_data = _get_cached_tags()
    
    # Парсим теги и создаем список уникальных тегов с количеством
    tag_counts = {}
    for tags_string, count in tags_data:
        if tags_string:
            # Разбиваем теги по пробелам и очищаем от # если нужно
            tags = [tag.strip() for tag in tags_string.split() if tag.strip()]
            for tag in tags:
                # Убираем # из начала если есть
                clean_tag = tag[1:] if tag.startswith('#') else tag
                if clean_tag not in tag_counts:
                    tag_counts[clean_tag] = 0
                tag_counts[clean_tag] += count
    
    # Сортируем по количеству, затем по алфавиту
    sorted_tags = sorted(tag_counts.items(), key=lambda x: (-x[1], x[0]))
    
    logger.info(f"Возвращено {len(sorted_tags)} уникальных тегов", "API_TAGS")
    return {'tags': [{'tag': tag, 'count': count} for tag, count in sorted_tags]}

@app.route('/test_api')
def test_api_page():
    return app.send_static_file('test_api.html')

@app.route('/migrate_tasks', methods=['POST'])
@limiter.limit("5 per minute")
@require_auth
def migrate_tasks():
    """Ручной запуск миграции задач"""
    try:
        from category_migration_manager import get_migration_manager
        migration_manager = get_migration_manager()
        
        # Запускаем миграцию в отдельном потоке
        result = {'status': 'started', 'message': 'Миграция запущена'}
        migration_manager.migrate_tasks_async()
        
        return jsonify(result), 202  # 202 Accepted - запрос принят, обработка началась
    except Exception as e:
        logger.error(f"Ошибка при запуске миграции: {e}", "MIGRATION")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/migrate_tasks_status', methods=['GET'])
@require_auth
def migrate_tasks_status():
    """Получить статус последней миграции (для будущего использования)"""
    # Пока просто возвращаем успешный статус
    # В будущем можно добавить отслеживание статуса миграции
    return jsonify({'status': 'completed', 'message': 'Миграция выполнена'}), 200

if __name__ == '__main__':
    logger.info("Запуск ToDoLite приложения", "STARTUP")
    logger.database("Инициализация базы данных", "DB_INIT")
    init_db()
    logger.success("База данных инициализирована", "DB_INIT")
    
    # Запускаем менеджер миграции категорий
    try:
        from category_migration_manager import get_migration_manager
        migration_manager = get_migration_manager()
        migration_manager.start_scheduler()
        logger.success("Менеджер миграции категорий запущен", "MIGRATION")
    except Exception as e:
        logger.error(f"Ошибка запуска менеджера миграции категорий: {e}", "MIGRATION")
    
    logger.http("Запуск Flask сервера на http://0.0.0.0:5000", "SERVER_START")
    app.run(debug=True, host='0.0.0.0', port=5000)
