# 🚀 Быстрая публикация ToDoLite v1.4

## 📋 Пошаговая инструкция

### 1. Подготовка Git
```bash
# Проверьте статус
git status

# Добавьте все изменения
git add .

# Создайте коммит
git commit -m "feat: Add archive system for tasks (v1.4)

- Add task archiving functionality
- Add archive protection (no editing)
- Add task restoration from archive
- Rename Kanban to Agile mode
- Add archive statistics
- Add automatic database migration"
```

### 2. Создание тега
```bash
# Создайте тег версии
git tag -a v1.4 -m "ToDoLite v1.4 - Archive System"

# Отправьте тег на GitHub
git push origin v1.4
```

### 3. Публикация на GitHub
1. **Перейдите:** https://github.com/ваш-username/ToDoLite/releases
2. **Нажмите:** "Create a new release"
3. **Выберите тег:** v1.4
4. **Заголовок:** `ToDoLite v1.4 - Archive System`
5. **Описание:** Скопируйте из файла `release_v1.4/GITHUB_RELEASE_v1.4.md`
6. **Настройки:**
   - ✅ Set as the latest release
   - ❌ Generate release notes (не используйте)
7. **Нажмите:** "Publish release"

## 📝 Готовое описание для GitHub

```markdown
# ToDoLite v1.4 - Archive System

## 🎉 Major Features

### 📦 Archive System
- **Archive completed/cancelled tasks** - Keep your main list clean
- **Restore archived tasks** - Bring tasks back to their original status
- **Archive protection** - Prevent accidental editing of archived tasks
- **Archive statistics** - Track archived tasks by status

### 🔒 Security & Reliability
- **Edit protection** - Archived tasks cannot be modified
- **Status preservation** - Original status is saved and restored
- **Comment support** - Add notes to archived tasks

### 🎨 UI Improvements
- **Archive button** - Easy access in mode switcher
- **Visual feedback** - Clear messages about edit restrictions
- **Agile mode** - Renamed from "Kanban" for terminology accuracy

## 🚀 How to Use

### Archiving Tasks
1. Complete a task (status "Done" or "Cancelled")
2. Click "📦 Archive" button in task card
3. Task disappears from main list and appears in archive

### Restoring Tasks
1. Go to "📦 Archive"
2. Find the task you need
3. Click "🔄 Restore"
4. Task returns to its original status

## 🔄 Backward Compatibility
- ✅ All existing tasks preserved
- ✅ Automatic database migration
- ✅ All settings and comments preserved
- ✅ Seamless upgrade from v1.1

## 🗄️ Database Changes
New fields added:
- `archived` - Archive flag (BOOLEAN)
- `archived_at` - Archive timestamp (TIMESTAMP)  
- `archived_from_status` - Original status before archiving (TEXT)

---

**Version:** v1.4  
**Date:** September 19, 2025  
**Compatibility:** Windows 10/11, Python 3.8+
```

## ✅ Проверка после публикации

1. ✅ Релиз отображается на странице releases
2. ✅ Тег v1.4 создан
3. ✅ Описание корректно отображается
4. ✅ Все ссылки работают
5. ✅ README.md обновлен с версией 1.4

## 🎯 Готово!

Релиз v1.4 опубликован! 🎉

---

**Время выполнения:** ~5 минут  
**Сложность:** Простая  
**Требования:** Git, GitHub аккаунт
