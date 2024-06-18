import logging
import asyncio
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from functions import read_yaml
from handler import dp

conf = read_yaml('config.yml')
bot = Bot(conf['telegram_token'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def main() -> None:
    print('Bot started!')
    await dp.start_polling(bot)


if __name__ == '__main__':
    # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
