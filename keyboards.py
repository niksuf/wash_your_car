from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import emoji

# 1st keyboard
send_position = KeyboardButton(text=emoji.emojize('Отправить геопозицию :round_pushpin:'), request_location=True)
start_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position]], resize_keyboard=True)

# 2nd keyboard
use_old_position = KeyboardButton(text=emoji.emojize('Использовать старую геолокацию'))
second_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position], [use_old_position]], resize_keyboard=True)
