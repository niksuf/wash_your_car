import logging

from aiogram import Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
import emoji
import requests
import json
import logger

import keyboards
from functions import read_yaml
from wash_functions import recommend_car_wash
import last_geo

logger.setup_logging()
conf = read_yaml('config.yml')
dp = Dispatcher()
lat = -999
lon = -999


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    print('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n\n{hbold('Мыть машину?')} - "
                           f"телеграм бот, который по запросу анализирует погоду (используется "
                           f"OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.\n\n"
                           f"Чтобы начать, примите соглашение :newspaper: и отправьте свою геопозицию "
                           f":round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.start_keyboard)


@dp.message(F.text.startswith('Далее'))
async def agreement(message: Message) -> None:
    print('Executing: agreement')
    await message.answer(
        text=emoji.emojize(f"{hbold('Мыть машину?')} анализирует данные об использовании бота, в том числе об "
                           f"устройстве, на котором он функционирует, источнике установки, составляет конверсию и "
                           f"статистику вашей активности в целях продуктовой аналитики, анализа и оптимизации "
                           f"рекламных кампаний, а также для устранения ошибок. Собранная таким образом информация "
                           f"не может идентифицировать вас."),
        parse_mode='HTML',
        reply_markup=keyboards.accept_agreement_keyboard)


@dp.message(F.text.startswith('Принять соглашение'))
async def work(message: Message) -> None:
    print('Executing: work')
    await message.answer(
        text=emoji.emojize(f"Чтобы получить прогноз, отправьте свою геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.send_position_keyboard)


@dp.message(Command(commands=['restart']))
async def command_restart_handler(message: Message) -> None:
    print('Executing: restart_bot')
    await message.answer("Чтобы начать заново, отправьте мне команду /start.")


@dp.message(F.location)
async def handle_location(message: types.Message) -> None:
    global lat
    lat = message.location.latitude
    global lon
    lon = message.location.longitude
    user_id = message.from_user.id
    user_username = message.from_user.username
    logging.info(f"user_id:{user_id};username:{user_username};latitude:{lat};longitude:{lon}")

    conn, cur = last_geo.connect_to_db(conf['db']['database_name'],
                                      conf['db']['user_name'],
                                      conf['db']['user_password'],
                                      conf['db']['host'])
    if conn and cur:
        last_geo_status = last_geo.check_last_geo(cur, user_id)
        if last_geo_status:
            last_geo.update_last_geo(conn, cur, user_id, lat, lon)
        elif last_geo_status is False:
            # TODO: fix hardcode for date and time
            last_geo.insert_last_geo(conn,
                                    cur,
                                    '2024-05-20',
                                    user_id,
                                    user_username,
                                    lat,
                                    lon,
                                    '14:00:00')
        last_geo.close_connection_db(conn, cur)
    else:
        logging.info(f'Can not connect to database!')

    response = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lang=ru&lat={lat}&lon={lon}&"
                           f"appid={conf['open_weather_token']}")
    weather_dict = json.loads(response.text)
    await message.answer(recommend_car_wash(weather_dict, lat, lon), parse_mode='HTML', reply_markup=keyboards.second_keyboard)


@dp.message()
async def use_old_location(message: types.Message) -> None:
    if 'Использовать последнюю геолокацию' in message.text:
        print('Executing: use_old_location')

        user_id = message.from_user.id
        conn, cur = last_geo.connect_to_db(conf['db']['database_name'],
                                      conf['db']['user_name'],
                                      conf['db']['user_password'],
                                      conf['db']['host'])
        if conn and cur:
            old_lat, old_lon = last_geo.get_last_geo(cur, user_id)
            last_geo.close_connection_db(conn, cur)
        else:
            logging.info(f'Can not connect to database!')

        print(f"latitude:  {old_lat}\nlongitude: {old_lon}")
        if old_lat and old_lon:
            response = requests.get(f"https://api.openweathermap.org/data/2.5/forecast?lang=ru&lat={old_lat}&lon={old_lon}&"
                                    f"appid={conf['open_weather_token']}")
            weather_dict = json.loads(response.text)
            await message.answer(recommend_car_wash(weather_dict, old_lat, old_lon) + f"\nТекущая локация: {weather_dict['city']['name']}",
                                parse_mode='HTML', reply_markup=keyboards.second_keyboard)
        else:
            await message.answer('Нет данных о последней использованной геолокации, для использования этой функции отправьте геолокацию!',
                                parse_mode='HTML', reply_markup=keyboards.second_keyboard)
