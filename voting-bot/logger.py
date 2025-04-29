from datetime import datetime
from aiogram import types
class logger:
    @staticmethod
    def log_message(message: types.Message):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_id = message.from_user.id
        username = message.from_user.username or "Без username"
        first_name = message.from_user.first_name or "Без имени"
        text = message.text or "Нет текста (стикер/фото/другое)"

        print(
            f"[{time}] 🚀 Сообщение от: "
            f"ID={user_id}, "
            f"Username=@{username}, "
            f"Имя={first_name}\n"
            f"Текст: {text}\n"
            f"────────────────────"
        )

    @staticmethod
    def log_vote(user_id: int, poll_id: int, option: str):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{time}] ✅ Голосование: "
            f"Пользователь ID={user_id} "
            f"проголосовал в опросе ID={poll_id} "
            f"за вариант '{option}'\n"
            f"────────────────────"
        )

    @staticmethod
    def log_vote_attempt(user_id: int, action: str):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{time}] ⚠️ Попытка голосования: "
            f"Пользователь ID={user_id} "
            f"действие: {action}\n"
            f"────────────────────"
        )