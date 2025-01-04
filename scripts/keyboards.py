"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Вспомогательный файл для хранения переменных клавиатур
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import emoji

# Кнопка помощь
help_button = KeyboardButton(text='Помощь')

# Приветственная клавиатура
next_button = KeyboardButton(text=emoji.emojize('Далее :right_arrow:'))
start_keyboard = ReplyKeyboardMarkup(keyboard=[[next_button],
                                               [help_button]],
                                     resize_keyboard=True)

# Клавиатура соглашения
accept_agreement = KeyboardButton(
    text=emoji.emojize('Принять соглашение :newspaper:'))
accept_agreement_keyboard = ReplyKeyboardMarkup(keyboard=[[accept_agreement],
                                                          [help_button]],
                                                resize_keyboard=True)

# Клавиатура для отправки геопозиции
send_position = KeyboardButton(text=emoji.emojize(
    'Отправить геопозицию :round_pushpin:'), request_location=True)
send_position_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position],
                                                       [help_button]],
                                             resize_keyboard=True)

# Клавиатура для отправки геопозиции или использования старой
use_old_position = KeyboardButton(text=emoji.emojize('Использовать последнюю геопозицию'))
second_keyboard = ReplyKeyboardMarkup(
    keyboard=[[send_position],
              [use_old_position],
              [help_button]],
    resize_keyboard=True)
