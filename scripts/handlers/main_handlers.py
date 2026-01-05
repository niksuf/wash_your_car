"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Подключение хэндлеров (роутеров)
"""

from aiogram import Dispatcher
from .basic_handlers import basic_router
from .statistics_handlers import statistics_router
from .rate_handlers import rate_router

# Создаем главный диспетчер
dp = Dispatcher()

# Включаем все роутеры
dp.include_router(basic_router)
dp.include_router(statistics_router)
dp.include_router(rate_router)
