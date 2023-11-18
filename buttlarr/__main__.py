from loguru import logger
from telegram import Updater

from .config import SERVICES, TELEGRAM_TOKEN


def init():
    pass


def main():
    logger.info('Creating bot...')
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    logger.info('Registering help commands...')
    # TODO pjordan: Add this

    logger.info('Registering services..')
    for s in SERVICES:
        def callback(update, context): s.handle_callback(update, context)
        for cmd in s.commands:
            updater.dispatcher.add_handler(CommandHandler(callback, cmd))

    logger.info('Registering callback handler..')

    def callback(update, context):
        service = SERVICES[0]
        service.handle_callback(update, context)
    updater.dispatcher.add_handler(CallbackQueryHandler(callback))

    logger.info('Start polling for messages..')
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
