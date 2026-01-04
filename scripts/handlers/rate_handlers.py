"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность хэндлеров оценки пронозов
"""

import json
import logging
from aiogram import Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import emoji

# Локальные импорты
import database_module
import logger
from functions import read_yaml

logger.setup_logging()
conf = read_yaml('config.yml')
rate_router = Router()


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
    """ Сохраняет прогноз в базу данных и возвращает его ID """
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
    """ Сохраняет оценку пользователя """
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
    """ Получает ID последней записи в car_washes для пользователя """
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


@rate_router.callback_query(F.data.startswith("feedback:"))
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


@rate_router.callback_query(F.data == "no_action")
async def handle_no_action(callback: CallbackQuery):
    """Обрабатывает нажатие на неактивную кнопку"""
    await callback.answer()
