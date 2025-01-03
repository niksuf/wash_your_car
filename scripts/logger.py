"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функции логирования
"""

import logging
import logging.config
from pathlib import Path
import functions

conf = functions.read_yaml('config.yml')


def setup_logging():
    """
    Настраивает логирование при вызове из другого файла
    """
    logging_format = "[%(asctime)s:%(funcName)s] <%(levelname)s> %(message)s"
    Path(conf['logs']['logs_dir']).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
                        filename=f"{conf['logs']['logs_dir']}/{conf['logs']['logs_file']}",
                        format=logging_format)
