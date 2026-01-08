"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Обработчики для системы донатов
"""

import asyncio
import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from scripts.functions import read_yaml
from scripts.database_module import (
    save_donation, 
    update_donation_status,
    get_user_donations,
    get_total_donations,
    check_donation_table_exists
)
from scripts.keyboards import (
    get_donate_methods_keyboard,
    get_stars_amounts_keyboard,
    get_yookassa_amounts_keyboard,
    get_payment_check_keyboard
)

# Для работы с ЮKassa
from scripts.yookassa_payment import YooKassaPayment

donate_router = Router()

# Загружаем конфиг
conf = read_yaml('config.yml')

# Получаем параметры БД из конфига
DB_PARAMS = {
    'dbname': conf['db']['database_name'],
    'user': conf['db']['user_name'],
    'password': conf['db']['user_password'],
    'host': conf['db']['host']
}

# Инициализируем ЮKassa если есть настройки
YOOKASSA_ENABLED = False
if conf.get('yookassa', {}).get('shop_id') and conf.get('yookassa', {}).get('secret_key'):
    yookassa = YooKassaPayment(
        shop_id=conf['yookassa']['shop_id'],
        secret_key=conf['yookassa']['secret_key']
    )
    YOOKASSA_ENABLED = True
else:
    logging.warning("YooKassa не настроен. Проверьте config.yml")

# Состояния для FSM
class DonateStates(StatesGroup):
    waiting_custom_amount = State()

# Проверяем таблицу донатов при старте
@donate_router.startup()
async def on_startup():
    """Проверка при старте бота"""
    if not check_donation_table_exists(DB_PARAMS):
        logging.error("Таблица donations не существует! Создайте её через SQL скрипт.")
        logging.error("Файл: scripts/sql/create_donations_table.sql")

# Команда /donate
@donate_router.message(Command("donate"))
async def cmd_donate(message: types.Message):
    """Обработка команды /donate"""
    await show_donate_menu(message)

@donate_router.message(F.text.contains("Поддержать"))
async def donate_button_handler(message: types.Message):
    """Обработка кнопки 'Поддержать проект'"""
    await show_donate_menu(message)

async def show_donate_menu(message: types.Message):
    """Показать меню донатов"""
    text = (
        "🎁 <b>Поддержать проект</b>\n\n"
        "Выберите способ доната:\n\n"
        "🌟 <b>Telegram Stars</b> - встроенная система донатов в Telegram\n"
    )
    
    if YOOKASSA_ENABLED:
        text += "💳 <b>ЮKassa</b> - перевод рублями на карту/кошелек"
    
    await message.answer(
        text,
        reply_markup=get_donate_methods_keyboard(YOOKASSA_ENABLED)
    )

# Обработка выбора способа доната
@donate_router.callback_query(F.data.in_(["donate_stars", "donate_yookassa"]))
async def process_donate_method(callback: types.CallbackQuery):
    """Обработка выбора способа доната"""
    if callback.data == "donate_stars":
        await callback.message.edit_text(
            "Выберите сумму доната в Telegram Stars:\n\n"
            "<i>1 звезда ≈ $0.012</i>",
            reply_markup=get_stars_amounts_keyboard()
        )
    else:  # donate_yookassa
        if not YOOKASSA_ENABLED:
            await callback.answer("ЮKassa временно недоступна", show_alert=True)
            return
            
        await callback.message.edit_text(
            "Выберите сумму доната в рублях:",
            reply_markup=get_yookassa_amounts_keyboard()
        )
    await callback.answer()

# Обработка возврата назад
@donate_router.callback_query(F.data == "donate_back")
async def process_donate_back(callback: types.CallbackQuery):
    """Обработка кнопки 'Назад'"""
    await show_donate_menu(callback.message)
    await callback.answer()

# Обработка выбора суммы в звездах
@donate_router.callback_query(F.data.startswith("stars_"))
async def process_stars_amount(callback: types.CallbackQuery, bot: Bot):
    """Обработка выбора суммы в звездах"""
    try:
        stars_amount = callback.data.split("_")[1]
        
        # Конвертация: 1 звезда = $0.012 = 1.2 цента
        prices_map = {
            "10": [types.LabeledPrice(label="10 Stars", amount=1000)],    # 10 звезд
            "50": [types.LabeledPrice(label="50 Stars", amount=5000)],    # 50 звезд
            "100": [types.LabeledPrice(label="100 Stars", amount=10000)]  # 100 звезд
        }
        
        prices = prices_map.get(stars_amount)
        if not prices:
            await callback.answer("Неверная сумма")
            return
        
        # Создаем инвойс
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Донат {stars_amount} звезд",
            description="Поддержка проекта Wash Your Car 🚗",
            payload=f"stars_{stars_amount}_{callback.from_user.id}",
            provider_token="",  # Для Stars оставляем пустым
            currency="XTR",  # Код валюты Stars
            prices=prices,
            start_parameter="donate",
            need_email=False,
            need_phone_number=False,
            need_shipping_address=False
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error creating stars invoice: {e}")
        await callback.answer("Ошибка при создании платежа", show_alert=True)

# Предварительная проверка платежа Stars
@donate_router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery, bot: Bot):
    """Предварительная проверка платежа"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Успешный платеж Stars
