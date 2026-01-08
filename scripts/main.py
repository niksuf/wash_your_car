"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Основной скрипт для запуска бота
"""

import asyncio
import sys
import os
import logging
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties

# Добавляем родительскую директорию в sys.path для корректного импорта
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from functions import read_yaml
from scripts.handlers.main_handlers import dp
import logger

logger.setup_logging()
conf = read_yaml('config.yml')
bot = Bot(conf['telegram_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def main() -> None:
    """ Функция стартует бота """
    logging.info('Bot started!')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
