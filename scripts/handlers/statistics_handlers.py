"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность хэндлеров обработки статистики
"""

import logging
import emoji
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

import logger
import database_module
from functions import read_yaml

logger.setup_logging()
conf = read_yaml('config.yml')
statistics_router = Router()


@statistics_router.message(F.text == emoji.emojize(':bar_chart: Статистика'))
async def stats_button_handler(message: Message):
    """Показывает статистику по кнопке"""
    logging.info(f"Кнопка статистики нажата пользователем {message.from_user.id}")
    await show_stats(message)


@statistics_router.message(Command(commands=['stats']))
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
