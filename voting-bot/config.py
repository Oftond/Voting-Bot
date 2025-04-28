import os
from dotenv import load_dotenv
load_dotenv()


class сonfig:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(','))) if os.getenv("ADMIN_IDS") else []

    AVAILABLE_COMMANDS = [
        "Voting Bot - это бот для проведения опросов в телеграмме с сохранением и выводом статистики по каждому опросу"
    ]

    POLL_ACTIVE = "active"
    POLL_CLOSED = "closed"