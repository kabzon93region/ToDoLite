# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).

## [Unreleased]

### Планируется
- Продолжение разработки ветки **v1.6.1-dev** (см. [README.md](README.md)).
- При следующей публикации клиентского архива — пересобрать `ToDoLite_v1.5.5.zip` из `dist/pack_v155_flat` после правок (см. [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md)).

---

## [1.5.5] — клиентский пакет и документация — 2026-04-03

Клиентский дистрибутив для пользователей Windows; номер **1.5.5** относится к **сборке архива**, не к отдельному тегу кода в репозитории. Версия разработки в шильдике README по-прежнему **1.6.1-dev**.

### Добавлено
- Архив **`ToDoLite_v1.5.5.zip`** (плоский корень): в корне проекта и копия в `docs/releases/v1.5.5/` (файл в `.gitignore`, пересобирается локально).
- В состав архива: `README.md`, `CLIENT_README.md`, `LICENSE`, `CHANGELOG.md`, `convert_line_endings.*`, `docs/AI_HANDOFF.md`, `docs/releases/v1.5.5/` (заметки релиза).
- Скрипт **`start.bat`** в клиентском наборе (в репозитории может отсутствовать — генерируется при сборке пакета в `dist/pack_v155_flat`).
- **`CHANGELOG.md`** — этот файл.
- **`docs/AI_HANDOFF.md`** — контекст для следующей сессии разработки с ИИ.

### Изменено
- **Форма добавления задачи** (`templates/index.html`): сетка **4 колонки**; поля переставлены (теги, даты, статус, Эйзенхауэр, треды на 3 колонки + напоминание в 4-й и т.д. по финальной вёрстке сессии).
- **«Ответственный»** при **создании** задачи: скрыт в UI, в форму уходит `<input type="hidden" name="assigned_to" value="">`; в **редактировании** задачи поле доступно.
- **`run_tray_silent.bat`**: проверка порта **5000** только для состояния **LISTENING** и строки с **`:5000 `**, чтобы не ловить ложные совпадения с портами вроде 50001.
- **`install.bat`**: финальные подсказки указывают на `start.bat` и `run_tray_silent.bat`.
- Документация: **`README.md`**, **`CLIENT_README.md`**, **`docs/README.md`**, **`docs/releases/README.md`**, **`docs/releases/v1.5.5/*`**, **`docs/technical/CLIENT_PACKAGE_REPORT.md`** (вступление со ссылкой на v1.5.5).

### Исправлено
- Устаревшие упоминания несуществующих скриптов (`update.cmd`, `run.bat`, `start_silent.bat` и т.п.) в пользовательской документации — приведены к актуальным `install.bat` / `run_tray_silent.bat` / `start.bat` из архива.
- Таблица зависимостей в **README**: дополнены пакеты из `requirements.txt` (Flask-WTF, WTForms, Flask-Limiter, colorama, bcrypt).

---

## Ранее

История подробных сессий и старых релизов: **[docs/DEVELOPMENT_LOG.md](docs/DEVELOPMENT_LOG.md)** и папки **[docs/releases/](docs/releases/)**.
