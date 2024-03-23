from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
import emoji
import requests
import json

from functions import read_yaml
import keyboards

conf = read_yaml('config.yml')
dp = Dispatcher()


def recommend_car_wash(weather_dict):
    temperature_sum = 0
    humidity_sum = 0
    description_rain_count = 0
    for weather_iteration in weather_dict['list']:
        temperature_sum += weather_iteration['main']['temp'] - 273.15
        humidity_sum += weather_iteration['main']['humidity']
        if 'дождь' in weather_iteration['weather'][0]['description'].lower():
            description_rain_count += 1
    temperature_avg = temperature_sum / 40
    humidity_avg = humidity_sum / 40
    print(temperature_avg, humidity_avg, description_rain_count)
    description_now = weather_dict['list'][0]['weather'][0]['description']
    if -2 > temperature_avg > 2 and humidity_avg < 80 and description_rain_count < 10:
        return f"Сегодня можно мыть машину.\nПогода: {description_now}"
    else:
        return f"Лучше отложить мытьё машины на другой день.\nПогода: {description_now}"


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    print('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n\n{hbold('Мыть машину?')} - "
                           f"телеграм бот, который по запросу анализирует погоду (используется "
                           f"OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.\n\n"
                           f"Чтобы начать, отправьте свою геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.start_keyboard)


@dp.message(F.location)
async def handle_location(message: types.Message) -> None:
    print('Executing: handle_location')
    lat = message.location.latitude
    lon = message.location.longitude
    print(f"latitude:  {lat}\nlongitude: {lon}")
    # {'dt': 1710612000, 'main': {'temp': 277.71, 'feels_like': 274.98, 'temp_min': 273.44, 'temp_max': 277.71, 'pressure': 1022, 'sea_level': 1022, 
    # 'grnd_level': 1003, 'humidity': 95, 'temp_kf': 4.27}, 'weather': [{'id': 804, 'main': 'Clouds', 'description': 'пасмурно', 'icon': '04n'}], 
    # 'clouds': {'all': 100}, 'wind': {'speed': 3.2, 'deg': 180, 'gust': 7.39}, 'visibility': 10000, 'pop': 0, 'sys': {'pod': 'n'}, 'dt_txt': '2024-03-16 18:00:00'}
    response = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lang=ru&lat={lat}&lon={lon}&"
                           f"appid={conf['open_weather_token']}")
    weather_dict = json.loads(response.text)
    await message.answer(recommend_car_wash(weather_dict), parse_mode='HTML', reply_markup=keyboards.start_keyboard)
