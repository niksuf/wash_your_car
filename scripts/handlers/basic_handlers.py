"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность базовых хэндлеров
"""

import logging
import json
import requests
import emoji
from aiogram import types, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold

# Импорты из текущей директории
import logger
import keyboards
from functions import read_yaml
from wash_functions import recommend_car_wash
import last_geo
import database_module

# Импорты из того же пакета (handlers)
from .rate_handlers import get_feedback_keyboard, save_forecast_to_db, get_last_car_wash_id

HELP_MESSAGE = emoji.emojize(f"\n{hbold('Мыть машину?')} - телеграм бот, который по запросу "
                             "анализирует погоду (используется OpenWeather) и дает совет, "
                             "целесообразно ли сегодня помыть машину.\n\n"
                             "/start - старт бота;\n"
                             "/restart - рестарт бота;\n"
                             "/help - открыть помощь;\n"
                             "/stats - статистика оценок.")
basic_router = Router()
logger.setup_logging()
conf = read_yaml('config.yml')
lat = -999
lon = -999


@basic_router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Ответ на команду /start
    """
    logging.debug('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n"
                           f"\n{hbold('Мыть машину?')} - телеграм бот, который по запросу "
                           "анализирует погоду (используется OpenWeather) и дает совет, "
                           "целесообразно ли сегодня помыть машину.\n\n"
                           "Чтобы начать, примите соглашение :newspaper: и отправьте свою "
                           "геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.start_keyboard)


@basic_router.message(F.text.startswith('Далее'))
async def agreement(message: Message) -> None:
    """
    Соглашение для использования персональных данных (обезличены)
    """
    logging.debug('Executing: agreement')
    await message.answer(
        text=emoji.emojize(f"{hbold('Мыть машину?')} анализирует данные об использовании бота, "
                           "в том числе об устройстве, на котором он функционирует, источник "
                           "установки, составляет конверсию и статистику вашей активности в "
                           "целях продуктовой аналитики, анализа и оптимизации рекламных "
                           "кампаний, а также для устранения ошибок. Собранная таким образом "
                           "информация не может идентифицировать вас."),
        parse_mode='HTML',
        reply_markup=keyboards.accept_agreement_keyboard)


@basic_router.message(F.text.startswith('Принять соглашение'))
async def work(message: Message) -> None:
    """
    Приглашение для отправки геопозиции
    """
    logging.debug('Executing: work')
    await message.answer(
        text=emoji.emojize("Чтобы получить прогноз, отправьте свою геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.second_keyboard
    )


@basic_router.message(Command(commands=['restart']))
async def command_restart_handler(message: Message) -> None:
    """
    Рестарт бота
    """
    logging.debug('Executing: restart_bot')
    await message.answer(text="Чтобы начать заново, отправьте мне команду /start.")


@basic_router.message(F.text.startswith('Помощь'))
async def show_help(message: Message) -> None:
    """
    Вывести справку по кнопке помощь
    """
    await message.answer(text=HELP_MESSAGE)


@basic_router.message(Command(commands=['help']))
async def show_help(message: Message) -> None:
    """
    Вывести справку по команде /help
    """
    await message.answer(text=HELP_MESSAGE)


@basic_router.message(F.location)
async def handle_location(message: types.Message) -> None:
    """
    Принимает геопозицию и присылает результат прогноза
    """
    global lat
    lat = message.location.latitude
    global lon
    lon = message.location.longitude
    user_id = message.from_user.id
    user_username = message.from_user.username
    logging.info("user_id:%s;username:%s;latitude:%s;longitude:%s",
                 user_id,
                 user_username,
                 lat,
                 lon)

    # Сохраняем геопозицию в основную таблицу
    conn, cur = database_module.connect_to_db(conf['db']['database_name'],
                                              conf['db']['user_name'],
                                              conf['db']['user_password'],
                                              conf['db']['host'])
    if conn and cur:
        last_geo_status = last_geo.check_last_geo(cur, user_id)
        if last_geo_status:
            last_geo.update_last_geo(conn, cur, user_id, lat, lon)
        elif last_geo_status is False:
            last_geo.insert_last_geo(conn,
                                    cur,
                                    'NULL',
                                    user_id,
                                    user_username,
                                    lat,
                                    lon,
                                    'NULL')
        database_module.close_connection_db(conn, cur)
    else:
        logging.info('Can not connect to database!')

    # Получаем прогноз погоды
    response = requests.get("https://api.openweathermap.org/data/2.5/"
                            f"forecast?lang=ru&lat={lat}&lon={lon}&"
                            f"appid={conf['open_weather_token']}",
                            timeout=10)
    weather_dict = json.loads(response.text)

    # Получаем рекомендацию
    recommendation_text = recommend_car_wash(weather_dict, lat, lon)
    location_name = weather_dict.get('city', {}).get('name', 'Неизвестно')

    # Отправляем сообщение с рекомендацией
    sent_message = await message.answer(
        text=emoji.emojize(f"{recommendation_text}\n\n:round_pushpin: Локация: {location_name}"),
        parse_mode='HTML'
    )

    # Получаем ID последней записи в car_washes
    car_wash_id = await get_last_car_wash_id(user_id)

    # Сохраняем прогноз в базу
    forecast_id = await save_forecast_to_db(
        user_id=user_id,
        car_wash_id=car_wash_id,
        weather_data=weather_dict,
        recommendation_text=recommendation_text,
        message_id=sent_message.message_id,
        location_name=location_name
    )

    # Добавляем кнопки оценки к сообщению (INLINE клавиатура)
    if forecast_id:
        await sent_message.edit_reply_markup(
            reply_markup=get_feedback_keyboard(forecast_id)
        )

    # ОТПРАВЛЯЕМ REPLY-КЛАВИАТУРУ ТОЛЬКО ЕСЛИ ЕЕ ЕЩЕ НЕТ
    # Просто удалите или закомментируйте этот блок, чтобы не отправлять "asd"
    # Если хотите отправлять меню только один раз, можно так:
    
    # Вариант 1: Не отправляем новое сообщение, оставляем существующую reply-клавиатуру
    # (просто удалите или закомментируйте блок ниже)
    
    # Вариант 2: Отправляем меню только если его нет
    # Проверьте, есть ли уже у пользователя активная reply-клавиатура
    # Это можно сделать через состояние или просто пропустить
    
    # Для простоты - просто удалите этот блок:
    # await message.reply(
    #     "asd",
    #     reply_markup=keyboards.second_keyboard
    # )


@basic_router.message(F.text == 'Использовать последнюю геопозицию')
async def use_old_location(message: types.Message) -> None:
    """
    Используя последнюю геопозицию присылает прогноз (берется из БД)
    """
    if 'Использовать последнюю геопозицию' in message.text:
        logging.debug('Executing: use_old_location')

        user_id = message.from_user.id
        conn, cur = database_module.connect_to_db(conf['db']['database_name'],
                                                  conf['db']['user_name'],
                                                  conf['db']['user_password'],
                                                  conf['db']['host'])
        if conn and cur:
            old_lat, old_lon = last_geo.get_last_geo(cur, user_id)
            database_module.close_connection_db(conn, cur)
        else:
            logging.error('Can not connect to database!')

        logging.info(f"latitude:  {old_lat}\nlongitude: {old_lon}")
        if old_lat and old_lon:
            response = requests.get("https://api.openweathermap.org/data/2.5/"
                                    f"forecast?lang=ru&lat={old_lat}&lon={old_lon}&"
                                    f"appid={conf['open_weather_token']}",
                                    timeout=10)
            weather_dict = json.loads(response.text)

            recommendation_text = recommend_car_wash(weather_dict, old_lat, old_lon)
            location_name = weather_dict.get('city', {}).get('name', 'Неизвестно')
            full_text = emoji.emojize(f"{recommendation_text}\n\n:round_pushpin: Локация: {location_name}")

            # Отправляем сообщение с рекомендацией
            sent_message = await message.answer(
                full_text,
                parse_mode='HTML'
            )

            # Получаем ID последней записи в car_washes
            car_wash_id = await get_last_car_wash_id(user_id)

            # Сохраняем прогноз в базу
            forecast_id = await save_forecast_to_db(
                user_id=user_id,
                car_wash_id=car_wash_id,
                weather_data=weather_dict,
                recommendation_text=recommendation_text,
                message_id=sent_message.message_id,
                location_name=location_name
            )

            # Добавляем кнопки оценки к сообщению
            if forecast_id:
                await sent_message.edit_reply_markup(
                    reply_markup=get_feedback_keyboard(forecast_id)
                )

            # УДАЛИТЬ этот блок - не отправляем новую reply-клавиатуру
            # await message.answer(
            #     "",
            #     reply_markup=keyboards.second_keyboard
            # )
        else:
            await message.answer("Нет данных о последней использованной геопозиции, "
                                 "для использования этой функции отправьте геопозицию!",
                                parse_mode='HTML',
                                reply_markup=keyboards.second_keyboard)
