"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Вспомогательные функции
"""

import yaml


def read_yaml(filename) -> dict:
    """
    Читает yaml конфиг из файла, возвращает словарь
    """
    try:
        with open(filename) as file:
            data = yaml.load(file, Loader=yaml.CLoader)
        return data
    except FileNotFoundError:
        print(f'Config file {filename} not found!')
        exit()
