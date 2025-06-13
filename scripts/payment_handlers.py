"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Функциональность хэндлеров оплаты
"""

from aiogram import Dispatcher, F
from aiogram.types import (
    Message, 
    PreCheckoutQuery,
    LabeledPrice,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import emoji
from functions import read_yaml

config = read_yaml('config.yml')
YOOKASSA_TOKEN = config['payment']['yookassa_token']
STAR_TOKEN = config['payment']['star_token']

PREMIUM_PRICE_STARS = 20  # 20 Stars
PREMIUM_PRICE_RUB = 29900  # 299 рублей в копейках
PREMIUM_DURATION_DAYS = 30


def register_payment_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    dp.message.register(choose_payment_method, F.text == emoji.emojize('Купить премиум :gem:'))
    dp.callback_query.register(process_payment_method)
    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(successful_payment_handler, F.successful_payment)


async def activate_premium(user_id: int):
    """Активация премиум-статуса (реализуйте подключение к вашей БД)"""
    # Пример для SQLite:
    # conn.execute('UPDATE users SET is_premium = 1 WHERE user_id = ?', (user_id,))
    # conn.commit()
    pass


async def choose_payment_method(message: Message):
    """Клавиатура выбора способа оплаты"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=emoji.emojize(f":star: Оплатить {PREMIUM_PRICE_STARS} Stars"),
            callback_data="pay_with_stars"
        ),
        InlineKeyboardButton(
            text=emoji.emojize(":credit_card: Оплатить картой"),
            callback_data="pay_with_card"
        )
    )
    await message.answer(
        "Выберите способ оплаты:",
        reply_markup=builder.as_markup()
    )


async def process_payment_method(callback: CallbackQuery):
    """Обработка выбора способа оплаты"""
    if callback.data == "pay_with_stars":
        await send_stars_invoice(callback.message)
    elif callback.data == "pay_with_card":
        await send_yookassa_invoice(callback.message)
    await callback.answer()


async def send_stars_invoice(message: Message):
    """Отправка инвойса для оплаты Stars"""
    await message.answer_invoice(
        title="Премиум подписка",
        description=f"Доступ к премиум-функциям на {PREMIUM_DURATION_DAYS} дней",
        provider_token=STAR_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label="Премиум", amount=PREMIUM_PRICE_STARS)],
        payload="stars_payment"
    )


async def send_yookassa_invoice(message: Message):
    """Отправка инвойса для ЮKassa"""
    await message.answer_invoice(
        title="Премиум подписка",
        description=f"Доступ к премиум-функциям на {PREMIUM_DURATION_DAYS} дней",
        provider_token=YOOKASSA_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Премиум", amount=PREMIUM_PRICE_RUB)],
        payload="yookassa_payment",
        need_email=True
    )


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительной проверки"""
    await pre_checkout_query.answer(ok=True)


async def successful_payment_handler(message: Message):
    """Обработка успешного платежа"""
    user_id = message.from_user.id
    await activate_premium(user_id)

    if message.successful_payment.invoice_payload == "stars_payment":
        await message.answer(text=emoji.emojize(":white_check_mark: "
                                                "Оплата Stars прошла успешно! Премиум активирован."))
    else:
        await message.answer(text=emoji.emojize(":white_check_mark: "
                                                "Оплата картой прошла успешно! Премиум активирован."))
