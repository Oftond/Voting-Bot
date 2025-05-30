# [Система голосований]  
**Команда:** [Сергеев Владимир, Балданай Белек, Коркин Михаил]  
**Задача:** [Бот создаёт опросы, голосования, сохраняет результаты и выдает статистку]  
**Стек:** Python, FastAPI, PostgreSQL  
**Ссылка на Miro:** [https://miro.com/welcomeonboard/Q2wzWWRyZStrTzI4dDhRMkNQQWxvUkNaWW5QSkJwTmxMRVExcGRZV01KMXRNTEowMjExT2pOMWpydWZtUGs2dkV5NW8vNXBTbXpOVElZOHExL1htU1RDcXkvTW5iaVlQNnNzQnVta0NIM2ZsOE1mWE1JWC9kcVZuWS81NFJKZ0J0R2lncW1vRmFBVnlLcVJzTmdFdlNRPT0hdjE=?share_link_id=825944607660]

# 🤖 Бот для голосований в Telegram  
Система позволяет создавать анонимные/публичные опросы, управлять ими через Telegram и сохранять результаты в БД.

## 🚀 Быстрый запуск  
### Требования:  
- Установленные **Docker** и **Docker Compose**.  
- Файл `.env` с настройками.

### Запуск:  
1. Склонируйте репозиторий:  
   git clone https://github.com/ваш-репозиторий.git  
   cd ваш-репозиторий
2. Запустите проект:
   docker-compose up -d
3. Бот будет доступен в Telegram по токену из .env.

### Команды бота
## 📌 Команды бота
- `/start` — приветствие.
- `Создать голосование` — создать голосование.
- `Статистика` — показать результаты.
- `Удалить/Завершить голосование` — управление голосованиями.
- `Проголосовать` — проголосовать.
- `Справка` — показать доступные команды.
- `Показать всех пользователей` — показать всех пользователей, зарегестрированных в боте.

### Конфигурация (`.env`)
## ⚙ Конфигурация  
Создайте файл `.env` в корне проекта:  
```env
TOKEN=ваш_токен_бота  
DB_URL=postgresql://user:password@db:5432/vote_bot  
ADMIN_IDS=123456789,987654321

TOKEN -	Токен бота от @BotFather
DB_URL - URL для подключения к PostgreSQL
ADMIN_IDS - ID админов через запятую
