from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

class keyboard:
    @staticmethod
    def get_start_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Удалить")],
                [KeyboardButton(text="Создать голосование")],
                [KeyboardButton(text="Проголосовать")],
                [KeyboardButton(text="Статистика")],
                [KeyboardButton(text="Справка")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @staticmethod
    def get_cancel_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @staticmethod
    def get_poll_options_keyboard(options: list):
        """Создает клавиатуру с вариантами голосования и кнопкой отмены"""
        buttons = [
            [KeyboardButton(text=option)] for option in options
        ]
        buttons.append([KeyboardButton(text="Отмена")])

        return ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            one_time_keyboard=True
        )