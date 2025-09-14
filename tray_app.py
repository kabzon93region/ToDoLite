import sys
import os
import threading
import time
import subprocess
import signal
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import tkinter as tk
from tkinter import scrolledtext
import webbrowser

class TaskManagerTray:
    def __init__(self):
        self.server_process = None
        self.console_window = None
        self.console_text = None
        self.is_console_visible = False
        self.is_server_running = False
        
        # Создаем иконку для трея
        self.icon = self.create_icon()
        
        # Создаем скрытое окно консоли
        self.create_console_window()
        
    def create_icon(self):
        # Создаем простую иконку
        image = Image.new('RGB', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill='white')
        draw.text((20, 25), "📝", fill='black')
        
        # Создаем меню трея
        menu = Menu(
            MenuItem("Показать/скрыть консоль", self.toggle_console),
            MenuItem("Запустить сервер", self.start_server, enabled=lambda item: not self.is_server_running),
            MenuItem("Перезапустить сервер", self.restart_server),
            MenuItem("Остановить сервер", self.stop_server, enabled=lambda item: self.is_server_running),
            Menu.SEPARATOR,
            MenuItem("Открыть в браузере", self.open_browser),
            MenuItem("Выход", self.quit_app)
        )
        
        return Icon("Задачник", image, menu=menu)
    
    def create_console_window(self):
        """Создает скрытое окно консоли"""
        self.console_window = tk.Tk()
        self.console_window.title("Задачник - Консоль")
        self.console_window.geometry("800x600")
        self.console_window.withdraw()  # Скрываем окно
        
        # Создаем текстовое поле для вывода
        self.console_text = scrolledtext.ScrolledText(
            self.console_window, 
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=('Consolas', 10)
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        # Обработчик закрытия окна
        self.console_window.protocol("WM_DELETE_WINDOW", self.hide_console)
    
    def log_message(self, message):
        """Добавляет сообщение в консоль"""
        if self.console_text:
            self.console_text.config(state=tk.NORMAL)
            self.console_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
            self.console_text.see(tk.END)
            self.console_text.config(state=tk.DISABLED)
            self.console_window.update()
    
    def toggle_console(self, icon=None, item=None):
        """Показывает/скрывает консоль"""
        if self.is_console_visible:
            self.hide_console()
        else:
            self.show_console()
    
    def show_console(self):
        """Показывает консоль"""
        if self.console_window:
            self.console_window.deiconify()
            self.console_window.lift()
            self.console_window.focus_force()
            self.is_console_visible = True
            self.log_message("Консоль показана")
    
    def hide_console(self):
        """Скрывает консоль"""
        if self.console_window:
            self.console_window.withdraw()
            self.is_console_visible = False
            self.log_message("Консоль скрыта")
    
    def start_server(self, icon=None, item=None):
        """Запускает сервер"""
        if self.is_server_running:
            self.log_message("Сервер уже запущен")
            return
        
        try:
            self.log_message("Запуск сервера...")
            
            # Запускаем сервер в отдельном процессе
            self.server_process = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.is_server_running = True
            self.log_message("Сервер запущен на http://localhost:5000")
            
            # Запускаем поток для чтения вывода сервера
            threading.Thread(target=self.read_server_output, daemon=True).start()
            
        except Exception as e:
            self.log_message(f"Ошибка запуска сервера: {e}")
    
    def stop_server(self, icon=None, item=None):
        """Останавливает сервер"""
        if not self.is_server_running:
            self.log_message("Сервер не запущен")
            return
        
        try:
            self.log_message("Остановка сервера...")
            
            if self.server_process:
                # Отправляем сигнал завершения
                self.server_process.terminate()
                
                # Ждем завершения процесса
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Принудительно завершаем если не отвечает
                    self.server_process.kill()
                    self.server_process.wait()
                
                self.server_process = None
            
            self.is_server_running = False
            self.log_message("Сервер остановлен")
            
        except Exception as e:
            self.log_message(f"Ошибка остановки сервера: {e}")
    
    def restart_server(self, icon=None, item=None):
        """Перезапускает сервер"""
        self.log_message("Перезапуск сервера...")
        self.stop_server()
        time.sleep(1)  # Небольшая пауза
        self.start_server()
    
    def read_server_output(self):
        """Читает вывод сервера и отображает в консоли"""
        if self.server_process:
            try:
                for line in iter(self.server_process.stdout.readline, ''):
                    if line:
                        self.log_message(line.strip())
            except Exception as e:
                self.log_message(f"Ошибка чтения вывода сервера: {e}")
    
    def open_browser(self, icon=None, item=None):
        """Открывает задачник в браузере"""
        try:
            webbrowser.open("http://localhost:5000")
            self.log_message("Открыт браузер")
        except Exception as e:
            self.log_message(f"Ошибка открытия браузера: {e}")
    
    def quit_app(self, icon=None, item=None):
        """Завершает работу приложения"""
        self.log_message("Завершение работы...")
        
        # Останавливаем сервер если запущен
        if self.is_server_running:
            self.stop_server()
        
        # Закрываем консоль
        if self.console_window:
            self.console_window.quit()
        
        # Останавливаем иконку трея
        self.icon.stop()
    
    def run(self):
        """Запускает приложение"""
        self.log_message("Задачник запущен")
        self.log_message("Используйте правую кнопку мыши на иконке в трее для управления")
        
        # Автоматически запускаем сервер
        self.start_server()
        
        # Запускаем иконку трея
        self.icon.run()

if __name__ == "__main__":
    # Проверяем наличие необходимых библиотек
    try:
        import pystray
        from PIL import Image
    except ImportError:
        print("Установка необходимых библиотек...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow"])
        print("Библиотеки установлены. Перезапустите приложение.")
        sys.exit(1)
    
    # Запускаем приложение
    app = TaskManagerTray()
    app.run()
