"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Модуль для работы с платежами ЮKassa (синхронная версия)
"""

import uuid
from typing import Dict, Any
import logging

try:
    from yookassa import Payment, Configuration
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False
    logging.warning("Библиотека yookassa не установлена. Установите: pip install yookassa")

class YooKassaPayment:
    """Класс для работы с платежами ЮKassa"""
    
    def __init__(self, shop_id: str, secret_key: str):
        """
        Инициализация ЮKassa
        
        Args:
            shop_id: Идентификатор магазина
            secret_key: Секретный ключ
        """
        if not YOOKASSA_AVAILABLE:
            raise ImportError("Библиотека yookassa не установлена")
        
        if shop_id and secret_key:
            Configuration.account_id = shop_id
            Configuration.secret_key = secret_key
            self.enabled = True
        else:
            self.enabled = False
            logging.warning("YooKassa не настроен. Проверьте shop_id и secret_key в config.yml")
    
    def create_payment(
        self, 
        amount: float, 
        user_id: int,
        description: str = "Донат на развитие бота"
    ) -> Dict[str, Any]:
        """
        Создание платежа в ЮKassa (синхронный метод)
        
        Args:
            amount: Сумма платежа
            user_id: ID пользователя Telegram
            description: Описание платежа
            
        Returns:
            Словарь с данными платежа
        """
        if not self.enabled:
            raise Exception("YooKassa не настроен")
        
        try:
            # Генерируем уникальный ключ идемпотентности
            idempotence_key = str(uuid.uuid4())
            
            # Создаем платеж
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "payment_method_data": {
                    "type": "bank_card"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/worth_wash_car_bot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": user_id,
                    "telegram_username": f"user_{user_id}"
                }
            }, idempotence_key)
            
            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status
            }
            
        except Exception as e:
            logging.error(f"Error creating YooKassa payment: {e}")
            raise Exception(f"Ошибка создания платежа: {str(e)}")
    
    def check_payment_status(self, payment_id: str) -> str:
        """
        Проверка статуса платежа (синхронный метод)
        
        Args:
            payment_id: ID платежа
            
        Returns:
            Статус платежа
        """
        if not self.enabled:
            return "disabled"
        
        try:
            # Получаем информацию о платеже
            payment = Payment.find_one(payment_id)
            return payment.status
            
        except Exception as e:
            logging.error(f"Error checking payment status {payment_id}: {e}")
            return "error"
