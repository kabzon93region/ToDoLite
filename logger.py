"""
Простая система логирования с цветным выводом
"""
import sys
from datetime import datetime
from typing import Optional

class Colors:
    """ANSI цветовые коды"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Цвета текста
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Яркие цвета
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

class Logger:
    """Простой логгер с цветным выводом"""
    
    def __init__(self, name: str = "ToDoLite"):
        self.name = name
        self.colors = {
            'DEBUG': Colors.DIM + Colors.WHITE,
            'INFO': Colors.BRIGHT_CYAN,
            'SUCCESS': Colors.BRIGHT_GREEN,
            'WARNING': Colors.BRIGHT_YELLOW,
            'ERROR': Colors.BRIGHT_RED,
            'CRITICAL': Colors.BOLD + Colors.BRIGHT_RED,
            'TASK': Colors.BRIGHT_MAGENTA,
            'DATABASE': Colors.BRIGHT_BLUE,
            'HTTP': Colors.CYAN,
            'FORM': Colors.YELLOW
        }
    
    def _format_message(self, level: str, message: str, tag: Optional[str] = None) -> str:
        """Форматирует сообщение с цветами и временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self.colors.get(level, Colors.WHITE)
        
        if tag:
            tag_part = f"[{Colors.BOLD}{Colors.WHITE}{tag}{Colors.RESET}] "
        else:
            tag_part = ""
        
        level_part = f"{color}{level:8}{Colors.RESET}"
        time_part = f"{Colors.DIM}{timestamp}{Colors.RESET}"
        
        return f"{time_part} {level_part} {tag_part}{message}"
    
    def debug(self, message: str, tag: Optional[str] = None):
        """Отладочное сообщение"""
        print(self._format_message("DEBUG", message, tag))
    
    def info(self, message: str, tag: Optional[str] = None):
        """Информационное сообщение"""
        print(self._format_message("INFO", message, tag))
    
    def success(self, message: str, tag: Optional[str] = None):
        """Сообщение об успехе"""
        print(self._format_message("SUCCESS", message, tag))
    
    def warning(self, message: str, tag: Optional[str] = None):
        """Предупреждение"""
        print(self._format_message("WARNING", message, tag))
    
    def error(self, message: str, tag: Optional[str] = None):
        """Ошибка"""
        print(self._format_message("ERROR", message, tag))
    
    def critical(self, message: str, tag: Optional[str] = None):
        """Критическая ошибка"""
        print(self._format_message("CRITICAL", message, tag))
    
    def task(self, message: str, tag: Optional[str] = None):
        """Сообщение о задаче"""
        print(self._format_message("TASK", message, tag))
    
    def database(self, message: str, tag: Optional[str] = None):
        """Сообщение о базе данных"""
        print(self._format_message("DATABASE", message, tag))
    
    def http(self, message: str, tag: Optional[str] = None):
        """HTTP сообщение"""
        print(self._format_message("HTTP", message, tag))
    
    def form(self, message: str, tag: Optional[str] = None):
        """Сообщение о форме"""
        print(self._format_message("FORM", message, tag))

# Создаем глобальный экземпляр логгера
logger = Logger("ToDoLite")
