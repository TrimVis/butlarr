from loguru import logger
from telegram import Update
from telegram.ext import Application

from .database import Database
from .config.secrets import TELEGRAM_TOKEN
from .config.services import SERVICES 
from .tg_handler.auth import get_auth_handler


def init():
    pass


def main():
    logger.info('Initializing database...')
    db = Database()

    logger.info('Creating bot...')
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    logger.info('Registering auth command...')
    application.add_handler(get_auth_handler(db))

    logger.info('Registering help commands...')
    # TODO pjordan: Add this

    logger.info('Registering services..')
    for s in SERVICES:
        s.register(application, db)

    logger.info('Start polling for messages..')
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
