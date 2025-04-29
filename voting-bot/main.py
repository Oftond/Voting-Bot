import asyncio
from bothandler import bothandler

if __name__ == "__main__":
    bot_handler = bothandler()
    asyncio.run(bot_handler.run())