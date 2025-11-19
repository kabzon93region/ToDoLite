#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ToDoLite - Утилиты для работы с Markdown
"""

import markdown
import re
from logger import logger

class MarkdownProcessor:
    """
    Обработчик Markdown для ToDoLite
    """
    
    def __init__(self):
        # Настройки Markdown с расширениями
        self.md_extensions = [
            'markdown.extensions.extra',      # Таблицы, определения, атрибуты
            'markdown.extensions.codehilite', # Подсветка синтаксиса кода
            'markdown.extensions.fenced_code', # Блоки кода с заборчиками
            'markdown.extensions.tables',     # Таблицы
            'markdown.extensions.toc',        # Оглавление
            'markdown.extensions.sane_lists', # Улучшенные списки
            'markdown.extensions.nl2br',      # Одинарные переносы строк
        ]
        
        # Настройки для подсветки кода
        self.md_extension_configs = {
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'use_pygments': False,  # Отключаем pygments для простоты
            },
            'markdown.extensions.toc': {
                'permalink': False,  # Отключаем якорные ссылки
            }
        }
        
        # Создаем экземпляр Markdown
        self.md = markdown.Markdown(
            extensions=self.md_extensions,
            extension_configs=self.md_extension_configs
        )
        
        logger.info("MarkdownProcessor инициализирован", "MARKDOWN")
    
    def to_html(self, markdown_text):
        """
        Конвертирует Markdown в HTML
        
        Args:
            markdown_text (str): Текст в формате Markdown
            
        Returns:
            str: HTML код
        """
        try:
            if not markdown_text:
                return ""
            
            # Обрабатываем зачёркивание (~~текст~~) перед парсингом
            markdown_text = self._process_strikethrough(markdown_text)
            
            # Обрабатываем горизонтальные линии (---, ***, ___) перед парсингом
            markdown_text = self._process_horizontal_rules(markdown_text)
            
            # Сбрасываем состояние парсера
            self.md.reset()
            
            # Конвертируем Markdown в HTML
            html = self.md.convert(markdown_text)
            
            # Дополнительная обработка для безопасности
            html = self._sanitize_html(html)
            
            return html
            
        except Exception as e:
            logger.error(f"Ошибка конвертации Markdown в HTML: {e}", "MARKDOWN")
            # Возвращаем исходный текст как есть
            return self._escape_html(markdown_text)
    
    def _process_strikethrough(self, text):
        """
        Обрабатывает зачёркивание ~~текст~~ -> <del>текст</del>
        Избегает обработки внутри блоков кода
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Текст с обработанным зачёркиванием
        """
        # Защищаем блоки кода от обработки
        code_blocks = []
        placeholders = []
        
        # Заменяем блоки кода на плейсхолдеры
        def replace_code_block(match):
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            placeholders.append(placeholder)
            return placeholder
        
        # Защищаем блоки кода с тройными обратными кавычками
        text = re.sub(r'```[\s\S]*?```', replace_code_block, text)
        # Защищаем инлайн код с одинарными обратными кавычками
        text = re.sub(r'`[^`]+`', replace_code_block, text)
        
        # Обрабатываем зачёркивание: ~~текст~~ -> <del>текст</del>
        # Используем негативный lookbehind и lookahead, чтобы избежать вложенных тильд
        text = re.sub(r'~~([^~]+)~~', r'<del>\1</del>', text)
        
        # Восстанавливаем блоки кода
        for i, placeholder in enumerate(placeholders):
            text = text.replace(placeholder, code_blocks[i])
        
        return text
    
    def _process_horizontal_rules(self, text):
        """
        Обрабатывает горизонтальные линии (---, ***, ___)
        Добавляет пустую строку перед линией, если её нет
        Избегает обработки внутри блоков кода
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Текст с обработанными горизонтальными линиями
        """
        # Защищаем блоки кода от обработки
        code_blocks = []
        placeholders = []
        
        # Заменяем блоки кода на плейсхолдеры
        def replace_code_block(match):
            placeholder = f"__CODE_BLOCK_{len(code_blocks)}__"
            code_blocks.append(match.group(0))
            placeholders.append(placeholder)
            return placeholder
        
        # Защищаем блоки кода с тройными обратными кавычками
        text = re.sub(r'```[\s\S]*?```', replace_code_block, text)
        # Защищаем инлайн код с одинарными обратными кавычками
        text = re.sub(r'`[^`]+`', replace_code_block, text)
        
        # Обрабатываем горизонтальные линии
        # Паттерн: строка, состоящая только из ---, ***, или ___ (минимум 3 символа, возможно с пробелами)
        lines = text.split('\n')
        processed_lines = []
        
        for i, line in enumerate(lines):
            # Проверяем, является ли строка горизонтальной линией
            # Горизонтальная линия: только дефисы, звёздочки или подчёркивания (минимум 3), возможно с пробелами
            stripped = line.strip()
            is_hr = False
            if len(stripped) >= 3:
                if re.match(r'^[-]{3,}$', stripped):  # ---
                    is_hr = True
                elif re.match(r'^[*]{3,}$', stripped):  # ***
                    is_hr = True
                elif re.match(r'^[_]{3,}$', stripped):  # ___
                    is_hr = True
            
            if is_hr:
                # Проверяем предыдущую строку в исходном тексте
                if i > 0:
                    prev_line = lines[i-1]
                    # Если предыдущая строка не пустая, добавляем пустую строку
                    if prev_line.strip():
                        processed_lines.append('')
                # Добавляем саму линию
                processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        text = '\n'.join(processed_lines)
        
        # Восстанавливаем блоки кода
        for i, placeholder in enumerate(placeholders):
            text = text.replace(placeholder, code_blocks[i])
        
        return text
    
    def _sanitize_html(self, html):
        """
        Очищает HTML от потенциально опасных элементов
        
        Args:
            html (str): HTML код
            
        Returns:
            str: Очищенный HTML
        """
        # Разрешенные теги
        allowed_tags = [
            'p', 'br', 'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'ins',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'dl', 'dt', 'dd',
            'blockquote', 'pre', 'code',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'hr', 'div', 'span'
        ]
        
        # Разрешенные атрибуты
        allowed_attrs = {
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'table': ['class'],
            'th': ['class'],
            'td': ['class'],
            'div': ['class'],
            'span': ['class'],
            'code': ['class'],
            'pre': ['class']
        }
        
        # Простая очистка - удаляем потенциально опасные теги
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
            r'<form[^>]*>.*?</form>',
            r'<input[^>]*>',
            r'<button[^>]*>.*?</button>',
            r'on\w+\s*=\s*["\'][^"\']*["\']',  # JavaScript события
        ]
        
        for pattern in dangerous_patterns:
            html = re.sub(pattern, '', html, flags=re.IGNORECASE | re.DOTALL)
        
        return html
    
    def _escape_html(self, text):
        """
        Экранирует HTML символы в тексте
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Экранированный текст
        """
        if not text:
            return ""
        
        # Заменяем HTML символы
        html_escape_table = {
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
            ">": "&gt;",
            "<": "&lt;",
        }
        
        for char, replacement in html_escape_table.items():
            text = text.replace(char, replacement)
        
        # Заменяем переносы строк на <br>
        text = text.replace('\n', '<br>')
        
        return text
    
    def get_preview(self, markdown_text, max_length=500):
        """
        Получает предпросмотр Markdown текста
        
        Args:
            markdown_text (str): Текст в формате Markdown
            max_length (int): Максимальная длина предпросмотра
            
        Returns:
            str: HTML предпросмотр
        """
        try:
            if not markdown_text:
                return ""
            
            # Обрезаем текст для предпросмотра
            preview_text = markdown_text[:max_length]
            if len(markdown_text) > max_length:
                preview_text += "..."
            
            # Конвертируем в HTML
            html = self.to_html(preview_text)
            
            return html
            
        except Exception as e:
            logger.error(f"Ошибка создания предпросмотра: {e}", "MARKDOWN")
            return self._escape_html(markdown_text[:max_length])
    
    def validate_markdown(self, markdown_text):
        """
        Валидирует Markdown текст
        
        Args:
            markdown_text (str): Текст для валидации
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            if not markdown_text:
                return True, "OK"
            
            # Проверяем на потенциально опасные конструкции
            dangerous_patterns = [
                r'<script',
                r'<iframe',
                r'<object',
                r'<embed',
                r'<form',
                r'<input',
                r'<button',
                r'javascript:',
                r'data:text/html',
            ]
            
            for pattern in dangerous_patterns:
                if re.search(pattern, markdown_text, re.IGNORECASE):
                    return False, f"Обнаружена потенциально опасная конструкция: {pattern}"
            
            # Пробуем конвертировать
            self.to_html(markdown_text)
            
            return True, "OK"
            
        except Exception as e:
            return False, f"Ошибка валидации Markdown: {e}"

# Глобальный экземпляр
_markdown_processor = None

def get_markdown_processor():
    """Получение глобального экземпляра MarkdownProcessor"""
    global _markdown_processor
    if _markdown_processor is None:
        _markdown_processor = MarkdownProcessor()
    return _markdown_processor

def markdown_to_html(markdown_text):
    """Конвертирует Markdown в HTML"""
    processor = get_markdown_processor()
    return processor.to_html(markdown_text)

def markdown_preview(markdown_text, max_length=500):
    """Получает предпросмотр Markdown"""
    processor = get_markdown_processor()
    return processor.get_preview(markdown_text, max_length)

def validate_markdown(markdown_text):
    """Валидирует Markdown текст"""
    processor = get_markdown_processor()
    return processor.validate_markdown(markdown_text)