@donate_router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    """Обработка успешного платежа"""
    payment = message.successful_payment
    
    try:
        # Извлекаем данные из payload
        payload_parts = payment.invoice_payload.split("_")
        if len(payload_parts) >= 3:
            donate_type = payload_parts[0]
            amount = payload_parts[1]
            user_id = payload_parts[2]
            
            # Подготавливаем данные для сохранения
            donation_data = {
                'user_id': message.from_user.id,
                'username': message.from_user.username,
                'amount': float(amount),
                'currency': 'XTR',
                'payment_system': 'telegram_stars',
                'payment_id': payment.telegram_payment_charge_id,
                'status': 'completed',
                'metadata': {
                    'total_amount': payment.total_amount,
                    'telegram_payment_charge_id': payment.telegram_payment_charge_id
                }
            }
            
            # Сохраняем в БД через отдельный поток
            saved = await asyncio.to_thread(save_donation, DB_PARAMS, donation_data)
            
            if saved:
                await message.answer(
                    f"🎉 <b>Спасибо за донат {amount} звезд!</b>\n\n"
                    f"Ваша поддержка помогает развивать проект!\n"
                    f"Спасибо, что делаете бота лучше! 🚗💦"
                )
                
                # Уведомление админа
                admin_ids = conf.get('admin_ids', [])
                for admin_id in admin_ids:
                    try:
                        await message.bot.send_message(
                            admin_id,
                            f"🆕 Новый донат Stars!\n"
                            f"👤 От: @{message.from_user.username}\n"
                            f"⭐ Сумма: {amount} звезд\n"
                            f"💰 Стоимость: {payment.total_amount / 100:.2f} USD"
                        )
                    except:
                        pass
            else:
                await message.answer("Платеж получен, но возникла ошибка при сохранении в БД.")
                
    except Exception as e:
        logging.error(f"Error processing successful payment: {e}")
        await message.answer("Произошла ошибка при обработке платежа.")

