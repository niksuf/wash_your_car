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
from aiogram import Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold
from aiogram import F
import logger

import keyboards
from functions import read_yaml
from wash_functions import recommend_car_wash
import last_geo
import database_module

HELP_MESSAGE = emoji.emojize(f"\n{hbold('Мыть машину?')} - телеграм бот, который по запросу "
                             "анализирует погоду (используется OpenWeather) и дает совет, "
                             "целесообразно ли сегодня помыть машину.\n\n"
                             "/start - старт бота;\n"
                             "/restart - рестарт бота;\n"
                             "/help - открыть помощь;\n"
                             "/stats - статистика оценок.")

logger.setup_logging()
conf = read_yaml('config.yml')
dp = Dispatcher()
lat = -999
lon = -999


# ==================== ФУНКЦИИ ДЛЯ ОЦЕНКИ ====================

def get_feedback_keyboard(forecast_id: int) -> InlineKeyboardMarkup:
    """Создает inline-клавиатуру для оценки прогноза"""
    keyboard = [
        [
            InlineKeyboardButton(
                text=emoji.emojize(":thumbs_up: Правильно"),
                callback_data=f"feedback:{forecast_id}:like"
            ),
            InlineKeyboardButton(
                text=emoji.emojize(":thumbs_down: Ошибся"),
                callback_data=f"feedback:{forecast_id}:dislike"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def extract_recommendation_type(recommendation_text: str) -> str:
    """Определяет тип рекомендации по тексту"""
    if "можно мыть" in recommendation_text.lower():
        return "wash"
    elif "отложить" in recommendation_text.lower():
        return "dont_wash"
    else:
        return "unknown"


async def save_forecast_to_db(user_id: int, car_wash_id: int, weather_data: dict, 
                            recommendation_text: str, message_id: int, location_name: str = "") -> int:
    """Сохраняет прогноз в базу данных и возвращает его ID"""
    conn, cur = database_module.connect_to_db(
        conf['db']['database_name'],
        conf['db']['user_name'],
        conf['db']['user_password'],
        conf['db']['host']
    )
    if not conn or not cur:
        logging.error("Не удалось подключиться к базе данных")
        return None

    try:
        # Определяем тип рекомендации
        rec_type = extract_recommendation_type(recommendation_text)

        # Сохраняем прогноз
        cur.execute("""
            INSERT INTO forecasts 
            (user_id, car_wash_id, weather_data, recommendation, recommendation_type, message_id, location_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (user_id, car_wash_id, json.dumps(weather_data), recommendation_text, rec_type, message_id, location_name))

        forecast_id = cur.fetchone()[0]
        conn.commit()
        logging.info(f"Сохранен прогноз ID: {forecast_id} для пользователя {user_id}")

        return forecast_id

    except Exception as e:
        logging.error(f"Ошибка при сохранении прогноза: {e}")
        conn.rollback()
        return None
    finally:
        database_module.close_connection_db(conn, cur)


async def save_feedback_to_db(forecast_id: int, user_id: int, is_positive: bool) -> bool:
    """Сохраняет оценку пользователя"""
    conn, cur = database_module.connect_to_db(
        conf['db']['database_name'],
        conf['db']['user_name'],
        conf['db']['user_password'],
        conf['db']['host']
    )
    if not conn or not cur:
        return False

    try:
        cur.execute("""
            INSERT INTO feedback (forecast_id, user_id, is_positive)
            VALUES (%s, %s, %s)
            ON CONFLICT (forecast_id, user_id) 
            DO UPDATE SET is_positive = %s
        """, (forecast_id, user_id, is_positive, is_positive))

        conn.commit()
        logging.info(f"Сохранена оценка {is_positive} для прогноза {forecast_id}")
        return True

    except Exception as e:
        logging.error(f"Ошибка при сохранении оценки: {e}")
        conn.rollback()
        return False
    finally:
        database_module.close_connection_db(conn, cur)


async def get_last_car_wash_id(user_id: int) -> int:
    """Получает ID последней записи в car_washes для пользователя"""
    conn, cur = database_module.connect_to_db(
        conf['db']['database_name'],
        conf['db']['user_name'],
        conf['db']['user_password'],
        conf['db']['host']
    )
    if not conn or not cur:
        return None

    try:
        cur.execute("""
            SELECT id FROM car_washes 
            WHERE user_id = %s 
            ORDER BY id DESC 
            LIMIT 1
        """, (user_id,))

        result = cur.fetchone()
        return result[0] if result else None

    except Exception as e:
        logging.error(f"Ошибка при получении car_wash_id: {e}")
        return None
    finally:
        database_module.close_connection_db(conn, cur)


# ==================== ОСНОВНЫЕ ХЭНДЛЕРЫ ====================

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
                           "в том числе об устройстве, на котором он функционирует, источник "
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

    # Добавляем кнопки оценки к сообщению
    if forecast_id:
        await sent_message.edit_reply_markup(
            reply_markup=get_feedback_keyboard(forecast_id)
        )

    # Отправляем клавиатуру для дальнейших действий
    await message.answer(
        "Вы можете отправить новую геопозицию или использовать предыдущую.",
        reply_markup=keyboards.second_keyboard
    )


@dp.message(F.text == 'Использовать последнюю геопозицию')
async def use_old_location(message: types.Message) -> None:
    """
    Используя последнюю геопозицию присылает прогноз (берется из БД)
    """
    if 'Использовать последнюю геопозицию' in message.text:
        print('Executing: use_old_location')

        user_id = message.from_user.id
        conn, cur = database_module.connect_to_db(conf['db']['database_name'],
                                                  conf['db']['user_name'],
                                                  conf['db']['user_password'],
                                                  conf['db']['host'])
        if conn and cur:
            old_lat, old_lon = last_geo.get_last_geo(cur, user_id)
            database_module.close_connection_db(conn, cur)
        else:
            logging.info('Can not connect to database!')

        print(f"latitude:  {old_lat}\nlongitude: {old_lon}")
        if old_lat and old_lon:
            response = requests.get("https://api.openweathermap.org/data/2.5/"
                                    f"forecast?lang=ru&lat={old_lat}&lon={old_lon}&"
                                    f"appid={conf['open_weather_token']}",
                                    timeout=10)
            weather_dict = json.loads(response.text)

            recommendation_text = recommend_car_wash(weather_dict, old_lat, old_lon)
            location_name = weather_dict.get('city', {}).get('name', 'Неизвестно')
            full_text = f"{recommendation_text}\n\n📍 Локация: {location_name}"

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

            # Отправляем клавиатуру для дальнейших действий
            await message.answer(
                "Вы можете отправить новую геопозицию или использовать предыдущую.",
                reply_markup=keyboards.second_keyboard
            )
        else:
            await message.answer("Нет данных о последней использованной геопозиции, "
                                 "для использования этой функции отправьте геопозицию!",
                                parse_mode='HTML',
                                reply_markup=keyboards.second_keyboard)


# ==================== ОБРАБОТЧИКИ ОЦЕНОК ====================

@dp.callback_query(F.data.startswith("feedback:"))
async def handle_feedback(callback: CallbackQuery):
    """Обрабатывает нажатие на лайк/дизлайк"""
    # Парсим callback_data
    _, forecast_id_str, feedback_type = callback.data.split(":")
    forecast_id = int(forecast_id_str)
    user_id = callback.from_user.id

    # Проверяем, что пользователь оценивает свой прогноз
    conn, cur = database_module.connect_to_db(
        conf['db']['database_name'],
        conf['db']['user_name'],
        conf['db']['user_password'],
        conf['db']['host']
    )

    if conn and cur:
        try:
            # Проверяем, принадлежит ли прогноз пользователю
            cur.execute("SELECT user_id FROM forecasts WHERE id = %s", (forecast_id,))
            result = cur.fetchone()

            if not result:
                await callback.answer("Прогноз не найден!", show_alert=True)
                return

            forecast_user_id = result[0]

            if forecast_user_id != user_id:
                await callback.answer("Вы не можете оценить чужой прогноз!", show_alert=True)
                return

        except Exception as e:
            logging.error(f"Ошибка при проверке прогноза: {e}")
            await callback.answer("Ошибка при проверке прогноза", show_alert=True)
            return
        finally:
            database_module.close_connection_db(conn, cur)

    # Определяем тип оценки
    is_positive = (feedback_type == "like")

    # Сохраняем оценку
    success = await save_feedback_to_db(forecast_id, user_id, is_positive)

    if success:
        # Меняем кнопки на подтверждение
        new_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=emoji.emojize(":check_mark_button: Оценка принята") if is_positive else emoji.emojize(":cross_mark: Оценка принята"),
                callback_data="no_action"
            )
        ]])

        await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        await callback.answer(
            "Спасибо за вашу оценку!" if is_positive 
            else "Спасибо за обратную связь!",
            show_alert=False
        )
        logging.info(f"Пользователь {user_id} оценил прогноз {forecast_id} как {':thumbs_up:' if is_positive else ':thumbs_down:'}")
    else:
        await callback.answer("Ошибка при сохранении оценки!", show_alert=True)


@dp.callback_query(F.data == "no_action")
async def handle_no_action(callback: CallbackQuery):
    """Обрабатывает нажатие на неактивную кнопку"""
    await callback.answer()


# ==================== КОМАНДА СТАТИСТИКИ ====================

@dp.message(F.text == emoji.emojize(':bar_chart: Статистика'))
async def stats_button_handler(message: Message):
    """Показывает статистику по кнопке"""
    logging.info(f"Кнопка статистики нажата пользователем {message.from_user.id}")
    await show_stats(message)


@dp.message(Command(commands=['stats']))
async def stats_command_handler(message: Message):
    """Показывает статистику по команде /stats"""
    logging.info(f"Команда /stats от пользователя {message.from_user.id}")
    await show_stats(message)


async def show_stats(message: Message):
    """Показывает статистику оценок пользователя"""
    user_id = message.from_user.id
    logging.info(f"User requested stats: user_id is {user_id}")
    conn, cur = database_module.connect_to_db(
        conf['db']['database_name'],
        conf['db']['user_name'],
        conf['db']['user_password'],
        conf['db']['host']
    )

    if not conn or not cur:
        await message.answer("Не удалось подключиться к базе данных.")
        return

    try:
        # Получаем общую статистику
        cur.execute("""
            SELECT 
                COUNT(*) as total_forecasts,
                COUNT(DISTINCT location_name) as locations_count
            FROM forecasts 
            WHERE user_id = %s
        """, (user_id,))

        stats = cur.fetchone()

        # Получаем статистику оценок
        cur.execute("""
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN is_positive THEN 1 ELSE 0 END) as likes,
                SUM(CASE WHEN NOT is_positive THEN 1 ELSE 0 END) as dislikes
            FROM feedback f
            JOIN forecasts fc ON f.forecast_id = fc.id
            WHERE fc.user_id = %s
        """, (user_id,))

        feedback_stats = cur.fetchone()

        # Формируем сообщение
        if stats and feedback_stats:
            total_forecasts = stats[0] or 0
            locations = stats[1] or 0

            total_feedback = feedback_stats[0] or 0
            likes = feedback_stats[1] or 0
            dislikes = feedback_stats[2] or 0

            if total_feedback > 0:
                accuracy = (likes / total_feedback) * 100
            else:
                accuracy = 0

            stats_message = emoji.emojize(
                f":bar_chart: <b>Ваша статистика</b>\n\n"
                f":chart_increasing: Всего прогнозов: {total_forecasts}\n"
                f":round_pushpin: Уникальных локаций: {locations}\n"
                f":check_mark_button: Лайков: {likes}\n"
                f":cross_mark: Дизлайков: {dislikes}\n"
                f":bar_chart: Точность рекомендаций: {accuracy:.1f}%\n\n"
                f"<i>Ваши оценки помогают улучшить алгоритм бота!</i>"
            )
        else:
            stats_message = "У вас пока нет статистики. Сделайте несколько прогнозов!"

        await message.answer(stats_message, parse_mode='HTML')

    except Exception as e:
        logging.error(f"Ошибка при получении статистики: {e}")
        await message.answer("Произошла ошибка при получении статистики.")
    finally:
        database_module.close_connection_db(conn, cur)


@dp.message()
async def debug_handler(message: Message):
    """Отладочный обработчик для всех сообщений"""
    logging.debug(f"Получено сообщение: '{message.text}' от {message.from_user.id}")
