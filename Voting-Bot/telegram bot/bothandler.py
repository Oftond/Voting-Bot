import os
import sys
from datetime import datetime, timedelta
import asyncpg
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import config
from keyboard import keyboard
from logger import logger
from dotenv import load_dotenv


class bothandler:
    class PollCreation(StatesGroup):
        waiting_for_title = State()
        waiting_for_options = State()
        waiting_for_duration = State()

    class Voting(StatesGroup):
        choosing_poll = State()
        choosing_option = State()

    def __init__(self):
        if not config.BOT_TOKEN:
            print("❌ Токен бота не найден! Создайте файл bot_token.txt с токеном")
            sys.exit(1)

        self.bot = Bot(token=config.BOT_TOKEN)
        self.dp = Dispatcher()
        
        # Подключение к базе данных
        self.db_pool = None
        self.init_db()

        self.active_polls = {}  # Словарь для хранения активных опросов
        self._register_handlers()

    async def init_db(self):
        """Инициализация пула соединений с базой данных"""
        self.db_pool = await asyncpg.create_pool(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )

    def _register_handlers(self):
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.handle_delete, F.text == "Удалить")
        self.dp.message.register(self.handle_create_poll, F.text == "Создать голосование")
        self.dp.message.register(self.handle_vote, F.text == "Проголосовать")
        self.dp.message.register(self.handle_statistika, F.text == "Статистика")
        self.dp.message.register(self.handle_help, F.text == "Справка")
        self.dp.message.register(self.handle_cancel, F.text == "Отмена")

        # Обработчики состояний
        self.dp.message.register(
            self.handle_poll_title_input,
            StateFilter(self.PollCreation.waiting_for_title)
        )
        self.dp.message.register(
            self.handle_poll_options_input,
            StateFilter(self.PollCreation.waiting_for_options)
        )
        self.dp.message.register(
            self.handle_poll_duration_input,
            StateFilter(self.PollCreation.waiting_for_duration)
        )
        self.dp.message.register(
            self.handle_choose_poll,
            StateFilter(self.Voting.choosing_poll)
        )
        self.dp.message.register(
            self.handle_choose_option,
            StateFilter(self.Voting.choosing_option)
        )

        self.dp.message.register(self.handle_any_message)

    async def show_main_menu(self, message: types.Message):
        """Показывает главное меню"""
        await message.answer(
            "Выберите действие:",
            reply_markup=keyboard.get_start_keyboard()
        )

    # Основные команды
    async def cmd_start(self, message: types.Message):
        logger.log_message(message)
        await self.show_main_menu(message)

    async def handle_delete(self, message: types.Message):
        logger.log_message(message)
        await message.answer("Вы нажали кнопку 'Удалить'")
        await self.show_main_menu(message)

    # Система голосования
    async def handle_vote(self, message: types.Message, state: FSMContext):
        """Обработка кнопки 'Проголосовать'"""
        logger.log_message(message)

        self.active_polls = await self.fetch_active_polls()

        if not self.active_polls:
            await message.answer("⏳ Сейчас нет активных голосований.")
            await self.show_main_menu(message)
            return

        polls_list = "\n".join(
            f"ID: {poll['id']} - {poll['title']} (до {poll['end_time'].strftime('%d.%m.%Y %H:%M')})"
            for poll in self.active_polls
        )

        await message.answer(
            f"📝 Выберите ID голосования:\n\n{polls_list}",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.Voting.choosing_poll)

    async def fetch_active_polls(self):
        """Получаем список активных опросов из базы данных"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, title, end_time FROM polls WHERE is_active = TRUE
            """)
            return [{'id': row['id'], 'title': row['title'], 'end_time': row['end_time']} for row in rows]

    async def handle_choose_poll(self, message: types.Message, state: FSMContext):
        """Обработка выбора голосования по ID"""
        try:
            poll_id = int(message.text)
            poll = await self.fetch_poll(poll_id)

            if not poll:
                await message.answer("🔢 Пожалуйста, введите корректный ID голосования.")
                return
            
            if datetime.now() > poll['end_time']:
                await message.answer("⏰ Это голосование уже завершено.")
                await state.clear()
                return
            
            if message.from_user.id in poll['voted_users']:
                await message.answer("❌ Вы уже голосовали в этом опросе.")
                await state.clear()
                return

            await state.update_data(poll_id=poll_id)
            await message.answer(
                f"🗳 Голосование: {poll['title']}\nВыберите вариант:",
                reply_markup=keyboard.get_poll_options_keyboard(poll['options'])
            )
            await state.set_state(self.Voting.choosing_option)

        except ValueError:
            await message.answer("🔢 Пожалуйста, введите корректный ID голосования.")
            return

    async def fetch_poll(self, poll_id):
        """Получить информацию об опросе по ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM polls WHERE id = $1", poll_id)
            return row

    async def handle_choose_option(self, message: types.Message, state: FSMContext):
        """Обработка выбора варианта"""
        data = await state.get_data()
        poll_id = data['poll_id']
        poll = await self.fetch_poll(poll_id)

        if message.text not in poll['options']:
            await message.answer(
                "⚠️ Пожалуйста, выберите вариант из предложенных.",
                reply_markup=keyboard.get_poll_options_keyboard(poll['options'])
            )
            return

        # Записываем голос в базу данных
        await self.save_vote(poll_id, message.text, message.from_user.id)

        await message.answer(
            f"✅ Спасибо! Ваш голос '{message.text}' засчитан.",
            reply_markup=keyboard.get_start_keyboard()
        )
        await state.clear()

    async def save_vote(self, poll_id, option_text, user_id):
        """Сохранение голоса в БД"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO votes (poll_id, user_id, option_id)
                VALUES ($1, $2, (SELECT id FROM poll_options WHERE poll_id = $1 AND option_text = $3))
                ON CONFLICT (poll_id, user_id) DO NOTHING
            """, poll_id, user_id, option_text)

    # Система создания голосований
    async def handle_create_poll(self, message: types.Message, state: FSMContext):
        logger.log_message(message)

        if not await self._check_admin_rights(message):
            await self.show_main_menu(message)
            return

        await message.answer("Введите название голосования:",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.PollCreation.waiting_for_title)

    async def handle_poll_title_input(self, message: types.Message, state: FSMContext):
        logger.log_message(message)
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
        logger.log_message(message)
        if len(options) < 2:
            await message.answer("Нужно минимум 2 варианта ответа!")
            return

        if len(options) > 10:
            await message.answer("Максимум 10 вариантов ответа!")
            return

        await state.update_data(options=options)
        await message.answer(
            "Введите продолжительность голосования в часах (1-720):",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.PollCreation.waiting_for_duration)

    async def handle_poll_duration_input(self, message: types.Message, state: FSMContext):
        try:
            duration = int(message.text)
            logger.log_message(message)
            if not 1 <= duration <= 720:  # От 1 часа до 30 дней
                raise ValueError
        except ValueError:
            await message.answer("Некорректное значение! Введите число от 1 до 720")
            return

        poll_data = await state.get_data()
        end_time = datetime.now() + timedelta(hours=duration)

        # Сохраняем опрос в БД
        async with self.db_pool.acquire() as conn:
            poll_id = await conn.fetchval("""
                INSERT INTO polls (question, created_by, ends_at)
                VALUES ($1, $2, $3) RETURNING id
            """, poll_data['title'], message.from_user.id, end_time)
            
            # Сохраняем варианты ответов
            for option in poll_data['options']:
                await conn.execute("""
                    INSERT INTO poll_options (poll_id, option_text)
                    VALUES ($1, $2)
                """, poll_id, option)

        await message.answer(
            f"✅ Голосование создано!\n"
            f"ID: #{poll_id}\n"
            f"Название: {poll_data['title']}\n"
            f"Варианты: {', '.join(poll_data['options'])}\n"
            f"Завершится: {end_time.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=keyboard.get_start_keyboard()
        )
        await state.clear()

    # Обработка отмены
    async def handle_cancel(self, message: types.Message, state: FSMContext):
        """Обработка кнопки 'Отмена'"""
        logger.log_message(message)
        current_state = await state.get_state()
        if current_state:
            logger.log_vote_attempt(message.from_user.id,
                                    f"Отмена на этапе {current_state.split(':')[-1]}")
            await message.answer("❌ Действие отменено")
            await state.clear()
        await self.show_main_menu(message)

    # Система статистики
    async def handle_statistika(self, message: types.Message):
        logger.log_message(message)

        if not self.active_polls:
            await message.answer("Активных голосований нет.")
            return

        response = "📊 Статистика голосований:\n\n"

        for poll_id in self.active_polls.keys():
            poll = await self.fetch_poll(poll_id)
            total_votes = sum(poll['votes'].values())
            end_time = poll['end_time']
            time_left = end_time - datetime.now()

            if time_left.total_seconds() > 0:
                time_str = f"⏳ Осталось: {str(time_left).split('.')[0]}"
            else:
                time_str = "🔴 Голосование завершено"

            options_stats = await self.calculate_votes_stats(poll_id)

            response += (
                f"📌 #{poll_id}: {poll['title']}\n"
                f"{time_str}\n"
                f"🗳 Всего голосов: {total_votes}\n"
                f"{options_stats}\n\n"
            )

        await message.answer(response)
        await self.show_main_menu(message)

    async def calculate_votes_stats(self, poll_id):
        """Получаем статистику голосов по опциим"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT option_text, COUNT(votes.id) AS vote_count
                FROM poll_options
                LEFT JOIN votes ON poll_options.id = votes.option_id
                WHERE poll_options.poll_id = $1
                GROUP BY option_text
            """, poll_id)

            stats = []
            for row in rows:
                stats.append(f"  • {row['option_text']}: {row['vote_count']}")

            return "\n".join(stats)

    # Вспомогательные методы
    async def _check_admin_rights(self, message: types.Message) -> bool:
        if message.from_user.id not in config.ADMIN_IDS:
            await message.answer("⛔ Вы не являетесь администратором!")
            return False
        return True

    async def handle_help(self, message: types.Message):
        logger.log_message(message)
        await message.answer("Справка:\n" + "\n".join(config.AVAILABLE_COMMANDS))
        await self.show_main_menu(message)

    async def handle_any_message(self, message: types.Message):
        logger.log_message(message)

    async def run(self):
        print("🟢 Бот запущен и начал логирование...")
        await self.dp.start_polling(self.bot)