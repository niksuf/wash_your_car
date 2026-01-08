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
import logging
import logger

logger.setup_logging()

# Порог для принятия решения по температуре (например, 35%)
TEMPERATURE_TRESHOLD = 0.35

# Константы для зимней логики
SNOW_THRESHOLD = 0.1  # мм снега за 3 часа
ICE_TEMP_THRESHOLD = 3  # °C - температура при которой возможен гололёд
WINTER_MODE_THRESHOLD = 5  # °C - ниже этой температуры включается зимняя логика
WIND_DIRT_THRESHOLD = 7  # м/с, ветер при котором грязь будет лететь на машину
REAGENT_WASH_INTERVAL = 3  # дня - как часто мыть при использовании реагентов


def format_date(date):
    """ Функция форматирования даты """
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    return date


def get_timezone(lat, lon):
    """ Функция получения часового пояса из широты и долготы """
    tmezone_finder = TimezoneFinder()
    timezone_str = tmezone_finder.timezone_at(lng=lon, lat=lat)
    return timezone_str


def convert_time(utc_time_str, lat, lon):
    """ Функция конвертирования времени в строку """
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
    """ Функция для сворачивания временных интервалов в диапазоны """
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


def _is_winter_condition(current_temp, month=None):
    """ Определяет, является ли условие зимним """
    if month is None:
        month = datetime.now().month
    # Зима с ноября по март, или если температура ниже порога
    return month in [11, 12, 1, 2, 3] or current_temp < WINTER_MODE_THRESHOLD


def _get_reagent_advice(current_temp):
    """ Возвращает рекомендации по мойке для городов с реагентами """
    advice = []

    # Основные советы для городов с реагентами
    advice.append(emoji.emojize(":warning: Внимание! На дорогах могут использоваться реагенты."))
    if current_temp < 0:
        advice.append(emoji.emojize(":droplet: Частая мойка кузова защищает от коррозии"))
    else:
        advice.append(emoji.emojize(":thermometer: При плюсовой температуре реагенты смываются дождём"))
    advice.append(emoji.emojize(f":alarm_clock: Рекомендуем мыть каждые {REAGENT_WASH_INTERVAL} дня"))

    return "\n".join(advice)


