# import asyncio
from aiogram import executor

from config import admin_id
from load_all import bot
from sql import create_db


async def on_startup(dp):  # При запуске бота
    await create_db()  # Создаст таблицы (если их нет)
    await bot.send_message(admin_id, "Я запущен!")  # Отправит сообщение админу при готовности


async def on_shutdown(dp):
    await bot.close()


if __name__ == '__main__':
    from handlers import dp

    executor.start_polling(dp, on_shutdown=on_shutdown, on_startup=on_startup)  # запуск поллинга
