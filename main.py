import asyncio
import aiogram
import os
import logging
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from routers import shop


load_dotenv()

TOKEN = os.getenv("TG_TOKEN")

async def main():
    dp = Dispatcher()
    dp.include_router(shop.router)
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())