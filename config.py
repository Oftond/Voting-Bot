import os
class config:
    # Чтение токена из файла
    try:
        with open(os.path.join(os.path.dirname(__file__), 'bot_token.txt'), 'r') as f:
            BOT_TOKEN = f.read().strip()
            if not BOT_TOKEN.startswith('') or len(BOT_TOKEN) < 30:  # Базовая проверка формата
                print("⚠️ Неверный формат токена бота!")
                BOT_TOKEN = ""
    except FileNotFoundError:
        BOT_TOKEN = ""
        print("⚠️ Файл с токеном бота (bot_token.txt) не найден!")
    # Список доступных команд
    AVAILABLE_COMMANDS = [
        "Voting Bot - это бот для проведения опросов в телеграмме с сохранением и выводом статистики по каждому опросу",
    ]

    # Белый список админов (ID пользователей)
    ADMIN_IDS = {1678859954,1652656859}

    # Статусы голосований
    POLL_ACTIVE = "active"
    POLL_CLOSED = "closed"