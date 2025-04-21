from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class keyboard:
    @staticmethod
    def get_start_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Удалить/Завершить голосование")],
                [KeyboardButton(text="Создать голосование")],
                [KeyboardButton(text="Проголосовать")],
                [KeyboardButton(text="Статистика")],
                [KeyboardButton(text="Справка")],
            ],
            resize_keyboard=True
        )

    @staticmethod
    def get_cancel_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Отмена")],
            ],
            resize_keyboard=True
        )

    @staticmethod
    def get_poll_options_keyboard(options: list):
        return ReplyKeyboardMarkup(
            keyboard=[
                         [KeyboardButton(text=option)] for option in options
                     ] + [[KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )

    @staticmethod
    def get_confirm_keyboard():
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Удалить"), KeyboardButton(text="Завершить")],
                [KeyboardButton(text="Отмена")]
            ],
            resize_keyboard=True
        )