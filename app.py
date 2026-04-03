import asyncio

from telethon import TelegramClient

from bot.handlers import register_handlers
from config import CONTROL_CHATS, RUN_OFFLINE_TODAY_AT_START, api_hash, api_id, session_name
from repositories.csv_repository import CsvRepository
from services.trademo_client import TradeMoClient
from use_cases.offline_backfill import offline_today
from use_cases.online_queue_worker import online_worker


async def main():
    repository = CsvRepository()
    trademo_client = TradeMoClient()
    client = TelegramClient(session_name, api_id, api_hash)
    request_queue = asyncio.Queue()

    register_handlers(client, repository, request_queue)

    repository.init_files()
    await client.start()

    if RUN_OFFLINE_TODAY_AT_START:
        print("Запускаю разовый оффлайн-прогон за сегодня...")
        await trademo_client.init_offline_browser()
        await offline_today(client, repository, trademo_client)
        await trademo_client.close_offline_browser()
        print("Оффлайн-прогон завершён, браузер закрыт.")
    else:
        print("Оффлайн-прогон отключён, сразу перехожу в онлайн-режим.")

    asyncio.create_task(online_worker(request_queue, repository, trademo_client))

    print("Перехожу в онлайн-режим, жду сигналы...")
    print(f"Команда /script доступна в {CONTROL_CHATS}")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
