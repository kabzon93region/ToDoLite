from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
import signal
import sys
from datetime import datetime

app = Flask(__name__)

# Переменная для отслеживания состояния сервера
server_running = True

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global server_running
    print(f"\nПолучен сигнал {signum}. Завершение работы...")
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
            ('due_date', 'DATE')
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
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Создаем таблицу комментариев
    c.execute('''CREATE TABLE IF NOT EXISTS task_comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task_id INTEGER NOT NULL,
                  comment TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE)''')
    
    conn.commit()
    conn.close()

# Получить все задачи
def get_tasks():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = c.fetchall()
    conn.close()
    return tasks

# Получить задачи по режиму отображения
def get_tasks_by_mode(mode):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    if mode == 'eisenhower':
        c.execute("SELECT * FROM tasks ORDER BY eisenhower_priority, due_date ASC")
    elif mode == 'kanban':
        c.execute("SELECT * FROM tasks ORDER BY status, due_date ASC")
    else:
        c.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    
    tasks = c.fetchall()
    conn.close()
    return tasks

# Получить задачу по ID с комментариями
def get_task_with_comments(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    
    # Получаем задачу
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    
    # Получаем комментарии
    c.execute("SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at ASC", (task_id,))
    comments = c.fetchall()
    
    conn.close()
    return task, comments

# Добавить новую задачу
def add_task(title, short_description, full_description, status, priority, eisenhower_priority, 
             assigned_to, related_threads, scheduled_date, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("""INSERT INTO tasks (title, short_description, full_description, status, priority, 
                 eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (title, short_description, full_description, status, priority, eisenhower_priority,
               assigned_to, related_threads, scheduled_date, due_date))
    conn.commit()
    conn.close()

# Обновить задачу
def update_task(task_id, title, short_description, full_description, status, priority, 
                eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("""UPDATE tasks SET title=?, short_description=?, full_description=?, status=?, 
                 priority=?, eisenhower_priority=?, assigned_to=?, related_threads=?, 
                 scheduled_date=?, due_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
              (title, short_description, full_description, status, priority, eisenhower_priority,
               assigned_to, related_threads, scheduled_date, due_date, task_id))
    conn.commit()
    conn.close()

# Добавить комментарий к задаче
def add_comment(task_id, comment):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO task_comments (task_id, comment) VALUES (?, ?)", (task_id, comment))
    conn.commit()
    conn.close()

# Удалить задачу
def delete_task(task_id):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    mode = request.args.get('mode', 'kanban')
    tasks = get_tasks_by_mode(mode)
    return render_template('index.html', tasks=tasks, current_mode=mode)

@app.route('/task/<int:task_id>')
def view_task(task_id):
    task, comments = get_task_with_comments(task_id)
    if not task:
        return "Задача не найдена", 404
    return render_template('task_detail.html', task=task, comments=comments)

@app.route('/add_task', methods=['POST'])
def add_task_route():
    title = request.form['title']
    short_description = request.form.get('short_description', '')
    full_description = request.form.get('full_description', '')
    status = request.form.get('status', 'new')
    priority = request.form.get('priority', 'medium')
    eisenhower_priority = request.form.get('eisenhower_priority', 'not_urgent_not_important')
    assigned_to = request.form.get('assigned_to', '')
    related_threads = request.form.get('related_threads', '')
    scheduled_date = request.form.get('scheduled_date', '')
    due_date = request.form.get('due_date', '')
    
    add_task(title, short_description, full_description, status, priority, eisenhower_priority,
             assigned_to, related_threads, scheduled_date, due_date)
    return redirect(url_for('index'))

@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task_route(task_id):
    title = request.form['title']
    short_description = request.form.get('short_description', '')
    full_description = request.form.get('full_description', '')
    status = request.form.get('status', 'new')
    priority = request.form.get('priority', 'medium')
    eisenhower_priority = request.form.get('eisenhower_priority', 'not_urgent_not_important')
    assigned_to = request.form.get('assigned_to', '')
    related_threads = request.form.get('related_threads', '')
    scheduled_date = request.form.get('scheduled_date', '')
    due_date = request.form.get('due_date', '')
    
    update_task(task_id, title, short_description, full_description, status, priority,
                eisenhower_priority, assigned_to, related_threads, scheduled_date, due_date)
    return redirect(url_for('view_task', task_id=task_id))

@app.route('/add_comment/<int:task_id>', methods=['POST'])
def add_comment_route(task_id):
    comment = request.form['comment']
    add_comment(task_id, comment)
    return redirect(url_for('view_task', task_id=task_id))

@app.route('/delete_task/<int:task_id>')
def delete_task_route(task_id):
    delete_task(task_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
