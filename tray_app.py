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
from logger import logger
from notifications_windows import register_tray_icon, notify, set_app_id

# Импортируем систему резервного копирования
try:
    from backup_scheduler import start_backup_scheduler, get_backup_scheduler
    from backup_manager import BackupManager
    from export_manager import ExportManager
    from import_manager import ImportManager
    from reminder_manager import start_reminder_scheduler, stop_reminder_scheduler, get_reminder_manager
    BACKUP_AVAILABLE = True
except ImportError as e:
    print(f"ToDoLite: Система резервного копирования недоступна: {e}")
    BACKUP_AVAILABLE = False

# Импортируем менеджер миграции категорий
try:
    from category_migration_manager import get_migration_manager
    MIGRATION_AVAILABLE = True
except ImportError as e:
    print(f"ToDoLite: Система миграции категорий недоступна: {e}")
    MIGRATION_AVAILABLE = False

class TaskManagerTray:
    def __init__(self):
        self.server_process = None
        self.console_window = None
        self.console_text = None
        self.is_console_visible = False
        self.is_server_running = False
        
        # Инициализируем менеджеры резервного копирования и экспорта/импорта
        if BACKUP_AVAILABLE:
            self.backup_manager = BackupManager()
            self.export_manager = ExportManager()
            self.import_manager = ImportManager()
            self.reminder_manager = get_reminder_manager()
            self.log_message("Система резервного копирования инициализирована")
        else:
            self.backup_manager = None
            self.export_manager = None
            self.import_manager = None
            self.reminder_manager = None
            self.log_message("Система резервного копирования недоступна")
        
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
        menu_items = [
            MenuItem("Открыть в браузере", self.open_browser),
            MenuItem("Показать консоль", self.toggle_console)
        ]
        
        # Добавляем функции резервного копирования если доступны
        if BACKUP_AVAILABLE:
            menu_items.extend([
                Menu.SEPARATOR,
                MenuItem("Создать резервную копию", self.create_backup),
                MenuItem("Экспорт задач", self.export_tasks),
                MenuItem("Импорт задач", self.import_tasks),
                MenuItem("Проверить напоминания", self.check_reminders)
            ])
        
        menu_items.extend([
            Menu.SEPARATOR,
            MenuItem("Остановить и выйти", self.quit_app)
        ])
        
        menu = Menu(*menu_items)
        
        icon = Icon("Задачник", image, menu=menu)
        try:
            register_tray_icon(icon)
        except Exception as e:
            self.log_message(f"Не удалось зарегистрировать иконку трея: {e}")
        return icon
    
    def update_menu(self):
        """Обновляет состояние меню"""
        if hasattr(self, 'icon') and self.icon:
            # Создаем новое меню с актуальным состоянием
            menu_items = [
                MenuItem("Открыть в браузере", self.open_browser),
                MenuItem("Показать консоль", self.toggle_console)
            ]
            
            # Добавляем функции резервного копирования если доступны
            if BACKUP_AVAILABLE:
                menu_items.extend([
                    Menu.SEPARATOR,
                    MenuItem("Создать резервную копию", self.create_backup),
                    MenuItem("Экспорт задач", self.export_tasks),
                    MenuItem("Импорт задач", self.import_tasks),
                    MenuItem("Проверить напоминания", self.check_reminders)
                ])
            
            menu_items.extend([
                Menu.SEPARATOR,
                MenuItem("Остановить и выйти", self.quit_app)
            ])
            
            new_menu = Menu(*menu_items)
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
                    except Exception as e:
                        self.log_message(f"Ошибка завершения сервера: {e}")
                
                self.server_process = None
            
            # Дополнительно завершаем все процессы pythonw.exe
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe', '/T'], 
                             capture_output=True, timeout=5)
                self.log_message("Завершены все процессы pythonw.exe")
            except Exception as e:
                self.log_message(f"Ошибка завершения процессов pythonw.exe: {e}")
            
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
    
    def create_backup(self, icon=None, item=None):
        """Создает резервную копию базы данных"""
        if not BACKUP_AVAILABLE or not self.backup_manager:
            self.log_message("Система резервного копирования недоступна")
            return
        
        try:
            self.log_message("Создание резервной копии...")
            backup_path = self.backup_manager.create_backup()
            if backup_path:
                self.log_message(f"Резервная копия создана: {backup_path}")
            else:
                self.log_message("Не удалось создать резервную копию")
        except Exception as e:
            self.log_message(f"Ошибка создания резервной копии: {e}")
    
    def export_tasks(self, icon=None, item=None):
        """Экспортирует задачи в JSON формат"""
        if not BACKUP_AVAILABLE or not self.export_manager:
            self.log_message("Система экспорта недоступна")
            return
        
        try:
            self.log_message("Экспорт задач...")
            export_path = self.export_manager.export_tasks(format='json')
            if export_path:
                self.log_message(f"Задачи экспортированы: {export_path}")
            else:
                self.log_message("Не удалось экспортировать задачи")
        except Exception as e:
            self.log_message(f"Ошибка экспорта задач: {e}")
    
    def import_tasks(self, icon=None, item=None):
        """Импортирует задачи из файла"""
        if not BACKUP_AVAILABLE or not self.import_manager:
            self.log_message("Система импорта недоступна")
            return
        
        try:
            # Открываем диалог выбора файла
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                title="Выберите файл для импорта",
                filetypes=[
                    ("JSON файлы", "*.json"),
                    ("CSV файлы", "*.csv"),
                    ("XML файлы", "*.xml"),
                    ("Все файлы", "*.*")
                ]
            )
            
            if file_path:
                self.log_message(f"Импорт задач из файла: {file_path}")
                result = self.import_manager.import_tasks(file_path)
                if result['success']:
                    self.log_message(f"Импорт завершен: {result['imported']} импортировано, {result['skipped']} пропущено, {result['errors']} ошибок")
                else:
                    self.log_message(f"Ошибка импорта: {result.get('error', 'Неизвестная ошибка')}")
            else:
                self.log_message("Импорт отменен")
        except Exception as e:
            self.log_message(f"Ошибка импорта задач: {e}")
    
    def check_reminders(self, icon=None, item=None):
        """Проверяет напоминания о задачах"""
        if not BACKUP_AVAILABLE or not self.reminder_manager:
            self.log_message("Система напоминаний недоступна")
            return
        
        try:
            self.log_message("Проверка напоминаний...")
            self.reminder_manager.force_check()
            self.log_message("Проверка напоминаний завершена")
        except Exception as e:
            self.log_message(f"Ошибка проверки напоминаний: {e}")
    
    def quit_app(self, icon=None, item=None):
        """Завершает работу приложения"""
        self.log_message("Завершение работы...")
        
        # Останавливаем планировщик резервного копирования
        if BACKUP_AVAILABLE:
            try:
                from backup_scheduler import stop_backup_scheduler
                stop_backup_scheduler()
                self.log_message("Планировщик резервного копирования остановлен")
            except Exception as e:
                self.log_message(f"Ошибка остановки планировщика резервного копирования: {e}")
            
            # Останавливаем планировщик напоминаний
            try:
                stop_reminder_scheduler()
                self.log_message("Планировщик напоминаний остановлен")
            except Exception as e:
                self.log_message(f"Ошибка остановки планировщика напоминаний: {e}")
        
        # Останавливаем менеджер миграции категорий
        if MIGRATION_AVAILABLE:
            try:
                migration_manager = get_migration_manager()
                migration_manager.stop_scheduler()
                self.log_message("Менеджер миграции категорий остановлен")
            except Exception as e:
                self.log_message(f"Ошибка остановки менеджера миграции категорий: {e}")
        
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
                except Exception as e:
                    self.log_message(f"Ошибка завершения сервера при выходе: {e}")
        
        # Дополнительно завершаем все процессы pythonw.exe
        try:
            import subprocess
            subprocess.run(['taskkill', '/F', '/IM', 'pythonw.exe', '/T'], 
                         capture_output=True, timeout=3)
            self.log_message("Завершены все процессы pythonw.exe")
        except Exception as e:
            self.log_message(f"Ошибка завершения процессов pythonw.exe при выходе: {e}")
        
        # Закрываем консоль
        if self.console_window:
            try:
                self.console_window.quit()
            except Exception as e:
                self.log_message(f"Ошибка закрытия консоли: {e}")
        
        # Останавливаем иконку трея
        try:
            self.icon.stop()
        except Exception as e:
            self.log_message(f"Ошибка остановки иконки трея: {e}")
        
        # Принудительно завершаем текущий процесс
        import os
        os._exit(0)
    
    def run(self):
        """Запускает приложение"""
        self.log_message("Задачник запущен")
        self.log_message("Используйте правую кнопку мыши на иконке в трее для управления")
        
        # Устанавливаем AppUserModelID, чтобы уведомления помечались нашим приложением
        try:
            set_app_id("ToDoLite.ToDoLite")
        except Exception as e:
            self.log_message(f"Не удалось установить AppUserModelID: {e}")

        # Восстанавливаем БД из свежей копии на старте, если требуется
        if BACKUP_AVAILABLE and self.backup_manager:
            try:
                restored = self.backup_manager.restore_latest_on_start()
                if restored:
                    self.log_message("База данных восстановлена из последней копии")
                else:
                    self.log_message("Восстановление БД на старте не потребовалось")
            except Exception as e:
                self.log_message(f"Ошибка восстановления БД на старте: {e}")

            # Запускаем планировщик резервного копирования
            if BACKUP_AVAILABLE:
                try:
                    start_backup_scheduler()
                    self.log_message("Планировщик резервного копирования запущен")
                except Exception as e:
                    self.log_message(f"Ошибка запуска планировщика резервного копирования: {e}")
                
                # Запускаем планировщик напоминаний
                try:
                    start_reminder_scheduler()
                    self.log_message("Планировщик напоминаний запущен")
                except Exception as e:
                    self.log_message(f"Ошибка запуска планировщика напоминаний: {e}")
            
            # Запускаем менеджер миграции категорий
            if MIGRATION_AVAILABLE:
                try:
                    migration_manager = get_migration_manager()
                    migration_manager.start_scheduler()
                    self.log_message("Менеджер миграции категорий запущен")
                except Exception as e:
                    self.log_message(f"Ошибка запуска менеджера миграции категорий: {e}")
        
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
        logger.warning("Установка необходимых библиотек...", "DEPENDENCIES")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pystray", "Pillow"])
        logger.success("Библиотеки установлены. Перезапустите приложение.", "DEPENDENCIES")
        sys.exit(1)
    
    # Запускаем приложение
    app = TaskManagerTray()
    app.run()
