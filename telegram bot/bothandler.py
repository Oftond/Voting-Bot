from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import config
from keyboard import keyboard
from logger import logger
from datetime import datetime, timedelta
import sys


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
        self._register_handlers()
        self.active_polls = {
            1: {
                'title': "Пример голосования",
                'options': ["За", "Против"],
                'creator_id': 123456789,
                'end_time': datetime.now() + timedelta(days=1),
                'votes': {"За": 0, "Против": 0},
                'voted_users': set()
            }
        }

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

        if not self.active_polls:
            await message.answer("⏳ Сейчас нет активных голосований.")
            await self.show_main_menu(message)
            return

        polls_list = "\n".join(
            f"ID: {poll_id} - {poll['title']} (до {poll['end_time'].strftime('%d.%m.%Y %H:%M')})"
            for poll_id, poll in self.active_polls.items()
        )

        await message.answer(
            f"📝 Выберите ID голосования:\n\n{polls_list}",
            reply_markup=keyboard.get_cancel_keyboard()
        )
        await state.set_state(self.Voting.choosing_poll)

    async def handle_choose_poll(self, message: types.Message, state: FSMContext):
        """Обработка выбора голосования по ID"""
        try:
            poll_id = int(message.text)
            if poll_id not in self.active_polls:
                raise ValueError

            poll = self.active_polls[poll_id]

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
                f"🗳 Голосование: {poll['title']}\n"
                "Выберите вариант:",
                reply_markup=keyboard.get_poll_options_keyboard(poll['options'])
            )
            await state.set_state(self.Voting.choosing_option)

        except ValueError:
            await message.answer("🔢 Пожалуйста, введите корректный ID голосования.")
            return

    async def handle_choose_option(self, message: types.Message, state: FSMContext):
        """Обработка выбора варианта"""
        data = await state.get_data()
        poll_id = data['poll_id']
        poll = self.active_polls[poll_id]

        if message.text not in poll['options']:
            await message.answer(
                "⚠️ Пожалуйста, выберите вариант из предложенных.",
                reply_markup=keyboard.get_poll_options_keyboard(poll['options'])
            )
            return

        # Записываем голос
        poll['votes'][message.text] += 1
        poll['voted_users'].add(message.from_user.id)

        await message.answer(
            f"✅ Спасибо! Ваш голос '{message.text}' засчитан.",
            reply_markup=keyboard.get_start_keyboard()
        )
        await state.clear()
    # Система создания голосований
    async def handle_create_poll(self, message: types.Message, state: FSMContext):
        logger.log_message(message)

        if not await self._check_admin_rights(message):
            await self.show_main_menu(message)
            return

        await message.answer(
            "Введите название голосования:",
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

        poll_id = len(self.active_polls) + 1
        self.active_polls[poll_id] = {
            'title': poll_data['title'],
            'options': poll_data['options'],
            'creator_id': message.from_user.id,
            'end_time': end_time,
            'votes': {option: 0 for option in poll_data['options']},
            'voted_users': set()
        }

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

        for poll_id, poll in self.active_polls.items():
            total_votes = sum(poll['votes'].values())
            end_time = poll['end_time']
            time_left = end_time - datetime.now()

            if time_left.total_seconds() > 0:
                time_str = f"⏳ Осталось: {str(time_left).split('.')[0]}"
            else:
                time_str = "🔴 Голосование завершено"

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
                f"{time_str}\n"
                f"🗳 Всего голосов: {total_votes}\n"
                f"{options_stats}\n\n"
            )

        await message.answer(response)
        await self.show_main_menu(message)

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