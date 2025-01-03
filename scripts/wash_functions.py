"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность для анализа погоды и и вывода стоит ли мыть машину
"""

import locale
from datetime import datetime
from timezonefinder import TimezoneFinder
import pytz
import emoji
import numpy as np

# Порог для принятия решения по температуре (например, 35%)
TEMPERATURE_TRESHOLD = 0.35


def format_date(date):
    """
    Функция форматирования даты
    """
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    return date


def get_timezone(lat, lon):
    """
    Функция получения часового пояса из широты и долготы
    """
    tmezone_finder = TimezoneFinder()
    timezone_str = tmezone_finder.timezone_at(lng=lon, lat=lat)
    return timezone_str


def convert_time(utc_time_str, lat, lon):
    """
    Функция конвертирования времени в строку
    """
    # Определение временной зоны
    timezone_str = get_timezone(lat, lon)
    if timezone_str:
        # Время по UTC
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        # Преобразование времени из UTC в местное время с учетом указанной временной зоны
        timezone = pytz.timezone(timezone_str)
        local_time = pytz.utc.localize(utc_time).astimezone(timezone)
        # Локализация даты
        local_time = format_date(local_time)
        # Преобразование объекта времени в строку без информации о смещении временной зоны
        local_time_str = local_time.strftime('%d %b %H:%M')
        return local_time_str
    return "Не удалось определить временную зону."


def collapse_time_intervals(current_zone_time):
    """
    Функция для сворачивания временных интервалов в диапазоны
    """
    collapse_time = []
    start_time = None
    prev_time_iter = None
    for weather_time_iteration in current_zone_time:
        time_iteration = datetime.strptime(weather_time_iteration, '%d %b %H:%M')
        if start_time is None:
            start_time = time_iteration
            prev_time_iter = time_iteration
        elif (time_iteration - prev_time_iter).total_seconds() <= 3 * 3600:
            prev_time_iter = time_iteration
        else:
            if start_time == prev_time_iter:
                collapse_time.append(start_time.strftime('%d %b %H:%M'))
            else:
                collapse_time.append(start_time.strftime('%d %b %H:%M') + \
                                     ' - ' + prev_time_iter.strftime('%H:%M'))
            start_time = time_iteration
            prev_time_iter = time_iteration
    if start_time is not None:
        if start_time == prev_time_iter:
            collapse_time.append(start_time.strftime('%d %b %H:%M'))
        else:
            collapse_time.append(start_time.strftime('%d %b %H:%M') + \
                                 ' - ' + prev_time_iter.strftime('%H:%M'))
    return collapse_time


def recommend_car_wash(weather_dict, lat, lon):
    """
    Функция принятия решения о целесообразности мытья машины
    """
    temperature_sum = 0
    humidity_sum = 0
    rain_probability = []
    weather_bad = []

    print(len(weather_dict['list']))
    for weather_iteration in weather_dict['list']:
        temperature_sum += weather_iteration['main']['temp'] - 273.15
        humidity_sum += weather_iteration['main']['humidity']
        rain_prob = weather_iteration.get('rain', {}).get('3h', 0)  # вероятность дождя в процентах
        rain_probability.append(rain_prob if rain_prob is not None else 0)
        if 'дождь' in weather_iteration['weather'][0]['description'].lower():
            weather_bad.append(weather_iteration['dt_txt'])

    temperature_avg = temperature_sum / 40
    humidity_avg = humidity_sum / 40
    print(temperature_avg, humidity_avg)
    description_now = weather_dict['list'][0]['weather'][0]['description']

    # Создаем массив весов
    weights = np.exp(np.linspace(0, -3, 40))
    # Нормализуем веса
    weights /= sum(weights)
    # Вычисляем взвешенную вероятность дождя
    weighted_rain_probability = np.dot(rain_probability, weights)
    # Проверка на наличие дождя в ближайшие часы
    # ближайшие 24 часа (8 * 3 часа)
    for weather_iteration in weather_dict['list'][:8]:
        if 'дождь' in weather_iteration['weather'][0]['description'].lower():
            current_zone_time = []
            for weather_time_iteration in weather_bad:
                current_zone_time.append(convert_time(weather_time_iteration, lat, lon))
            collapsed_intervals = collapse_time_intervals(current_zone_time)
            collapsed_intervals_str = '\n'.join(collapsed_intervals)
            return emoji.emojize(f"Лучше отложить мытьё машины на другой день.\n:cloud_with_rain: "
                                 f"Взвешенная вероятность дождя: {weighted_rain_probability:.2f}%\n"
                                 f"Дождь в ближайшие часы:\n"
                                 f"{collapsed_intervals_str}")

    if weighted_rain_probability <= TEMPERATURE_TRESHOLD and \
       humidity_avg < 80 and \
       not -2 < temperature_avg < 2:
        return emoji.emojize(f"Сегодня можно мыть машину. :soap:\nПогода: {description_now}")

    current_zone_time = []
    for weather_time_iteration in weather_bad:
        current_zone_time.append(convert_time(weather_time_iteration, lat, lon))
    collapsed_intervals = collapse_time_intervals(current_zone_time)
    collapsed_intervals_str = '\n'.join(collapsed_intervals)
    return emoji.emojize(f"Лучше отложить мытьё машины на другой день.\n\n:cloud_with_rain: "
                            f"Взвешенная вероятность дождя: {weighted_rain_probability:.2f}%\n"
                            "Дождь в ближайшие дни:\n"
                            f"{collapsed_intervals_str}\n\n"
                            f"Средняя температура: {round(temperature_avg, 1)}\n"
                            f"Средняя влажность: {humidity_avg}")
