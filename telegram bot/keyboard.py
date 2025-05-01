from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class keyboard:
    @staticmethod
    def get_start_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Удалить")],
                [KeyboardButton(text="Создать голосование")],
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