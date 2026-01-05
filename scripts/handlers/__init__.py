"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Пакет хэндлеров
"""

from .basic_handlers import basic_router
from .statistics_handlers import statistics_router
from .rate_handlers import rate_router
from .main_handlers import dp

__all__ = ['dp', 'basic_router', 'statistics_router', 'rate_router']
