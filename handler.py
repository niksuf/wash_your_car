from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
import emoji
import requests

from functions import read_yaml
import keyboards

conf = read_yaml('config.yml')
dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    print('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n\n{hbold('Мыть машину?')} - "
                           f"телеграм бот, который по запросу анализирует погоду (используется "
                           f"Яндекс.Погода) и дает совет, целесообразно ли сегодня помыть машину.\n\n"
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
    print(response.json()['list'][1])
