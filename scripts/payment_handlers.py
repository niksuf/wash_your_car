import logging
from aiogram import F, Dispatcher
from aiogram.types import Message, PreCheckoutQuery, LabeledPrice
from aiogram.utils.markdown import hbold
import emoji
import keyboards
from functions import read_yaml

logger = logging.getLogger(__name__)
conf = read_yaml('config.yml')


async def send_invoice_handler(message: Message):
    try:
        prices = [LabeledPrice(label="Премиум подписка", amount=20)]  # 20 Stars
        await message.answer_invoice(
            title="🌟 Премиум доступ",
            description="Премиум подписка на 1 месяц",
            provider_token=conf['payment']['stars_provider_token'],
            currency="XTR",
            prices=prices,
            payload="premium_subscription",
            reply_markup=keyboards.payment_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке инвойса: {e}")
        await message.answer("⚠️ Произошла ошибка при создании платежа")


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logger.error(f"Ошибка pre_checkout: {e}")


async def success_payment_handler(message: Message):
    try:
        user_id = message.from_user.id
        await message.answer(
            "🎉 Премиум подписка активирована!\n"
            "Срок действия: 1 месяц\n"
            "Спасибо за покупку!"
        )
        # Здесь добавьте логику активации премиума
    except Exception as e:
        logger.error(f"Ошибка обработки платежа: {e}")
        await message.answer("⚠️ Произошла ошибка при активации подписки")


def register_payment_handlers(dp: Dispatcher):
    dp.message.register(send_invoice_handler, F.text == 'Купить премиум 💎')
    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(success_payment_handler, F.successful_payment)
