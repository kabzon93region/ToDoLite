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
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT 'todo',
                  priority TEXT DEFAULT 'medium',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
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

# Добавить новую задачу
def add_task(title, description, priority):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (title, description, priority) VALUES (?, ?, ?)",
              (title, description, priority))
    conn.commit()
    conn.close()

# Обновить статус задачи
def update_task_status(task_id, new_status):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
              (new_status, task_id))
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
    tasks = get_tasks()
    return render_template('index.html', tasks=tasks)

@app.route('/add_task', methods=['POST'])
def add_task_route():
    title = request.form['title']
    description = request.form['description']
    priority = request.form['priority']
    add_task(title, description, priority)
    return redirect(url_for('index'))

@app.route('/update_status/<int:task_id>/<new_status>')
def update_status(task_id, new_status):
    update_task_status(task_id, new_status)
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>')
def delete_task_route(task_id):
    delete_task(task_id)
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
