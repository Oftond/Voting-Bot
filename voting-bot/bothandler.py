import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import BaseMiddleware
from keyboard import keyboard
from logger import logger
from datetime import datetime, timedelta
import config
import asyncpg
import sys

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Для сообщений
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            data['user_id'] = user_id
        
        # Для callback-запросов (если нужно)
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            data['user_id'] = user_id
            
        return await handler(event, data)

class bothandler:
    class PollCreation(StatesGroup):
        waiting_for_title = State()
        waiting_for_options = State()
        waiting_for_duration = State()

    class Voting(StatesGroup):
        choosing_poll = State()
        choosing_option = State()

    class PollManagement(StatesGroup):
        choosing_poll = State()
        confirm_action = State()

    def __init__(self):
        self.BOT_TOKEN = os.getenv("BOT_TOKEN")
        self.DB_USER = os.getenv("DB_USER")
        self.DB_PASSWORD = os.getenv("DB_PASSWORD")
        self.DB_NAME = os.getenv("DB_NAME")
        self.DB_HOST = os.getenv("DB_HOST")
        self.DB_PORT = os.getenv("DB_PORT")

        if not self.BOT_TOKEN:
            print("❌ Токен бота не найден! Убедитесь, что он указан в .env")
            sys.exit(1)

        self.bot = Bot(token=self.BOT_TOKEN)
        self.dp = Dispatcher()
        self._register_handlers()
        self.active_polls = {}
        self.archived_polls = {}

        self.pool = None

    async def init_db(self):
        """Инициализирует пул соединений с PostgreSQL."""
        self.pool = await asyncpg.create_pool(
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            database=self.DB_NAME,
            host=self.DB_HOST,
            port=self.DB_PORT
        )

    async def close_db(self):
        """Закрывает пул соединений с PostgreSQL."""
        await self.pool.close()

    def _register_handlers(self):
        self.dp.message.middleware.register(UserMiddleware())  # Регистрация middleware

        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.handle_delete, F.text == "Удалить/Завершить голосование")
        self.dp.message.register(self.handle_create_poll, F.text == "Создать голосование")
        self.dp.message.register(self.handle_vote, F.text == "Проголосовать")
        self.dp.message.register(self.handle_statistika, F.text == "Статистика")
        self.dp.message.register(self.handle_help, F.text == "Справка")
        self.dp.message.register(self.handle_cancel, F.text == "Отмена")

        self.dp.message.register(self.handle_poll_title_input, StateFilter(self.PollCreation.waiting_for_title))
        self.dp.message.register(self.handle_poll_options_input, StateFilter(self.PollCreation.waiting_for_options))
        self.dp.message.register(self.handle_poll_duration_input, StateFilter(self.PollCreation.waiting_for_duration))
        self.dp.message.register(self.handle_choose_poll, StateFilter(self.Voting.choosing_poll))
        self.dp.message.register(self.handle_choose_option, StateFilter(self.Voting.choosing_option))
        self.dp.message.register(self.handle_choose_poll_to_manage, StateFilter(self.PollManagement.choosing_poll))
        self.dp.message.register(self.handle_confirm_management, StateFilter(self.PollManagement.confirm_action))

        self.dp.message.register(self.handle_any_message)

    async def show_main_menu(self, message: types.Message):
        """Показывает главное меню"""
        await message.answer("Выберите действие:", reply_markup=keyboard.get_start_keyboard())

    # Основные команды
    async def cmd_start(self, message: types.Message):
        logger.log_message(message)
        await self.show_main_menu(message)

    async def handle_vote(self, message: types.Message, state: FSMContext):
        """Обработка кнопки 'Проголосовать'"""
        data = await state.get_data()
        user_id = data.get('user_id')  # Получаем ID пользователя

        poll_list = await self.fetch_active_polls()
        if not poll_list:
            await message.answer("⏳ Сейчас нет активных голосований.")
            return

        polls_list = "\n".join(
            f"ID: {poll['id']} - {poll['title']} (до {poll['end_time']})"
            for poll in poll_list
        )
        await message.answer(
            f"📝 Выберите ID голосования:\n\n{polls_list}",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.Voting.choosing_poll)

    async def fetch_active_polls(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM polls WHERE is_active = TRUE AND end_time > NOW()")

    async def handle_delete(self, message: types.Message, state: FSMContext):
        """Обработка кнопки 'Удалить/Завершить голосование'"""
        data = await state.get_data()
        user_id = data.get('user_id')  # Получаем ID пользователя

        polls_to_show = await self.fetch_user_polls(user_id)
        
        if not polls_to_show:
            await message.answer("Нет доступных голосований для управления.")
            return

        polls_list = "\n".join(
            f"ID: {poll['id']} - {poll['title']} (до {poll['end_time']})"
            for poll in polls_to_show
        )
        await message.answer(f"Ваши голосования для управления:\n\n{polls_list}", reply_markup=keyboard.get_cancel_keyboard())
        await state.set_state(self.PollManagement.choosing_poll)

    async def fetch_user_polls(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM polls WHERE creator_id = $1", user_id)

    async def handle_choose_poll_to_manage(self, message: types.Message, state: FSMContext):
        """Обработка выбора голосования для управления"""
        data = await state.get_data()
        user_id = data.get('user_id')  # Получаем ID пользователя
        is_admin = data.get('is_admin', False)

        try:
            poll_id = int(message.text)
            poll = await self.fetch_poll(poll_id)

            if not poll:
                raise ValueError("Голосование не найдено")
            if not is_admin and poll['creator_id'] != user_id:
                raise ValueError("Нет прав для управления этим голосованием")

            status_msg = "🔴 Голосование уже завершено" if not poll['is_active'] else "🟢 Голосование активно"

            await message.answer(
                f"Голосование #{poll_id}: {poll['title']}\n{status_msg}\nВыберите действие:",
                reply_markup=keyboard.get_confirm_keyboard()
            )

            await state.update_data(poll_id=poll_id)
            await state.set_state(self.PollManagement.confirm_action)

        except ValueError as e:
            await message.answer(f"Ошибка: {str(e)}")
            await state.clear()

    async def fetch_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM polls WHERE id = $1", poll_id)

    async def handle_confirm_management(self, message: types.Message, state: FSMContext):
        """Обработка подтверждения действия"""
        logger.log_message(message)
        data = await state.get_data()
        poll_id = data.get('poll_id')
        user_id = data.get('user_id')  # Получаем ID пользователя
        is_admin = data.get('is_admin', False)

        if not poll_id:
            await message.answer("Ошибка: голосование не выбрано")
            await state.clear()
            return

        poll = self.active_polls.get(poll_id)

        if not poll:
            await message.answer("Голосование не найдено")
        elif not is_admin and poll['creator_id'] != user_id:
            await message.answer("❌ Нет прав для управления этим голосованием")
        else:
            if message.text == "Удалить":
                # Полное удаление голосования
                del self.active_polls[poll_id]
                await message.answer(
                    f"Голосование #{poll_id} полностью удалено.",
                    reply_markup=keyboard.get_start_keyboard()

                )
            elif message.text == "Завершить":
                if datetime.now() > poll['end_time']:
                    await message.answer("Это голосование уже завершено")
                else:
                    # Завершаем голосование и сохраняем в архив
                    poll['end_time'] = datetime.now()
                    self.archived_polls[poll_id] = poll
                    del self.active_polls[poll_id]
                    await message.answer(
                        f"✅ Голосование #{poll_id} завершено.\n"
                        f"Название: {poll['title']}\n"
                        f"Статистика сохранена.",
                        reply_markup=keyboard.get_start_keyboard()
                    )
            elif message.text == "Отмена":
                await message.answer("Действие отменено", reply_markup=keyboard.get_start_keyboard())

        await state.clear()

    async def delete_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM polls WHERE id = $1", poll_id)

    async def end_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE polls SET is_active = FALSE WHERE id = $1", poll_id)

    async def handle_create_poll(self, message: types.Message, state: FSMContext):
        user_id = message.from_user.id  # Получение Telegram ID пользователя
        username = message.from_user.username  # Получение имени пользователя (если задано)
        
        # Запрашиваем название голосования
        await message.answer(
            "Введите название голосования:",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        
        # Устанавливаем состояние ожидания названия голосования
        await state.set_state(self.PollCreation.waiting_for_title)

    async def handle_poll_title_input(self, message: types.Message, state: FSMContext):
        if len(message.text) > 200:
            await message.answer("Слишком длинное название (макс. 200 символов)")
            return

        await state.update_data(title=message.text)
        await message.answer(
            "Введите варианты ответов через пробел (например: Да Нет Воздержался)",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.PollCreation.waiting_for_options)

    async def handle_poll_options_input(self, message: types.Message, state: FSMContext):
        options = message.text.split()
        if len(options) < 2:
            await message.answer("Нужно минимум 2 варианта ответа!")
            return
        if len(options) > 10:
            await message.answer("Максимум 10 вариантов ответа!")
            return

        await state.update_data(options=options)
        await message.answer("Введите продолжительность голосования в часах (1-720):", reply_markup=keyboard.get_cancel_keyboard())
        await state.set_state(self.PollCreation.waiting_for_duration)


    async def upsert_user(self, telegram_id: int, username: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute(
                '''
                INSERT INTO users (telegram_id, username) 
                VALUES ($1, $2)
                ON CONFLICT (telegram_id) DO UPDATE SET username = EXCLUDED.username
                ''',
                telegram_id,
                username
            )

    async def handle_poll_duration_input(self, message: types.Message, state: FSMContext):
        try:
            duration = int(message.text)
            if not 1 <= duration <= 720:
                raise ValueError
        except ValueError:
            await message.answer("Некорректное значение! Введите число от 1 до 720")
            return

        poll_data = await state.get_data()
        user_id = message.from_user.id  # Получаем user_id
        username = message.from_user.username  # Получаем username (может быть None)

        end_time = datetime.now() + timedelta(hours=duration)

        async with self.pool.acquire() as conn:
            # Здесь сохраняем или обновляем пользователя в таблице
            await self.upsert_user(user_id, username)

            poll_id = await conn.fetchval(
                '''
                INSERT INTO polls (title, creator_id, end_time, is_active)
                VALUES ($1, $2, $3, TRUE) RETURNING id
                ''',
                poll_data['title'],      # Название голосования
                user_id,                 # Telegram ID пользователя
                end_time                 # Время окончания голосования
            )

            await message.answer(
                f"✅ Голосование создано!\n"
                f"ID: #{poll_id}\n"
                f"Название: {poll_data['title']}\n"
                f"Варианты: {', '.join(poll_data['options'])}\n"
                f"Завершится: {end_time.strftime('%d.%m.%Y %H:%M')}",
                reply_markup=keyboard.get_start_keyboard()
            )
            await state.clear()

    async def handle_choose_poll(self, message: types.Message, state: FSMContext):
        """Обработка выбора голосования"""
        data = await state.get_data()
        user_id = data.get('user_id')  # Получаем ID пользователя

        try:
            poll_id = int(message.text)
            poll = await self.fetch_poll(poll_id)

            if not poll:
                raise ValueError

            if not poll['is_active']:
                await message.answer("⏰ Это голосование уже завершено.")
                await state.clear()
                return

            await state.update_data(poll_id=poll_id)
            options = await self.fetch_poll_options(poll_id)
            options_list = [option['option_text'] for option in options]
            await message.answer(
                f"🗳 Голосование: {poll['title']}\nВыберите вариант:",
                reply_markup=keyboard.get_poll_options_keyboard(options_list)
            )
            await state.set_state(self.Voting.choosing_option)

        except ValueError:
            await message.answer("🔢 Пожалуйста, введите корректный ID голосования.")

    async def fetch_poll_options(self, poll_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM poll_options WHERE poll_id = $1", poll_id)

    async def handle_choose_option(self, message: types.Message, state: FSMContext):
        data = await state.get_data()
        poll_id = data['poll_id']

        options = await self.fetch_poll_options(poll_id)
        if message.text not in [option['option_text'] for option in options]:
            await message.answer("⚠️ Пожалуйста, выберите вариант из предложенных.")
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                '''
                INSERT INTO votes (poll_id, user_id, option_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (poll_id, user_id) DO NOTHING
                ''',
                poll_id,
                message.from_user.id,     # Используем ID из message
                message.text               # Можно также добавить option_id, если это необходимо
            )

        await message.answer(f"✅ Спасибо! Ваш голос '{message.text}' засчитан.", reply_markup=keyboard.get_start_keyboard())
        await state.clear()

    async def handle_cancel(self, message: types.Message, state: FSMContext):
        logger.log_message(message)
        await state.clear()
        await self.show_main_menu(message)

    async def handle_statistika(self, message: types.Message):
        logger.log_message(message)

        all_polls = {**self.active_polls, **self.archived_polls}

        if not all_polls:
            await message.answer("Нет доступных голосований.")
            return

        response = "📊 Статистика голосований:\n\n"

        for poll_id, poll in all_polls.items():
            total_votes = sum(poll['votes'].values())
            end_time = poll['end_time']
            status = "🟢 Активно" if poll_id in self.active_polls else "🔴 Завершено"

            if total_votes > 0:
                options_stats = "\n".join(
                    f"  • {option}: {votes} ({votes / total_votes * 100:.1f}%)"
                    for option, votes in poll['votes'].items()
                )
            else:
                options_stats = "\n".join(
                    f"  • {option}: {votes} (0%)"
                    for option, votes in poll['votes'].items()
                )

            response += (
                f"📌 #{poll_id}: {poll['title']}\n"
                f"Статус: {status}\n"
                f"Завершено: {end_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"Всего голосов: {total_votes}\n"
                f"{options_stats}\n\n"
            )

        await message.answer(response)
        await self.show_main_menu(message)

    async def count_votes(self, poll_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval('SELECT COUNT(*) FROM votes WHERE poll_id = $1', poll_id)
        
    async def handle_help(self, message: types.Message):
        logger.log_message(message)
        await message.answer("Справка:\n" + "\n".join(config.AVAILABLE_COMMANDS))
        await self.show_main_menu(message)

    async def handle_any_message(self, message: types.Message):
        logger.log_message(message)

    async def run(self):
        await self.init_db()
        print("🟢 Бот запущен и начал логирование...")
        try:
            await self.dp.start_polling(self.bot)
        finally:
            await self.close_db()