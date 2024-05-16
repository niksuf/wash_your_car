from timezonefinder import TimezoneFinder
from datetime import datetime
import pytz
import locale
import emoji


def get_timezone(lat, lon):
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lng=lon, lat=lat)
    return timezone_str


def convert_time(utc_time_str, lat, lon):
    # Определение временной зоны
    timezone_str = get_timezone(lat, lon)
    if timezone_str:
        # Время по UTC
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        # Преобразование времени из UTC в местное время с учетом указанной временной зоны
        timezone = pytz.timezone(timezone_str)
        local_time = pytz.utc.localize(utc_time).astimezone(timezone)
        # Преобразование объекта времени в строку без информации о смещении временной зоны
        local_time_str = local_time.strftime('%d %b %H:%M')
        return local_time_str
    else:
        return "Не удалось определить временную зону."


def collapse_time_intervals(current_zone_time):
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
                collapse_time.append(start_time.strftime('%d %b %H:%M') + ' - ' + prev_time_iter.strftime('%H:%M'))
            start_time = time_iteration
            prev_time_iter = time_iteration
    if start_time is not None:
        if start_time == prev_time_iter:
            collapse_time.append(start_time.strftime('%d %b %H:%M'))
        else:
            collapse_time.append(start_time.strftime('%d %b %H:%M') + ' - ' + prev_time_iter.strftime('%H:%M'))
    return collapse_time


def recommend_car_wash(weather_dict, lat, lon):
    temperature_sum = 0
    humidity_sum = 0
    description_rain_count = 0
    weather_bad = []

    for weather_iteration in weather_dict['list']:
        temperature_sum += weather_iteration['main']['temp'] - 273.15
        humidity_sum += weather_iteration['main']['humidity']
        if 'дождь' in weather_iteration['weather'][0]['description'].lower():
            description_rain_count += 1
            weather_bad.append(weather_iteration['dt_txt'])

    temperature_avg = temperature_sum / 40
    humidity_avg = humidity_sum / 40
    print(temperature_avg, humidity_avg, description_rain_count)
    description_now = weather_dict['list'][0]['weather'][0]['description']
    if not (-2 > temperature_avg > 2) and humidity_avg < 80 and description_rain_count < 10:
        return emoji.emojize(f"Сегодня можно мыть машину. :soap:\nПогода: {description_now}")
    else:
        current_zone_time = []
        for weather_time_iteration in weather_bad:
            current_zone_time.append(convert_time(weather_time_iteration, lat, lon))

        collapsed_intervals = collapse_time_intervals(current_zone_time)
        collapsed_intervals_str = '\n'.join(collapsed_intervals)
        return emoji.emojize(f"Лучше отложить мытьё машины на другой день.\n:cloud_with_rain: "
                             f"Дождь в ближайшие дни:\n"
                             f"{collapsed_intervals_str}")
