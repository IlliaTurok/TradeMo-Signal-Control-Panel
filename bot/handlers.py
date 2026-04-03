from telethon import events

from config import CONTROL_CHATS, DAILY_CSV, DAILY_XLSX, EVENTS_CSV, EVENTS_XLSX, TARGET_TEXT, chat
from services.export_service import csv_to_xlsx
from use_cases.process_signal import build_online_job_from_event


def register_handlers(client, repository, request_queue):
    @client.on(events.NewMessage(chats=chat))
    async def signal_handler(event):
        text_upper = (event.raw_text or "").upper()
        if TARGET_TEXT.upper() not in text_upper:
            return

        job = build_online_job_from_event(event)
        if not job:
            return

        await request_queue.put(job)
        print(f"[QUEUE] Задача добавлена для устройства {job['device_id']}. Размер очереди: {request_queue.qsize()}")

    @client.on(events.NewMessage(chats=CONTROL_CHATS, pattern=r"^/script$"))
    async def send_script_files(event):
        try:
            repository.update_daily_group_csv()

            csv_to_xlsx(EVENTS_CSV, EVENTS_XLSX, "events")
            csv_to_xlsx(DAILY_CSV, DAILY_XLSX, "daily_groups")

            events_count = repository.get_csv_row_count(EVENTS_CSV)
            daily_count = repository.get_csv_row_count(DAILY_CSV)

            await event.respond(
                f"Готово.\n"
                f"events: {events_count} строк\n"
                f"daily_groups: {daily_count} строк\n"
                f"Отправляю файлы..."
            )

            await client.send_file(
                entity=event.chat_id,
                file=str(DAILY_XLSX),
                caption="daily_groups.xlsx",
            )

            await client.send_file(
                entity=event.chat_id,
                file=str(EVENTS_XLSX),
                caption="events.xlsx",
            )

        except Exception as e:
            await event.respond(f"Ошибка при подготовке файлов: {e}")
