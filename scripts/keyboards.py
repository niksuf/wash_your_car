from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import emoji

# first keyboard
next_button = KeyboardButton(text=emoji.emojize('Далее :right_arrow:'))
start_keyboard = ReplyKeyboardMarkup(keyboard=[[next_button]], resize_keyboard=True)

# agreement keyboard
accept_agreement = KeyboardButton(text=emoji.emojize('Принять соглашение :newspaper:'))
accept_agreement_keyboard = ReplyKeyboardMarkup(keyboard=[[accept_agreement]], resize_keyboard=True)

# position keyboard
send_position = KeyboardButton(text=emoji.emojize('Отправить геопозицию :round_pushpin:'), request_location=True)
send_position_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position]], resize_keyboard=True)

# old position keyboard
use_old_position = KeyboardButton(text=emoji.emojize('Использовать последнюю геолокацию'))
second_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position], [use_old_position]], resize_keyboard=True)
