from datetime import datetime

from config import LOCAL_TZ, TARGET_TEXT, chat
from parsers import extract_url_from_message_obj, parse_balance, parse_device, parse_url


async def offline_today(client, repository, trademo_client):
    today = datetime.now(LOCAL_TZ).date()

    found_map = {}

    async for msg in client.iter_messages(chat):
        msg_local_date = msg.date.astimezone(LOCAL_TZ).date()

        if msg_local_date != today:
            continue

        text = (msg.raw_text or "").lower()
        if TARGET_TEXT not in text:
            continue

        device_raw, device_group, device_name = parse_device(msg.raw_text or "")
        source_url, device_id = parse_url(msg.raw_text or "")

        if not device_id:
            source_url, device_id = extract_url_from_message_obj(msg)

        if device_id and device_id not in found_map:
            found_map[device_id] = {
                "msg": msg,
                "device_raw": device_raw,
                "device_group": device_group,
                "device_name": device_name,
                "source_url": source_url,
                "device_id": device_id,
            }

    found = list(found_map.values())

    print(f"Найдено устройств за сегодня: {len(found)} -> {[x['device_id'] for x in found]}")

    for item in found:
        device_id = item["device_id"]
        print(f"\n=== Устройство {device_id} ===")
        print(f"URL: https://trademo.io/ru/devices/device/{device_id}?tab=messages")

        msg_text = await trademo_client.fetch_last_message_text_offline(device_id)
        if not msg_text:
            print("Сообщений нет или список не загрузился.")
            continue

        print("=== Текст последнего сообщения ===")
        print(msg_text)

        duplicate = repository.is_duplicate_message(device_id, msg_text)
        if duplicate:
            print("Дубль по этому устройству: balance будет пустым, в daily_groups.csv не пойдёт.")

        balance_value, balance_currency, balance_text = parse_balance(msg_text)

        msg = item["msg"]
        event_time = msg.date.astimezone(LOCAL_TZ)

        repository.write_event_row(
            dt=event_time,
            device_id=device_id,
            device_raw=item["device_raw"],
            device_group=item["device_group"],
            device_name=item["device_name"],
            source_time_text="offline_today",
            source_url=item["source_url"],
            balance_value=None if duplicate else balance_value,
            balance_currency="" if duplicate else balance_currency,
            balance_text="" if duplicate else balance_text,
            site_message_text=msg_text,
            is_duplicate=1 if duplicate else 0,
        )

        if (not duplicate) and (balance_value is not None):
            repository.update_daily_group_csv()

        repository.remember_last_message(device_id, msg_text)


async def offline_yesterday(client, repository, trademo_client):
    # Backward-compatible alias for older imports.
    await offline_today(client, repository, trademo_client)
