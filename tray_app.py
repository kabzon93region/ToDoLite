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
        # Используем простой текст вместо эмодзи
        draw.text((25, 25), "TD", fill='black')
        
        # Создаем упрощенное меню трея
        menu = Menu(
            MenuItem("Открыть в браузере", self.open_browser),
            MenuItem("Остановить и выйти", self.quit_app)
        )
        
        return Icon("Задачник", image, menu=menu)
    
    def update_menu(self):
        """Обновляет состояние меню"""
        if hasattr(self, 'icon') and self.icon:
            # Создаем новое меню с актуальным состоянием
            new_menu = Menu(
                MenuItem("Открыть в браузере", self.open_browser),
                MenuItem("Остановить и выйти", self.quit_app)
            )
            self.icon.menu = new_menu
    
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
            # Используем after_idle для безопасного обновления из другого потока
            def update_console():
                try:
                    self.console_text.config(state=tk.NORMAL)
                    self.console_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
                    self.console_text.see(tk.END)
                    self.console_text.config(state=tk.DISABLED)
                except:
                    pass  # Игнорируем ошибки если окно закрыто
            
            self.console_window.after_idle(update_console)
    
    def toggle_console(self, icon=None, item=None):
        """Показывает/скрывает консоль"""
        if self.is_console_visible:
            self.hide_console()
        else:
            self.show_console()
    
    def show_console(self):
        """Показывает консоль"""
        if self.console_window:
            try:
                self.console_window.deiconify()
                self.console_window.lift()
                self.console_window.focus_force()
                self.is_console_visible = True
                self.log_message("Консоль показана")
            except:
                pass  # Игнорируем ошибки если окно недоступно
    
    def hide_console(self):
        """Скрывает консоль"""
        if self.console_window:
            try:
                self.console_window.withdraw()
                self.is_console_visible = False
                self.log_message("Консоль скрыта")
            except:
                pass  # Игнорируем ошибки если окно недоступно
    
    def start_server(self, icon=None, item=None):
        """Запускает сервер"""
        if self.is_server_running:
            self.log_message("Сервер уже запущен")
            return
        
        try:
            self.log_message("Запуск сервера...")
            
            # Запускаем сервер в отдельном процессе без консоли
            self.server_process = subprocess.Popen(
                [sys.executable, "app.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            # Проверяем, что процесс действительно запустился
            if self.server_process.poll() is None:
                self.is_server_running = True
                self.log_message("Сервер запущен на http://localhost:5000")
                self.update_menu()  # Обновляем меню
            else:
                self.log_message("Ошибка: Сервер не запустился")
                self.server_process = None
                self.is_server_running = False
            
        except Exception as e:
            self.log_message(f"Ошибка запуска сервера: {e}")
            self.is_server_running = False
            self.server_process = None
    
    def stop_server(self, icon=None, item=None):
        """Останавливает сервер"""
        if not self.is_server_running:
            self.log_message("Сервер не запущен")
            return
        
        try:
            self.log_message("Остановка сервера...")
            
            if self.server_process:
                # Сначала пытаемся корректно завершить
                try:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Если не отвечает, принудительно завершаем
                    self.log_message("Принудительное завершение сервера...")
                    self.server_process.kill()
                    self.server_process.wait(timeout=2)
                except Exception as e:
                    self.log_message(f"Ошибка при завершении: {e}")
                    # Пытаемся принудительно завершить
                    try:
                        self.server_process.kill()
                        self.server_process.wait(timeout=2)
                    except:
                        pass
                
                self.server_process = None
            
            # Дополнительно завершаем все процессы pythonw.exe
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe', '/T'], 
                             capture_output=True, timeout=5)
                self.log_message("Завершены все процессы pythonw.exe")
            except:
                pass
            
            self.is_server_running = False
            self.log_message("Сервер остановлен")
            self.update_menu()  # Обновляем меню
            
        except Exception as e:
            self.log_message(f"Ошибка остановки сервера: {e}")
            # Сбрасываем состояние даже при ошибке
            self.is_server_running = False
            self.server_process = None
    
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
            self.log_message("Остановка сервера...")
            try:
                if self.server_process:
                    self.server_process.terminate()
                    self.server_process.wait(timeout=2)
            except:
                try:
                    if self.server_process:
                        self.server_process.kill()
                        self.server_process.wait(timeout=1)
                except:
                    pass
        
        # Дополнительно завершаем все процессы pythonw.exe
        try:
            import subprocess
            subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe', '/T'], 
                         capture_output=True, timeout=3)
            self.log_message("Завершены все процессы pythonw.exe")
        except:
            pass
        
        # Закрываем консоль
        if self.console_window:
            try:
                self.console_window.quit()
            except:
                pass
        
        # Останавливаем иконку трея
        try:
            self.icon.stop()
        except:
            pass
        
        # Принудительно завершаем текущий процесс
        import os
        os._exit(0)
    
    def run(self):
        """Запускает приложение"""
        self.log_message("Задачник запущен")
        self.log_message("Используйте правую кнопку мыши на иконке в трее для управления")
        
        # Автоматически запускаем сервер
        self.start_server()
        
        # Проверяем состояние сервера через 2 секунды
        def check_server_status():
            if self.is_server_running and self.server_process:
                if self.server_process.poll() is not None:
                    # Сервер завершился неожиданно
                    self.log_message("Сервер завершился неожиданно")
                    self.is_server_running = False
                    self.server_process = None
                    self.update_menu()
        
        # Запускаем проверку через 2 секунды
        threading.Timer(2.0, check_server_status).start()
        
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
