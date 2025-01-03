"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Основной скрипт для запуска бота
"""

import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from functions import read_yaml
from handler import dp

conf = read_yaml('config.yml')
bot = Bot(conf['telegram_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def main() -> None:
    """
    Функция стартует бота
    """
    print('Bot started!')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
