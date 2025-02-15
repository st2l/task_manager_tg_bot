# Инструкция по запуску бота

## 1. Установка зависимостей

Установите все необходимые зависимости из файла requirements.txt:
```bash
pip install -r requirements.txt
```

## 2. Настройка .env файла

Создайте файл `.env` в корневой директории проекта со следующими параметрами:

```plaintext
# Telegram Bot
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz # Токен бота от @BotFather
TELEGRAM_BOT_USERNAME=your_bot_username # Имя бота без символа @
TELEGRAM_GROUP_ID=-1001234567890 # ID группы, где будет работать бот (с минусом для групп)

# Google Sheets (опционально, для работы с отчетами)
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json # Путь к файлу с credentials от Google Cloud
GOOGLE_SHEETS_SPREADSHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms # ID таблицы Google Sheets
```

## 3. Подготовка базы данных

Выполните миграции базы данных:
```bash
python manage.py migrate
```

## 4. Создание администратора

Для создания первого администратора, запустите бота и отправьте ему команду `/start`. Затем в Django админ-панели (`http://localhost:8000/admin/`) найдите вашего пользователя и установите флаг `is_admin = True`.

## 5. Запуск бота

Есть два способа запуска:

### Способ 1: Через entrypoint.sh
```bash
chmod +x entrypoint.sh
./entrypoint.sh
```

### Способ 2: Вручную
```bash
python manage.py runserver # В первом терминале
python manage.py runbot # Во втором терминале
```

## Примечания:
- Для работы с отчетами в Google Sheets необходимо настроить проект в Google Cloud Platform и получить credentials.json
- ID группы можно получить, добавив бота @RawDataBot в вашу группу
- Токен бота можно получить у @BotFather в Telegram

После запуска бот будет доступен в Telegram по указанному username. Отправьте команду `/start` для начала работы.
