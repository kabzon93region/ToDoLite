#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows уведомления для ToDoLite с несколькими бэкендами:
- plyer.notification (если установлен)
- pystray Icon.notify (если иконка трея доступна)
- winrt (если установлен)
- PowerShell BalloonTip (fallback)
"""

import subprocess
from typing import Optional
import sys
import os
import ctypes
from ctypes import wintypes

_tray_icon = None  # type: Optional[object]
_app_id_set = False
_app_id = "ToDoLite.ToDoLite"

def register_tray_icon(icon_obj):
    """Регистрирует иконку трея для нативных уведомлений через pystray."""
    global _tray_icon
    _tray_icon = icon_obj

def set_app_id(app_id: Optional[str] = None):
    """Устанавливает AppUserModelID для текущего процесса (Windows 7+)."""
    global _app_id_set, _app_id
    if _app_id_set:
        return
    try:
        if app_id:
            _app_id = app_id
        shell32 = ctypes.WinDLL('shell32', use_last_error=True)
        SetCurrentProcessExplicitAppUserModelID = shell32.SetCurrentProcessExplicitAppUserModelID
        SetCurrentProcessExplicitAppUserModelID.argtypes = [wintypes.LPCWSTR]
        SetCurrentProcessExplicitAppUserModelID.restype = wintypes.HRESULT
        hr = SetCurrentProcessExplicitAppUserModelID(_app_id)
        if hr == 0:
            _app_id_set = True
    except Exception as e:
        # Игнорируем ошибки установки AppUserModelID - не критично
        pass

def notify(title: str, message: str):
    """Показывает уведомление Windows, предпочитая нативные способы."""
    # Устанавливаем AppUserModelID процесса (попытка привязать уведомление к приложению)
    set_app_id()
    # 0) Пытаемся через plyer (кроссплатформенный интерфейс)
    try:
        from plyer import notification as _plyer_notification
        _plyer_notification.notify(title=title, message=message, app_name="ToDoLite")
        return
    except Exception as e:
        # plyer недоступен, пробуем следующий способ
        pass
    # 1) Пытаемся через pystray Icon.notify
    try:
        if _tray_icon is not None and hasattr(_tray_icon, 'notify'):
            _tray_icon.notify(message, title)
            return
    except Exception as e:
        # pystray недоступен, пробуем следующий способ
        pass

    # 2) Пытаемся через winrt (если установлен)
    try:
        # Ленивая загрузка, чтобы не требовать зависимости
        import winrt.windows.ui.notifications as notifications
        import winrt.windows.data.xml.dom as dom

        # Простой Toast
        t = f"""
        <toast>
          <visual>
            <binding template='ToastGeneric'>
              <text>{title}</text>
              <text>{message}</text>
            </binding>
          </visual>
        </toast>
        """
        xml = dom.XmlDocument()
        xml.load_xml(t)
        # Используем AppUserModelID процесса для группировки уведомлений как от нашего приложения
        notifier = notifications.ToastNotificationManager.create_toast_notifier(_app_id)
        notification = notifications.ToastNotification(xml)
        notifier.show(notification)
        return
    except Exception as e:
        # winrt недоступен, пробуем PowerShell
        pass

    # 3) Fallback: PowerShell BalloonTip (EncodedCommand для корректной Unicode-передачи)
    try:
        def _ps_escape(text: str) -> str:
            return str(text).replace('`', '``').replace('"', '`"')

        ps_title = _ps_escape(title)
        ps_message = _ps_escape(message)
        ps_script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$ni = New-Object System.Windows.Forms.NotifyIcon; "
            "$ni.Icon = [System.Drawing.SystemIcons]::Information; "
            f"$ni.BalloonTipTitle = \"{ps_title}\"; "
            f"$ni.BalloonTipText = \"{ps_message}\"; "
            "$ni.Visible = $true; "
            "$ni.ShowBalloonTip(5000); "
            "Start-Sleep -Seconds 6; "
            "$ni.Dispose();"
        )
        import base64
        # PowerShell ожидает UTF-16LE для -EncodedCommand
        encoded = base64.b64encode(ps_script.encode('utf-16le')).decode('ascii')
        subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded
        ], capture_output=True, text=True, timeout=10)
    except Exception as e:
        # PowerShell уведомление не удалось отправить - не критично
        pass


