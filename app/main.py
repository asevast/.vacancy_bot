import asyncio

from app.config import BOT_TOKEN, DB_CONFIG, logger
from app.context import bot, dp
from app.db import init_db
from app.handlers import subscription_worker
from app.lists import start_web_server


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN is not configured. Set BOT_TOKEN in .env before запуск.")
        raise RuntimeError("BOT_TOKEN is required to start the bot.")

    bot_instance = bot
    logger.info("Starting Vacancy Analyzer PRO...")
    logger.info(f"Bot token: {BOT_TOKEN[:15]}...")
    logger.info(f"DB: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    
    try:
        init_db()
        logger.info("Database connected and initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
    
    try:
        await start_web_server()
    except Exception as e:
        logger.error(f"Web server init failed: {e}")

    logger.info("Bot is polling for updates...")
    asyncio.create_task(subscription_worker(bot_instance))
    await dp.start_polling(bot_instance)
