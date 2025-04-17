# import logging
# from telegram import Update
# from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
# import psycopg2
# from psycopg2 import sql
# from aiogram import Bot, Dispatcher, types, F
# from aiogram.filters import Command, StateFilter
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import StatesGroup, State
# from config import config
# from keyboard import keyboard
# from logger import logger
# from datetime import datetime, timedelta
# from bdConn import get_db_connection


# class bothandler:
#     class PollCreation(StatesGroup):
#         waiting_for_title = State()
#         waiting_for_options = State()
#         waiting_for_duration = State()

#     def __init__(self):
#         self.bot = Bot(token=config.BOT_TOKEN)
#         self.dp = Dispatcher()
#         self._register_handlers()
#         self.active_polls = {}  # Временное хранилище для разработки

#     def _register_handlers(self):
#         self.dp.message.register(self.cmd_start, Command("start"))
#         self.dp.message.register(self.handle_delete, F.text == "Удалить")
#         self.dp.message.register(self.handle_create_poll, F.text == "Создать голосование")
#         self.dp.message.register(self.handle_statistika, F.text == "Статистика")
#         self.dp.message.register(self.handle_help, F.text == "Справка")
#         self.dp.message.register(self.handle_cancel, F.text == "Отмена")
#         self.dp.message.register(
#             self.handle_poll_title_input,
#             StateFilter(self.PollCreation.waiting_for_title)
#         )
#         self.dp.message.register(
#             self.handle_poll_options_input,
#             StateFilter(self.PollCreation.waiting_for_options)
#         )
#         self.dp.message.register(
#             self.handle_poll_duration_input,
#             StateFilter(self.PollCreation.waiting_for_duration)
#         )
#         self.dp.message.register(self.handle_any_message)

#     # Основные команды
#     async def cmd_start(self, message: types.Message, update: Update, context: CallbackContext) -> None:
#         logger.log_message(message)
#         conn = get_db_connection()
#         with conn:
#             with conn.cursor() as cursor:
#                 cursor.execute(sql.SQL("INSERT INTO users (telegram_id, username) VALUES (%s, %s) ON CONFLICT (telegram_id) DO NOTHING;"),
#                             [user.id, user.username])
#         conn.close()
#         await message.answer(
#             "Выберите действие:",
#             reply_markup=keyboard.get_start_keyboard()        
#         )

#     async def handle_delete(self, message: types.Message):
#         logger.log_message(message)
#         await message.answer("Вы нажали кнопку 'Удалить'")

#     # Система создания голосований
#     async def handle_create_poll(self, message: types.Message, state: FSMContext, update: Update, context: CallbackContext) -> None:
#         logger.log_message(message)

#         if not await self._check_admin_rights(message):
#             return

#         await message.answer(
#             "Введите название голосования:",
#             reply_markup=keyboard.get_cancel_keyboard()
#         )
#         await state.set_state(self.PollCreation.waiting_for_title)

        

    

#     async def handle_poll_title_input(self, message: types.Message, state: FSMContext):
#         if len(message.text) > 200:
#             await message.answer("Слишком длинное название (макс. 200 символов)")
#             return

#         await state.update_data(title=message.text)
#         await message.answer(
#             "Введите варианты ответов через пробел (например: Да Нет Воздержался)",
#             reply_markup=keyboard.get_cancel_keyboard()
#         )
#         await state.set_state(self.PollCreation.waiting_for_options)

#     async def handle_poll_options_input(self, message: types.Message, state: FSMContext):
#         options = message.text.split()

#         if len(options) < 2:
#             await message.answer("Нужно минимум 2 варианта ответа!")
#             return

#         if len(options) > 10:
#             await message.answer("Максимум 10 вариантов ответа!")
#             return

#         await state.update_data(options=options)
#         await message.answer(
#             "Введите продолжительность голосования в часах (1-720):",
#             reply_markup=keyboard.get_cancel_keyboard()
#         )
#         await state.set_state(self.PollCreation.waiting_for_duration)

#     async def handle_poll_duration_input(self, message: types.Message, state: FSMContext):
#         try:
#             duration = int(message.text)
#             if not 1 <= duration <= 720:  # От 1 часа до 30 дней
#                 raise ValueError
#         except ValueError:
#             await message.answer("Некорректное значение! Введите число от 1 до 720")
#             return

#         poll_data = await state.get_data()
#         end_time = datetime.now() + timedelta(hours=duration)

#         # Временное решение до интеграции с бэкендом
#         poll_id = len(self.active_polls) + 1
#         self.active_polls[poll_id] = {
#             'title': poll_data['title'],
#             'options': poll_data['options'],
#             'creator_id': message.from_user.id,
#             'end_time': end_time,
#             'votes': {option: 0 for option in poll_data['options']}
#         }

#         await message.answer(
#             f"✅ Голосование создано!\n"
#             f"ID: #{poll_id}\n"
#             f"Название: {poll_data['title']}\n"
#             f"Варианты: {', '.join(poll_data['options'])}\n"
#             f"Завершится: {end_time.strftime('%d.%m.%Y %H:%M')}",
#             reply_markup=keyboard.get_start_keyboard()
#         )
#         await state.clear()

#     async def handle_cancel(self, message: types.Message, state: FSMContext):
#         logger.log_message(message)
#         current_state = await state.get_state()
#         if current_state is None:
#             return

#         await state.clear()
#         await message.answer(
#             "Действие отменено",
#             reply_markup=keyboard.get_start_keyboard()
#         )

#     # Система статистики
#     async def handle_statistika(self, message: types.Message):
#         logger.log_message(message)

#         if not self.active_polls:
#             await message.answer("Активных голосований нет.")
#             return

#         response = "📊 Статистика голосований:\n\n"

#         for poll_id, poll in self.active_polls.items():
#             total_votes = sum(poll['votes'].values())
#             end_time = poll['end_time']
#             time_left = end_time - datetime.now()

#             # Форматируем время окончания
#             if time_left.total_seconds() > 0:
#                 time_str = f"⏳ Осталось: {str(time_left).split('.')[0]}"
#             else:
#                 time_str = "🔴 Голосование завершено"

#             # Формируем статистику по вариантам
#             if total_votes > 0:
#                 options_stats = "\n".join(
#                     f"  • {option}: {votes} ({votes / total_votes * 100:.1f}%)"
#                     for option, votes in poll['votes'].items()
#                 )
#             else:
#                 options_stats = "\n".join(
#                     f"  • {option}: {votes} (0%)"
#                     for option, votes in poll['votes'].items()
#                 )

#             response += (
#                 f"📌 #{poll_id}: {poll['title']}\n"
#                 f"{time_str}\n"
#                 f"🗳 Всего голосов: {total_votes}\n"
#                 f"{options_stats}\n\n"
#             )

#         await message.answer(response)
#     # Вспомогательные методы
#     async def _check_admin_rights(self, message: types.Message) -> bool:
#         if message.from_user.id not in config.ADMIN_IDS:
#             await message.answer("⛔ Вы не являетесь администратором!")
#             return False
#         return True

#     async def handle_help(self, message: types.Message):
#         logger.log_message(message)
#         await message.answer("Справка:\n" + "\n".join(config.AVAILABLE_COMMANDS))

#     async def handle_any_message(self, message: types.Message):
#         logger.log_message(message)

#     async def run(self):
#         print("🟢 Бот запущен и начал логирование...")
#         await self.dp.start_polling(self.bot)