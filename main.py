import asyncio
from bothandler import bothandler

async def main():
    bot = bothandler()
    await bot.run()

if __name__ == "__main__":

    asyncio.run(main())