def _analyze_winter_conditions(weather_dict, lat, lon, current_temp):
    """ Анализ зимних условий с учётом реагентов """
    winter_warnings = []
    good_windows = []

    temperatures = []
    snow_accumulation = 0
    current_window_start = None
    window_duration = 0

    # Анализируем ближайшие 48 часов (16 интервалов по 3 часа)
    for _, weather_iteration in enumerate(weather_dict['list'][:16]):
        temp = weather_iteration['main']['temp'] - 273.15
        description = weather_iteration['weather'][0]['description'].lower()
        snow = weather_iteration.get('snow', {}).get('3h', 0)
        wind_speed = weather_iteration.get('wind', {}).get('speed', 0)

        temperatures.append(temp)
        snow_accumulation += snow

        # Проверяем условия для гололёда
        is_freezing_risk = (temp < ICE_TEMP_THRESHOLD and 
                           ('дождь' in description or 'снег' in description or 
                            'мокрый' in description) and
                           temp > -20)

        # Проверяем, можно ли мыть в этом интервале
        can_wash_now = (
            temp > -20 and  # Убрали нижний порог -10
            temp < 5 and  # не слишком тепло для слякоти
            snow < SNOW_THRESHOLD and
            'дождь' not in description and
            'снег' not in description and
            not is_freezing_risk and
            wind_speed < WIND_DIRT_THRESHOLD
        )

        # Отслеживаем "окна" хорошей погоды
        if can_wash_now:
            if current_window_start is None:
                current_window_start = weather_iteration['dt_txt']
                window_duration = 3
            else:
                window_duration += 3
        else:
            if current_window_start and window_duration >= 6:  # минимум 6 часов
                start_time = convert_time(current_window_start, lat, lon)
                # Для температурного диапазона нужно сохранять температуры окон
                window_temps = temperatures[-window_duration//3:]
                good_windows.append({
                    'start': start_time,
                    'duration': window_duration,
                    'temp_range': f"{min(window_temps):.1f}...{max(window_temps):.1f}°C",
                })
            current_window_start = None
            window_duration = 0

    # Добавляем последнее окно если есть
    if current_window_start and window_duration >= 6:
        start_time = convert_time(current_window_start, lat, lon)
        window_temps = temperatures[-window_duration//3:]
        good_windows.append({
            'start': start_time,
            'duration': window_duration,
            'temp_range': f"{min(window_temps):.1f}...{max(window_temps):.1f}°C",
        })

    # Предупреждение о снеге
    if snow_accumulation > 1.0:
        winter_warnings.append(emoji.emojize(f":snowflake: Ожидается снег: {snow_accumulation:.1f} мм"))

    # Предупреждение о сильном ветре
    max_wind = max([w.get('wind', {}).get('speed', 0) for w in weather_dict['list'][:8]])
    if max_wind > WIND_DIRT_THRESHOLD:
        winter_warnings.append(emoji.emojize(f":dashing_away: Сильный ветер: до {max_wind} м/с"))

    # Добавляем предупреждение о реагентах если зима
    if current_temp < 5:
        reagent_warning = emoji.emojize(":triangular_flag: Внимание: на дорогах могут быть реагенты!")
        winter_warnings.append(reagent_warning)

    return winter_warnings, good_windows


def _get_winter_wash_advice(best_window):
    """ Генерирует советы для зимней мойки """
    advice_lines = []
    advice_lines.append(emoji.emojize(":sunny: Условия подходящие для мойки"))

    if best_window:
        advice_lines.append(emoji.emojize(f":alarm_clock: Лучшее время мойки: {best_window['start']} (на {best_window['duration']}ч)"))
        advice_lines.append(emoji.emojize(f":thermometer: Температура: {best_window['temp_range']}"))

    return "\n".join(advice_lines)


def recommend_car_wash(weather_dict, lat, lon):
    """ Функция принятия решения о целесообразности
    мытья машины с учётом зимних условий и реагентов """
    temperature_sum = 0
    humidity_sum = 0
    rain_probability = []
    weather_bad = []
    snow_accumulation = 0
    temperatures = []

    logging.info(f"len weather_dict['list'] {len(weather_dict['list'])}")

    for weather_iteration in weather_dict['list']:
        temp = weather_iteration['main']['temp'] - 273.15
        temperature_sum += temp
        temperatures.append(temp)
        humidity_sum += weather_iteration['main']['humidity']

        # Вероятность дождя
        rain_prob = weather_iteration.get('rain', {}).get('3h', 0)
        rain_probability.append(rain_prob if rain_prob is not None else 0)

        # Количество снега
        snow = weather_iteration.get('snow', {}).get('3h', 0)
        snow_accumulation += snow

        # Проверяем неблагоприятные условия
        description = weather_iteration['weather'][0]['description'].lower()
        if any(keyword in description for keyword in ['дождь', 'снег', 'ливень', 'мокрый снег', 'изморось']):
            weather_bad.append(weather_iteration['dt_txt'])

    temperature_avg = temperature_sum / len(weather_dict['list'])
    humidity_avg = humidity_sum / len(weather_dict['list'])
    current_temp = temperatures[0]

    logging.info(f"temperature_avg, humidity_avg: {temperature_avg}, {humidity_avg}")
    description_now = weather_dict['list'][0]['weather'][0]['description']

    # Создаем массив весов
    weights = np.exp(np.linspace(0, -3, len(weather_dict['list'])))
    # Нормализуем веса
    weights /= sum(weights)
    # Вычисляем взвешенную вероятность дождя
    weighted_rain_probability = np.dot(rain_probability, weights)

    # Определяем, зимний ли режим
    is_winter = _is_winter_condition(current_temp)

    # ЗИМНЯЯ ЛОГИКА
    if is_winter:
        winter_warnings, good_windows = _analyze_winter_conditions(
            weather_dict, lat, lon, current_temp
        )

        # Проверяем ближайшие 24 часа на осадки (зимняя версия)
        has_precipitation_next_24h = False
        precip_times = []

        for weather_iteration in weather_dict['list'][:8]:
            description = weather_iteration['weather'][0]['description'].lower()
            if any(keyword in description for keyword in ['дождь', 'снег', 'ливень', 'мокрый снег']):
                has_precipitation_next_24h = True
                precip_times.append(weather_iteration['dt_txt'])

        if has_precipitation_next_24h:
            current_zone_time = [convert_time(t, lat, lon) for t in precip_times]
            collapsed_intervals = collapse_time_intervals(current_zone_time)
            collapsed_intervals_str = '\n'.join(collapsed_intervals)

            winter_info = ""
            if winter_warnings:
                winter_info = "\n" + "\n".join(winter_warnings[:3])
            return emoji.emojize(f":snowflake: Зимний режим\n"
                               f"Лучше отложить мытьё машины.\n\n"
                               f":cloud_with_snow: Осадки в ближайшие часы:\n"
                               f"{collapsed_intervals_str}"
                               f"{winter_info}\n\n"
                               f":thermometer: Средняя температура: {temperature_avg:.1f}°C\n"
                               f":snowflake: Накопление снега: {snow_accumulation:.1f} мм")

        # Если есть хорошие окна для мойки зимой
        if good_windows:
            best_window = max(good_windows, key=lambda x: x['duration'])
            winter_advice = _get_winter_wash_advice(best_window)

            winter_info = ""
            if winter_warnings:
                winter_info = "\n" + "\n".join(winter_warnings[:2])

            return emoji.emojize(f"{winter_advice}"
                               f"{winter_info}\n\n"
                               f":sun_behind_cloud: Погода сейчас: {description_now}\n"
                               f":cloud_with_rain: Вероятность осадков: {weighted_rain_probability:.1f}%")

        # Если зима, но нет хороших окон
        winter_info = ""
        if winter_warnings:
            winter_info = "\n" + emoji.emojize(":snowflake: Зимние условия:") + "\n" + "\n".join(winter_warnings[:3])
        return emoji.emojize(f":snowflake: Зимний режим\n"
                           f"Сегодня не лучшее время для мойки.\n"
                           f"{winter_info}\n\n"
                           f":thermometer: Средняя температура: {temperature_avg:.1f}°C\n"
                           f":snowflake: Накопление снега: {snow_accumulation:.1f} мм\n"
                           f":sweat_drops: Влажность: {humidity_avg:.0f}%")

    # СТАНДАРТНАЯ ЛОГИКА (как было, но с улучшениями)
    # Проверка на наличие дождя в ближайшие часы
    # ближайшие 24 часа (8 * 3 часа)
    for weather_iteration in weather_dict['list'][:8]:
        if 'дождь' in weather_iteration['weather'][0]['description'].lower():
            current_zone_time = []
            for weather_time_iteration in weather_bad:
                current_zone_time.append(convert_time(weather_time_iteration, lat, lon))
            collapsed_intervals = collapse_time_intervals(current_zone_time)
            collapsed_intervals_str = '\n'.join(collapsed_intervals)

            # Добавляем информацию о температуре для зимнего контекста
            temp_info = ""
            if current_temp < 5:
                temp_info = emoji.emojize(f"\n:thermometer: Температура низкая: {current_temp:.1f}°C")

            return emoji.emojize(f":cloud_with_rain: Лучше отложить мытьё машины на другой день.\n\n"
                               f"Краткая погодная сводка:\n"
                               f":cloud_with_rain: Взвешенная вероятность дождя: "
                               f"{weighted_rain_probability:.2f}%\n"
                               f":alarm_clock: Дождь в ближайшие часы:\n"
                               f"{collapsed_intervals_str}"
                               f"{temp_info}")

    # Улучшенное условие с учётом температуры
    is_safe_temp = not (-2 < temperature_avg < 2)  # Избегаем температуры около 0°C

    # Учитываем ветер (сильный ветер = быстрое загрязнение)
    wind_speed = weather_dict['list'][0].get('wind', {}).get('speed', 0)
    wind_emoji = emoji.emojize(" :dashing_away:") if wind_speed > 6 else ""

    if (weighted_rain_probability <= TEMPERATURE_TRESHOLD and 
        humidity_avg < 80 and 
        is_safe_temp):

        # Дополнительные советы в зависимости от температуры
        temp_advice = ""
        if current_temp < 5:
            temp_advice = emoji.emojize("\n:warning: Температура низкая - используйте горячую воду и просушите замки и уплотнители!")

        return emoji.emojize(f":soap: Сегодня можно мыть машину.{wind_emoji}\n"
                           f":sun_behind_cloud: Погода: {description_now}\n"
                           f":thermometer: Температура: {current_temp:.1f}°C"
                           f"{temp_advice}")

    # Если не рекомендуется мыть
    current_zone_time = []
    for weather_time_iteration in weather_bad:
        current_zone_time.append(convert_time(weather_time_iteration, lat, lon))
    collapsed_intervals = collapse_time_intervals(current_zone_time)
    collapsed_intervals_str = '\n'.join(collapsed_intervals)

    # Анализируем причину отказа
    reasons = []
    if weighted_rain_probability > TEMPERATURE_TRESHOLD:
        reasons.append(emoji.emojize(f":cloud_with_rain: высокая вероятность осадков ({weighted_rain_probability:.1f}%)"))
    if humidity_avg >= 80:
        reasons.append(emoji.emojize(f":sweat_drops: высокая влажность ({humidity_avg:.0f}%)"))
    if not is_safe_temp:
        reasons.append(emoji.emojize(f":thermometer: температура около 0°C ({temperature_avg:.1f}°C)"))

    reason_text = ""
    if reasons:
        reason_text = "\n" + emoji.emojize(":exclamation: Причины:") + "\n" + "\n".join(reasons)

    # Если холодно, но не зима по определению, все равно предупреждаем о возможных реагентах
    reagent_note = ""
    if current_temp < 10:
        reagent_note = emoji.emojize("\n\n:triangular_flag: Примечание: при температуре ниже 10°C на дорогах могут быть реагенты")

    return emoji.emojize(f":cloud_with_rain: Лучше отложить мытьё машины на другой день.\n\n"
                       f"Краткая погодная сводка:\n"
                       f":cloud_with_rain: Взвешенная вероятность дождя: "
                       f"{weighted_rain_probability:.2f}%\n"
                       f":alarm_clock: Осадки в ближайшие дни:\n"
                       f"{collapsed_intervals_str}\n\n"
                       f":thermometer: Средняя температура: {round(temperature_avg, 1)}°C\n"
                       f":thermometer: Температура сейчас: {current_temp:.1f}°C\n"
                       f":sweat_drops: Средняя влажность: {humidity_avg:.0f}%"
                       f"{reason_text}"
                       f"{reagent_note}")


# Дополнительная функция для определения сезона
def get_season_emoji(lat, month=None):
    """ Возвращает эмодзи сезона по широте и месяцу """
    if month is None:
        month = datetime.now().month

    # Для северного полушария
    if lat >= 0:
        if month in [12, 1, 2]:
            return emoji.emojize(":snowflake:")
        elif month in [3, 4, 5]:
            return emoji.emojize(":cherry_blossom:")
        elif month in [6, 7, 8]:
            return emoji.emojize(":sun_with_face:")
        else:
            return emoji.emojize(":fallen_leaf:")
    # Для южного полушария
    else:
        if month in [12, 1, 2]:
            return emoji.emojize(":sun_with_face:")
        elif month in [3, 4, 5]:
            return emoji.emojize(":fallen_leaf:")
        elif month in [6, 7, 8]:
            return emoji.emojize(":snowflake:")
        else:
            return emoji.emojize(":cherry_blossom:")
