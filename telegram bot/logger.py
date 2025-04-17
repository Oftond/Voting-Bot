# from datetime import datetime
# from aiogram import types
# class logger:
#     @staticmethod
#     def log_message(message: types.Message):
#         time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         user_id = message.from_user.id
#         username = message.from_user.username or "Без username"
#         first_name = message.from_user.first_name or "Без имени"
#         text = message.text or "Нет текста (стикер/фото/другое)"

#         print(
#             f"[{time}] 🚀 Сообщение от: "
#             f"ID={user_id}, "
#             f"Username=@{username}, "
#             f"Имя={first_name}\n"
#             f"Текст: {text}\n"
#             f"────────────────────"
#         )