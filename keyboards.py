from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import emoji

send_position = KeyboardButton(text=emoji.emojize('Отправить геопозицию :round_pushpin:'), request_location=True)
start_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position]], resize_keyboard=True)
