"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность хэндлеров
"""

import logging
import json
import requests
import emoji
from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.markdown import hbold
import logger
from . import payment_handlers

import keyboards
from functions import read_yaml
from wash_functions import recommend_car_wash
import last_geo

HELP_MESSAGE = emoji.emojize(f"\n{hbold('Мыть машину?')} - телеграм бот, который по запросу "
                             "анализирует погоду (используется OpenWeather) и дает совет, "
                             "целесообразно ли сегодня помыть машину.\n\n"
                             "/start - старт бота;\n"
                             "/restart - рестарт бота;\n"
                             "/help - открыть помощь.")

logger.setup_logging()
conf = read_yaml('config.yml')
dp = Dispatcher()
lat = -999
lon = -999


def register_handlers(dp: Dispatcher):
    # Регистрируем обработчик для кнопки "Купить премиум"
    dp.message.register(payment_handlers.send_invoice_handler, F.text == 'Купить премиум 💎')
    dp.pre_checkout_query.register(payment_handlers.pre_checkout_handler)
    dp.message.register(payment_handlers.success_payment_handler, F.successful_payment)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Ответ на команду /start
    """
    print('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n"
                           f"\n{hbold('Мыть машину?')} - телеграм бот, который по запросу "
                           "анализирует погоду (используется OpenWeather) и дает совет, "
                           "целесообразно ли сегодня помыть машину.\n\n"
                           "Чтобы начать, примите соглашение :newspaper: и отправьте свою "
                           "геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.start_keyboard)


@dp.message(F.text.startswith('Далее'))
async def agreement(message: Message) -> None:
    """
    Соглашение для использования персональных данных (обезличены)
    """
    print('Executing: agreement')
    await message.answer(
        text=emoji.emojize(f"{hbold('Мыть машину?')} анализирует данные об использовании бота, "
                           "в том числе об устройстве, на котором он функционирует, источнике "
                           "установки, составляет конверсию и статистику вашей активности в "
                           "целях продуктовой аналитики, анализа и оптимизации рекламных "
                           "кампаний, а также для устранения ошибок. Собранная таким образом "
                           "информация не может идентифицировать вас."),
        parse_mode='HTML',
        reply_markup=keyboards.accept_agreement_keyboard)


@dp.message(F.text.startswith('Принять соглашение'))
async def work(message: Message) -> None:
    """
    Приглашение для отправки геопозиции
    """
    print('Executing: work')
    await message.answer(
        text=emoji.emojize("Чтобы получить прогноз, отправьте свою геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.send_position_keyboard)


@dp.message(Command(commands=['restart']))
async def command_restart_handler(message: Message) -> None:
    """
    Рестарт бота
    """
    print('Executing: restart_bot')
    await message.answer(text="Чтобы начать заново, отправьте мне команду /start.")


@dp.message(F.text.startswith('Помощь'))
async def show_help(message: Message) -> None:
    """
    Вывести справку по кнопке помощь
    """
    await message.answer(text=HELP_MESSAGE)


@dp.message(Command(commands=['help']))
async def show_help(message: Message) -> None:
    """
    Вывести справку по команде /help
    """
    await message.answer(text=HELP_MESSAGE)


@dp.message(F.location)
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

    conn, cur = last_geo.connect_to_db(conf['db']['database_name'],
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
        last_geo.close_connection_db(conn, cur)
    else:
        logging.info('Can not connect to database!')

    response = requests.get("https://api.openweathermap.org/data/2.5/"
                            f"forecast?lang=ru&lat={lat}&lon={lon}&"
                            f"appid={conf['open_weather_token']}",
                            timeout=10)
    weather_dict = json.loads(response.text)
    await message.answer(recommend_car_wash(weather_dict, lat, lon),
                         parse_mode='HTML',
                         reply_markup=keyboards.second_keyboard)


@dp.message()
async def use_old_location(message: types.Message) -> None:
    """
    Используя последнюю геопозицию присылает прогноз (берется из БД)
    """
    if 'Использовать последнюю геопозицию' in message.text:
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
            logging.info('Can not connect to database!')

        print(f"latitude:  {old_lat}\nlongitude: {old_lon}")
        if old_lat and old_lon:
            response = requests.get("https://api.openweathermap.org/data/2.5/"
                                    f"forecast?lang=ru&lat={old_lat}&lon={old_lon}&"
                                    f"appid={conf['open_weather_token']}",
                                    timeout=10)
            weather_dict = json.loads(response.text)
            await message.answer(recommend_car_wash(weather_dict, old_lat, old_lon) + \
                                 f"\n\nТекущая локация: {weather_dict['city']['name']}",
                                 parse_mode='HTML',
                                 reply_markup=keyboards.second_keyboard)
        else:
            await message.answer("Нет данных о последней использованной геопозиции, "
                                 "для использования этой функции отправьте геопозицию!",
                                parse_mode='HTML',
                                reply_markup=keyboards.second_keyboard)


@dp.message(F.text.startswith('Купить премиум'))
async def handle_premium_purchase(message: Message):
    """
    Обработчик покупки премиум-подписки
    """
    logger.info(f"User {message.from_user.id} initiated premium purchase")
    try:
        # Проверяем текущий статус подписки
        if is_user_premium(message.from_user.id):
            await message.answer("🎉 У вас уже активна премиум-подписка!")
            return

        # Вызываем платежный обработчик
        await send_invoice_handler(message)
        
    except Exception as e:
        logger.error(f"Error in premium purchase: {e}")
        await message.answer("⚠️ Произошла ошибка при обработке запроса")


async def send_invoice_handler(message: Message):
    prices = [LabeledPrice(label="Премиум подписка", amount=20)]    # 20 Stars
    await message.answer_invoice(
        title="Премиум подписка",
        description="Доступ к премиум-функциям за 20 Stars",
        provider_token="YOUR_PROVIDER_TOKEN",       # Получить через BotFather
        currency="XTR",     # Валюта Stars
        prices=prices,
        payload="premium_subscription",
        reply_markup=keyboards.payment_keyboard(),
    )


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    # Здесь можно добавить дополнительную проверку
    await pre_checkout_query.answer(ok=True)


async def success_payment_handler(message: Message):
    # Активируем премиум доступ
    user_id = message.from_user.id
    activate_premium(user_id)
    
    await message.answer(
        text="🎉 Премиум подписка активирована! Спасибо за покупку!\n"
             "Теперь вам доступны все эксклюзивные функции!"
    )


def activate_premium(user_id: int):
    # Логика активации премиума в БД
    pass
    # conn.execute('''
    #     INSERT OR REPLACE INTO users (user_id, is_premium, premium_until) 
    #     VALUES (?, 1, datetime('now', '+1 month'))
    # ''', (user_id,))
    # conn.commit()


def is_user_premium(user_id: int) -> bool:
    """
    Проверка премиум-статуса пользователя
    """
    # реализация проверки статуса из БД
    # Пример:
    # cursor.execute('SELECT premium_until FROM users WHERE user_id = ?', (user_id,))
    # result = cursor.fetchone()
    # return result[0] > datetime.now() if result else False
    return False  # Заглушка для примера
