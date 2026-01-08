"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Вспомогательный файл для хранения переменных клавиатур
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import emoji

# Кнопка помощь
help_button = KeyboardButton(text='Помощь')

# Кнопка статистики
stats_button = KeyboardButton(text=emoji.emojize(':bar_chart: Статистика'))

# Кнопка доната
donate_button = KeyboardButton(text=emoji.emojize('💎 Поддержать проект'))

# Приветственная клавиатура
next_button = KeyboardButton(text=emoji.emojize('Далее :right_arrow:'))
start_keyboard = ReplyKeyboardMarkup(keyboard=[[next_button],
                                               [help_button]],
                                     resize_keyboard=True)

# Клавиатура соглашения
accept_agreement = KeyboardButton(
    text=emoji.emojize('Принять соглашение :newspaper:'))
accept_agreement_keyboard = ReplyKeyboardMarkup(keyboard=[[accept_agreement],
                                                          [help_button]],
                                                resize_keyboard=True)

# Клавиатура для отправки геопозиции
send_position = KeyboardButton(text=emoji.emojize(
    'Отправить геопозицию :round_pushpin:'), request_location=True)
send_position_keyboard = ReplyKeyboardMarkup(keyboard=[[send_position],
                                                       [help_button]],
                                             resize_keyboard=True)

# Клавиатура для отправки геопозиции или использования старой
use_old_position = KeyboardButton(text=emoji.emojize('Использовать последнюю геопозицию'))
second_keyboard = ReplyKeyboardMarkup(
    keyboard=[[send_position],
              [use_old_position],
              [stats_button, help_button, donate_button]],
    resize_keyboard=True)


# Inline клавиатуры для донатов
def get_donate_methods_keyboard():
    """ Клавиатура выбора способа доната """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Telegram Stars", callback_data="donate_stars")],
        [InlineKeyboardButton(text="💳 ЮKassa (рубли)", callback_data="donate_yookassa")]
    ])


def get_stars_amounts_keyboard():
    """ Клавиатура выбора суммы в звездах """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 ⭐", callback_data="stars_10")],
        [InlineKeyboardButton(text="50 ⭐", callback_data="stars_50")],
        [InlineKeyboardButton(text="100 ⭐", callback_data="stars_100")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="donate_back")]
    ])


def get_yookassa_amounts_keyboard():
    """ Клавиатура выбора суммы в рублях """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="100 ₽", callback_data="yookassa_100")],
        [InlineKeyboardButton(text="500 ₽", callback_data="yookassa_500")],
        [InlineKeyboardButton(text="1000 ₽", callback_data="yookassa_1000")],
        [InlineKeyboardButton(text="Другая сумма", callback_data="yookassa_custom")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="donate_back")]
    ])


def get_payment_check_keyboard(payment_id: str):
    """ Клавиатура для проверки платежа ЮKassa """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url="")],  # URL будет установлен динамически
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_{payment_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="donate_back")]
    ])


def get_forecast_keyboard(forecast_id: int = None) -> InlineKeyboardMarkup:
    """Создает комбинированную inline-клавиатуру с оценкой и меню"""
    keyboard = []
    
    # Добавляем кнопки оценки только если есть forecast_id
    if forecast_id:
        keyboard.append([
            InlineKeyboardButton(
                text=emoji.emojize(":thumbs_up: Правильно"),
                callback_data=f"feedback:{forecast_id}:like"
            ),
            InlineKeyboardButton(
                text=emoji.emojize(":thumbs_down: Ошибся"),
                callback_data=f"feedback:{forecast_id}:dislike"
            )
        ])
    
    # Добавляем меню действий
    keyboard.extend([
        [
            InlineKeyboardButton(
                text=emoji.emojize(":bar_chart: Статистика"), 
                callback_data="menu_stats"
            ),
            InlineKeyboardButton(
                text="📈 Новый прогноз", 
                callback_data="menu_new_forecast"
            )
        ],
        [
            InlineKeyboardButton(
                text=emoji.emojize(":round_pushpin: Отправить геопозицию"), 
                callback_data="menu_send_location"
            ),
            InlineKeyboardButton(
                text=emoji.emojize("📍 Использовать последнюю"), 
                callback_data="menu_use_last_location"
            )
        ],
        [
            InlineKeyboardButton(
                text=emoji.emojize("⚙️ Настройки"), 
                callback_data="menu_settings"
            ),
            InlineKeyboardButton(
                text=emoji.emojize("ℹ️ Помощь"), 
                callback_data="menu_help"
            )
        ]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_feedback_confirmed_keyboard(is_positive: bool) -> InlineKeyboardMarkup:
    """Создает клавиатуру с подтверждением оценки"""
    keyboard = [[
        InlineKeyboardButton(
            text=emoji.emojize(":check_mark_button: Оценка принята") if is_positive 
            else emoji.emojize(":cross_mark: Оценка принята"),
            callback_data="no_action"
        )
    ]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
