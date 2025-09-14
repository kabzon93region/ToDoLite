Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Проверяем существование виртуального окружения
If Not objFSO.FolderExists("ToDoLite_venv") Then
    MsgBox "ОШИБКА: Виртуальное окружение не найдено!" & vbCrLf & "Сначала запустите setup_env.cmd для создания окружения", vbCritical, "Ошибка"
    WScript.Quit
End If

' Запускаем bat файл скрыто
objShell.Run "run_tray_console.bat", 0, False
