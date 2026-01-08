"""
Wash your car - телеграм бот, который по запросу анализирует погоду (используется
OpenWeather) и дает совет, целесообразно ли сегодня помыть машину.

Бот можно найти по адресу:
https://t.me/worth_wash_car_bot

Сервис для обработки вебхуков от ЮKassa
"""

from aiohttp import web
import logging
from scripts.database_module import update_donation_status
from scripts.functions import read_yaml

conf = read_yaml('config.yml')

async def handle_yookassa_webhook(request):
    """
    Обработка вебхуков от ЮKassa
    """
    try:
        data = await request.json()
        event = data.get('event')
        
        if event == 'payment.succeeded':
            payment_object = data.get('object', {})
            payment_id = payment_object.get('id')
            
            # Обновляем статус в базе данных
            await update_donation_status(payment_id, 'completed')
            
            logging.info(f"Payment succeeded: {payment_id}")
            
        elif event == 'payment.canceled':
            payment_object = data.get('object', {})
            payment_id = payment_object.get('id')
            
            await update_donation_status(payment_id, 'canceled')
            logging.info(f"Payment canceled: {payment_id}")
        
        return web.Response(text='OK', status=200)
        
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return web.Response(text='Error', status=500)

def setup_webhook_routes(app):
    """Настройка маршрутов вебхука"""
    app.router.add_post('/yookassa-webhook', handle_yookassa_webhook)

if __name__ == '__main__':
    app = web.Application()
    setup_webhook_routes(app)
    web.run_app(app, port=3000)
