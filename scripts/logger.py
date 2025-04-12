"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функции логирования
"""

import logging
from pathlib import Path
import datetime
import functions

conf = functions.read_yaml('config.yml')

def setup_logging():
    """
    Настраивает логирование с учётом даты в имени файла.
    Автоматически создаёт новый файл при смене даты.
    """
    logging_format = "[%(asctime)s:%(funcName)s] <%(levelname)s> %(message)s"

    logs_dir = conf.get('logs', {}).get('logs_dir', 'logs')
    logs_file = conf.get('logs', {}).get('logs_file', 'app.log')

    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    if not logs_file:
        logs_file = "app.log"

    original_log = Path(logs_file)

    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    log_filename = f"{original_log.stem}_{current_date}{original_log.suffix}"

    log_path = logs_path / log_filename

    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        format=logging_format
    )
