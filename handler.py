from aiogram import Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
import emoji
import keyboards

dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    print('Executing: command_start_handler')
    await message.answer(
        text=emoji.emojize(f"Привет, {hbold(message.from_user.full_name)}!\n\n{hbold('Мыть машину?')} - "
                           f"телеграм бот, который по запросу анализирует погоду (используется "
                           f"Яндекс.Погода) и дает совет, целесообразно ли сегодня помыть машину.\n\n"
                           f"Чтобы начать, отправьте свою геопозицию :round_pushpin:"),
        parse_mode='HTML',
        reply_markup=keyboards.start_keyboard)


@dp.message(F.location)
async def handle_location(message: types.Message) -> None:
    print('Executing: handle_location')
    lat = message.location.latitude
    lon = message.location.longitude
    reply = f"latitude:  {lat}\nlongitude: {lon}"
    await message.answer(reply)
