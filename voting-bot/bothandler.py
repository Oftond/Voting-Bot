import asyncio
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
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            data['user_id'] = user_id
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
        try:
            self.pool = await asyncpg.create_pool(
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                database=self.DB_NAME,
                host=self.DB_HOST,
                port=self.DB_PORT)
            print("Successfully initialized DB")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            sys.exit(1)

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

    #################################################################################################################################################################################################
    async def cmd_start(self, message: types.Message):
        logger.log_message(message)
        user_id = message.from_user.id
        username = message.from_user.username

        # Проверяем, есть ли пользователь в базе
        is_new_user = await self.is_new_user(user_id)

        # Добавляем/обновляем пользователя в базе
        await self.upsert_user(user_id, username)

        # Если пользователь новый - показываем приветственное сообщение
        if is_new_user:
            welcome_msg = (
                "Voting Bot - это бот для проведения опросов в телеграмме "
                "с сохранением и выводом статистики по каждому опросу.\n\n"
                "Выберите действие:"
            )
            await message.answer(welcome_msg, reply_markup=keyboard.get_start_keyboard())
        else:
            await self.show_main_menu(message)

    async def is_new_user(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь новым (отсутствует в базе)"""
        async with self.pool.acquire() as conn:
            user = await conn.fetchrow("SELECT 1 FROM users WHERE telegram_id = $1", user_id)
            return user is None
    #################################################################################################################################################################################################
    async def handle_vote(self, message: types.Message, state: FSMContext):
        active_polls = await self.fetch_active_polls()
        if not active_polls:
            await message.answer("⏳ Нет активных голосований.")
            return

        # Конструируем список голосований для пользователя
        polls_list = "\n".join(f"ID: {poll['id']} - {poll['title']}" for poll in active_polls)

        await message.answer(f"📝 Доступные голосования:\n\n{polls_list}", reply_markup=keyboard.get_cancel_keyboard())
        await state.set_state(self.Voting.choosing_poll)

    async def fetch_active_polls(self, user_id=None):
        query = "SELECT * FROM polls WHERE is_active = TRUE AND end_time > NOW()"
        if user_id:  # Filter by user if provided
            query = f"SELECT * FROM polls WHERE is_active = TRUE AND end_time > NOW() AND creator_id = {user_id}"
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch(query)
            except Exception as e:
                print(f"Error fetching active polls: {e}")
                return []

    async def handle_delete(self, message: types.Message, state: FSMContext):
        """Обработка кнопки 'Удалить/Завершить голосование'"""
        data = await state.get_data()
        user_id = data.get('user_id')  # Получаем ID пользователя

        polls_to_show = await self.fetch_active_polls(user_id=user_id)
        
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
            try:
              return await conn.fetch("SELECT * FROM polls WHERE creator_id = $1", user_id)
            except Exception as e:
                print(f"Error fetching user polls: {e}")
                return []

    async def handle_choose_poll_to_manage(self, message: types.Message, state: FSMContext):
        """Обработка выбора голосования для управления"""
        user_id = message.from_user.id  # Получаем ID пользователя

        try:
            poll_id = int(message.text)  # Получаем ID голосования из текста сообщения

            if poll_id <= 0:
                await message.answer("Некорректный ID голосования.")
                return
                
            # Запрашиваем информацию о голосовании
            poll = await self.fetch_poll(poll_id)

            if not poll:
                await message.answer("Голосование не найдено.")
                return
                
            # Сохраняем creator_id для дальнейшей проверки прав
            creator_id = poll['creator_id']
            if creator_id != user_id:  # Проверка прав на управление
                await message.answer("❌ У вас нет прав на управление этим голосованием.")
                await state.set_state(self.PollManagement.choosing_poll)  # Повторно устанавливаем состояние
                return

            # Определяем статус голосования
            status_msg = "🔴 Голосование уже завершено" if not poll['is_active'] else "🟢 Голосование активно"

            # Отправляем пользователю информацию о голосовании и статусе
            await message.answer(
                f"Голосование #{poll_id}: {poll['title']}\n{status_msg}\nВыберите действие:",
                reply_markup=keyboard.get_confirm_keyboard()  # Отправляем клавиатуру действия
            )

            # Сохраняем poll_id и creator_id в состоянии для дальнейшего использования
            await state.update_data(poll_id=poll_id, creator_id=creator_id)  
            await state.set_state(self.PollManagement.confirm_action)  # Выставляем состояние для подтверждения действия

        except ValueError as e:
            await message.answer(f"Ошибка: {str(e)}")
            await state.set_state(self.PollManagement.choosing_poll)  # Устанавливаем состояние повторно
            
    async def handle_confirm_management(self, message: types.Message, state: FSMContext):
        """Обработка подтверждения действия"""
        logger.log_message(message)
        data = await state.get_data()
        poll_id = data.get('poll_id')

        if not poll_id:
            await message.answer("Ошибка: голосование не выбрано.")
            await state.clear()
            return

        try:
            poll = await self.fetch_poll(poll_id)

            if not poll:
                await message.answer("Голосование не найдено.")
                await state.clear()
                return

            # Теперь мы не проверяем права доступа
            if message.text == "Удалить":
                await self.delete_poll(poll_id)  # Удаление из БД
                await message.answer(
                    f"Голосование #{poll_id} удалено.",
                    reply_markup=keyboard.get_start_keyboard()
                )

            elif message.text == "Завершить":
                if datetime.now() > poll['end_time']:
                    await message.answer("Это голосование уже завершено.")
                    await state.clear()
                    return
                
                # Завершаем голосование и сохраняем в архив
                await self.end_poll(poll_id)  # Завершение в БД

                # Важно: Добавьте обработку статистики, если требуется
                await message.answer(
                    f"✅ Голосование #{poll_id} завершено.\n"
                    f"Название: {poll['title']}",
                    reply_markup=keyboard.get_start_keyboard()
                )

            elif message.text == "Отмена":
                await message.answer("Действие отменено.", reply_markup=keyboard.get_start_keyboard())
            
            else:
                await message.answer("Неизвестная команда.")

            await state.clear()

        except (ValueError, KeyError) as e:
            await message.answer(f"Ошибка: {e}")
            await state.clear()

    async def delete_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("DELETE FROM polls WHERE id = $1", poll_id)
                await conn.execute("DELETE FROM poll_options WHERE poll_id = $1", poll_id)  # Важно!
                await conn.execute("DELETE FROM votes WHERE poll_id = $1", poll_id)  # Важно!
                print(f"Голосование {poll_id} удалено из БД.")
            except Exception as e:
                print(f"Ошибка при удалении голосования из БД: {e}")

    async def end_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("UPDATE polls SET is_active = FALSE WHERE id = $1", poll_id)
                print(f"Голосование {poll_id} завершено в БД.")
            except Exception as e:
                print(f"Ошибка при завершении голосования в БД: {e}")

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

            # Сохраняем опрос
            poll_id = await conn.fetchval(
                '''
                INSERT INTO polls (title, creator_id, end_time, is_active)
                VALUES ($1, $2, $3, TRUE) RETURNING id
                ''',
                poll_data['title'],
                user_id,
                end_time
            )

            # Сохраняем варианты опроса
            for option in poll_data['options']:
                await conn.execute(
                    '''
                    INSERT INTO poll_options (poll_id, option_text) 
                    VALUES ($1, $2)
                    ''',
                    poll_id,
                    option
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
        try:
            poll_id = int(message.text)  # Получаем ID голосования из текста сообщения
            poll = await self.fetch_poll(poll_id)

            if not poll:
                raise ValueError("Голосование не найдено.")
            
            if not poll['is_active']:
                await message.answer("⏰ Это голосование уже завершено.")
                await state.clear()
                return
            
            # Проверяем, уже проголосовал ли этот пользователь
            user_id = message.from_user.id
            async with self.pool.acquire() as conn:
                existing_vote = await conn.fetchrow(
                    "SELECT option_id FROM votes WHERE poll_id = $1 AND user_id = $2", poll_id, user_id
                )
                if existing_vote:
                    await message.answer("❌ Вы уже проголосовали в этом голосовании.")
                    await self.show_main_menu(message)  # Перенаправляем пользователя в главное меню
                    await state.clear()
                    return

            # Если голосование активно и пользователь еще не голосовал, показываем варианты
            await state.update_data(poll_id=poll_id)
            options = await self.fetch_poll_options(poll_id)
            if not options:
                await message.answer("⚠️ Нет вариантов ответа для этого голосования.")
                await state.clear()
                return

            options_list = [option['option_text'] for option in options]
            await message.answer(
                f"🗳 Голосование: {poll['title']}\nВыберите вариант:",
                reply_markup=keyboard.get_poll_options_keyboard(options_list)
            )
            
            await state.set_state(self.Voting.choosing_option)

        except ValueError as e:
            await message.answer(f"Ошибка: {str(e)}")
            await self.show_main_menu(message)  # Можно также вернуть пользователя в главное меню
            await state.clear()


    async def fetch_poll_options(self, poll_id):
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetch("SELECT * FROM poll_options WHERE poll_id = $1", poll_id)
            except Exception as e:
                print(f"Error fetching poll options: {e}")
                return []
            
    async def fetch_poll(self, poll_id):
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetchrow("SELECT * FROM polls WHERE id = $1", poll_id)
            except Exception as e:
                print(f"Error fetching poll: {e}")
                return None

    async def handle_choose_option(self, message: types.Message, state: FSMContext):
        try:
            data = await state.get_data()
            poll_id = data['poll_id']
            user_id = message.from_user.id

            # Получаем варианты голосования
            options = await self.fetch_poll_options(poll_id)
            option_dict = {option['option_text']: option['id'] for option in options}

            # Убедитесь, что пользователь существует в базе
            username = message.from_user.username  # Получаем имя пользователя
            await self.upsert_user(user_id, username)

            # Проверяем, уже проголосовал ли этот пользователь
            async with self.pool.acquire() as conn:
                existing_vote = await conn.fetchrow(
                    "SELECT option_id FROM votes WHERE poll_id = $1 AND user_id = $2", poll_id, user_id
                )
                if existing_vote:
                    await message.answer("❌ Вы уже проголосовали в этом голосовании.")
                    await self.show_main_menu(message)  # Возврат в главное меню
                    await state.clear()
                    return

                if message.text not in option_dict:
                    await message.answer("⚠️ Пожалуйста, выберите вариант из предложенных.")
                    return

                selected_option_id = option_dict[message.text]

                # Запись голоса пользователя в БД
                await conn.execute(
                    '''
                    INSERT INTO votes (poll_id, user_id, option_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (poll_id, user_id) DO NOTHING
                    ''',
                    poll_id,
                    user_id,
                    selected_option_id
                )

            await message.answer(f"✅ Спасибо! Ваш голос за '{message.text}' засчитан.", reply_markup=keyboard.get_start_keyboard())
            await state.clear()

        except Exception as e:
            print(f"Ошибка в обработке выбора варианта: {e}")
            await message.answer("Произошла ошибка. Повторите попытку позже.")
            await state.clear()

    async def handle_cancel(self, message: types.Message, state: FSMContext):
        logger.log_message(message)
        await state.clear()
        await self.show_main_menu(message)

    async def handle_statistika(self, message: types.Message):
        logger.log_message(message)

        async with self.pool.acquire() as conn:
            try:
                all_polls = await conn.fetch(
                    """
                    SELECT
                    p.id,
                    p.title,
                    p.created_at,
                    p.end_time,
                    po.option_text,
                    COUNT(v.option_id) AS votes_count,
                    CASE WHEN p.is_active THEN true ELSE false END AS is_active
                    FROM
                        polls p
                    JOIN
                        poll_options po ON p.id = po.poll_id
                    LEFT JOIN
                        votes v ON po.id = v.option_id
                    GROUP BY
                        p.id, po.id
                    ORDER BY
                        p.id;
                    """
                )

                if not all_polls:
                    await message.answer("Не найдено ни одного голосования.")
                    return

                response = "📊 Статистика голосований:\n\n"
                polls_stats = {}

                for poll in all_polls:
                    poll_id = poll['id']
                    if poll_id not in polls_stats:
                        polls_stats[poll_id] = {
                            "title": poll['title'],
                            "created_at": poll['created_at'],
                            "end_time": poll['end_time'],
                            "votes": 0,
                            "is_active": poll['is_active'],
                            "options": {}
                        }

                    option = poll['option_text']
                    votes = poll['votes_count']

                    polls_stats[poll_id]["votes"] += votes
                    polls_stats[poll_id]["options"][option] = votes

                for poll_id, stats in polls_stats.items():
                    options_stats = stats["options"]
                    total_votes = stats["votes"]
                    option_strings = [
                        f"  • {option}: {votes} ({(votes / total_votes * 100) if total_votes > 0 else 0:.1f}%)"
                        for option, votes in options_stats.items()
                    ]

                    status = "🔴 Завершено" if not stats["is_active"] else "🟢 Активно"

                    response += ( 
                        f"📌 #{poll_id}: {stats['title']}\n"
                        f"Создано: {stats['created_at'].strftime('%d.%m.%Y %H:%M')}\n"
                        f"Завершится: {stats['end_time'].strftime('%d.%m.%Y %H:%M')}\n"
                        f"Статус: {status}\n"
                        f"Всего голосов: {total_votes}\n"
                        f"{''.join([s + '\n' for s in option_strings])}\n\n"
                    )

                await message.answer(response)

            except Exception as e:
                await message.answer(f"Ошибка при получении статистики: {e}")


    async def count_votes(self, poll_id):
            async with self.pool.acquire() as conn:
                return await conn.fetchval('SELECT COUNT(*) FROM votes WHERE poll_id = $1', poll_id)
            
    async def handle_help(self, message: types.Message):
        logger.log_message(message)
            
        help_message = (
            "Спасибо, что выбрали нашего бота Voting Bot — это бот для проведения опросов в Telegram "
            "с сохранением и выводом статистики по каждому опросу.\n\n"
            "Доступные команды:\n"
            "Удалить/Завершить голосование\n"
            "Создать голосование\n"
            "Проголосовать\n"
            "Статистика\n"
            "Справка"
        )
        await message.answer(help_message)
        await self.show_main_menu(message)

    # Добавьте этот метод в класс bothandler
    async def show_available_commands(self, message: types.Message):
        commands = (
            "/start - Начать взаимодействие с ботом\n"
            "/удалить - Удалить/Завершить голосование\n"
            "/создать - Создать новое голосование\n"
            "/проголосовать - Проголосовать в активном голосовании\n"
            "/статистика - Показать статистику голосований\n"
            "/справка - Получить справочную информацию"
        )
        await message.answer(f"Неизвестная команда. Доступные команды:\n{commands}")

    # Обновите метод handle_any_message
    async def handle_any_message(self, message: types.Message):
        await message.answer("❌ Команда не распознана.")
        await self.show_available_commands(message)

    async def update_polls(self):
        await asyncio.sleep(10)  # Обновляем информацию о голосованиях каждые 10c
        await self.update_active_polls()
        await self.update_archived_polls()

    async def update_active_polls(self):
        async with self.pool.acquire() as conn:
            try:
                active_polls = await conn.fetch("SELECT * FROM polls WHERE is_active = TRUE AND end_time > NOW()")
                for poll in active_polls:
                    # Обновляем информацию о голосовании в БД
                    await conn.execute("UPDATE polls SET last_updated = NOW() WHERE id = $1", poll['id'])
            except Exception as e:
                print(f"Error updating active polls: {e}")

    async def update_archived_polls(self):
        async with self.pool.acquire() as conn:
            try:
                archived_polls = await conn.fetch("SELECT * FROM polls WHERE is_active = FALSE AND end_time <= NOW()")
                for poll in archived_polls:
                    # Обновляем информацию о голосовании в БД
                    await conn.execute("UPDATE polls SET last_updated = NOW() WHERE id = $1", poll['id'])
            except Exception as e:
                print(f"Error updating archived polls: {e}")

    async def run(self):
        await self.init_db()
        print("🟢 Бот запущен и начал логирование...")
        try:
            await self.dp.start_polling(self.bot)
            self.dp.loop.create_task(self.update_polls())
        finally:
            await self.close_db()