# Обработка выбора суммы ЮKassa
@donate_router.callback_query(F.data.startswith("yookassa_"))
async def process_yookassa_amount(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Обработка выбора суммы для ЮKassa"""
    if not YOOKASSA_ENABLED:
        await callback.answer("ЮKassa временно недоступна", show_alert=True)
        return
    
    data = callback.data
    
    if data == "yookassa_custom":
        # Запрашиваем кастомную сумму
        await callback.message.edit_text(
            "Введите сумму доната в рублях (от 10 до 15000):"
        )
        await state.set_state(DonateStates.waiting_custom_amount)
        await callback.answer()
        return
    
    # Получаем сумму из callback_data
    amount_str = data.split("_")[1]
    
    try:
        amount = int(amount_str)
        if amount < 10 or amount > 15000:
            await callback.answer("Сумма должна быть от 10 до 15000 рублей", show_alert=True)
            return
            
        await create_yookassa_payment(callback, amount, bot)
        
    except ValueError:
        await callback.answer("Неверная сумма", show_alert=True)

# Обработка кастомной суммы
@donate_router.message(DonateStates.waiting_custom_amount)
async def process_custom_amount(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка ввода кастомной суммы"""
    try:
        amount = int(message.text)
        if amount < 10 or amount > 15000:
            await message.answer("Сумма должна быть от 10 до 15000 рублей. Попробуйте еще раз:")
            return
        
        await state.clear()
        
        # Создаем callback объект для единообразия
        class FakeCallback:
            def __init__(self):
                self.from_user = message.from_user
                self.message = message
                self.data = f"yookassa_{amount}"
        
        await create_yookassa_payment(FakeCallback(), amount, bot)
        
    except ValueError:
        await message.answer("Пожалуйста, введите число (например: 300):")

async def create_yookassa_payment(callback, amount: int, bot: Bot):
    """Создание платежа в ЮKassa"""
    try:
        # Создаем платеж
        payment_data = await asyncio.to_thread(
            yookassa.create_payment,
            amount=amount,
            user_id=callback.from_user.id,
            description=f"Донат от @{callback.from_user.username} в боте Wash Your Car"
        )
        
        # Подготавливаем данные для сохранения
        donation_data = {
            'user_id': callback.from_user.id,
            'username': callback.from_user.username,
            'amount': float(amount),
            'currency': 'RUB',
            'payment_system': 'yookassa',
            'payment_id': payment_data["payment_id"],
            'status': 'pending',
            'metadata': {
                'confirmation_url': payment_data["confirmation_url"],
                'initial_status': payment_data["status"]
            }
        }
        
        # Сохраняем в БД
        saved = await asyncio.to_thread(save_donation, DB_PARAMS, donation_data)
        
        if saved:
            # Обновляем клавиатуру с правильной ссылкой
            keyboard = get_payment_check_keyboard(payment_data["payment_id"])
            keyboard.inline_keyboard[0][0].url = payment_data["confirmation_url"]
            
            await callback.message.edit_text(
                f"💳 <b>Оплата {amount} ₽</b>\n\n"
                f"Для оплаты перейдите по ссылке ниже:\n\n"
                f"<b>ID платежа:</b> <code>{payment_data['payment_id']}</code>\n\n"
                "После оплаты нажмите кнопку '✅ Я оплатил'",
                reply_markup=keyboard
            )
        else:
            await callback.message.answer("Ошибка при сохранении платежа в БД")
        
    except Exception as e:
        logging.error(f"Error creating YooKassa payment: {e}")
        await callback.message.answer(
            f"❌ Ошибка при создании платежа: {str(e)}\n\n"
            "Пожалуйста, попробуйте позже или выберите другой способ оплаты."
        )

# Проверка статуса платежа ЮKassa
@donate_router.callback_query(F.data.startswith("check_"))
async def check_payment_status(callback: types.CallbackQuery):
    """Проверка статуса платежа ЮKassa"""
    if not YOOKASSA_ENABLED:
        await callback.answer("ЮKassa недоступна", show_alert=True)
        return
    
    payment_id = callback.data.replace("check_", "")
    
    try:
        # Проверяем статус платежа
        status = await asyncio.to_thread(yookassa.check_payment_status, payment_id)
        
        if status == "succeeded":
            # Обновляем статус в БД
            updated = await asyncio.to_thread(
                update_donation_status, DB_PARAMS, payment_id, "completed"
            )
            
            if updated:
                await callback.message.edit_text(
                    "✅ <b>Платеж успешно завершен!</b>\n\n"
                    "Спасибо за вашу поддержку! 🎉\n"
                    "Ваш донат поможет сделать бота лучше! 🚗💦"
                )
                
                # Получаем информацию о донате для уведомления
                donations = await asyncio.to_thread(
                    get_user_donations, DB_PARAMS, callback.from_user.id, 1
                )
                
                if donations:
                    # Уведомление админа
                    admin_ids = conf.get('admin_ids', [])
                    for admin_id in admin_ids:
                        try:
                            await callback.bot.send_message(
                                admin_id,
                                f"🆕 Новый донат ЮKassa!\n"
                                f"👤 От: @{callback.from_user.username}\n"
                                f"💰 Сумма: {donations[0]['amount']} {donations[0]['currency']}\n"
                                f"✅ Статус: оплачен"
                            )
                        except:
                            pass
            else:
                await callback.answer("Ошибка при обновлении статуса", show_alert=True)
                
        elif status == "pending":
            await callback.answer(
                "⏳ Платеж еще не прошел. Пожалуйста, подождите несколько минут и проверьте снова.",
                show_alert=True
            )
        elif status == "canceled":
            # Обновляем статус в БД
            await asyncio.to_thread(
                update_donation_status, DB_PARAMS, payment_id, "canceled"
            )
            
            await callback.message.edit_text(
                "❌ Платеж был отменен.\n\n"
                "Если это ошибка, попробуйте создать новый платеж."
            )
        else:
            await callback.answer(
                f"Статус платежа: {status}",
                show_alert=True
            )
            
    except Exception as e:
        logging.error(f"Error checking payment status: {e}")
        await callback.answer(
            f"Ошибка при проверке платежа: {str(e)}",
            show_alert=True
        )

# Команда для просмотра статистики донатов (админская)
@donate_router.message(Command("donations_stats"))
async def cmd_donations_stats(message: types.Message):
    """Показать статистику донатов (админская команда)"""
    admin_ids = conf.get('admin_ids', [])
    
    if message.from_user.id not in admin_ids:
        await message.answer("У вас нет прав для просмотра этой информации.")
        return
    
    try:
        # Получаем статистику
        stats = await asyncio.to_thread(get_total_donations, DB_PARAMS)
        
        text = "📊 <b>Статистика донатов</b>\n\n"
        text += f"💰 Всего собрано: {stats['total_rub']:.2f} RUB\n"
        text += f"⭐ Всего звезд: {stats['total_stars']}\n"
        text += f"✅ Успешных донатов: {stats['completed_count']}\n"
        text += f"📈 Всего попыток: {stats['total_count']}\n\n"
        
        if stats['recent']:
            text += "🕒 <b>Последние донаты:</b>\n"
            for donation in stats['recent']:
                username = donation['username'] or 'Аноним'
                amount = donation['amount']
                currency = donation['currency']
                created = donation['created_at'].strftime("%d.%m.%Y %H:%M")
                
                if currency == 'RUB':
                    text += f"• {username}: {amount:.0f} RUB ({created})\n"
                else:
                    text += f"• {username}: {amount} Stars ({created})\n"
        
        await message.answer(text)
        
    except Exception as e:
        logging.error(f"Error getting donation stats: {e}")
        await message.answer("Ошибка при получении статистики.")
