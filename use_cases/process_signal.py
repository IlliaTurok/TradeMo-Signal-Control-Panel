from parsers import extract_url_from_message_obj, parse_balance, parse_debt, parse_device, parse_time_from_event, parse_url


def build_online_job_from_event(event):
    print("\n=== Новое сообщение с disabled ===")
    print(event.raw_text)

    device_raw, device_group, device_name = parse_device(event.raw_text or "")
    source_time_text, event_time = parse_time_from_event(event)
    source_url, device_id = parse_url(event.raw_text or "")

    if not device_id:
        source_url, device_id = extract_url_from_message_obj(event.message)

    print(f"Устройство raw: {device_raw}, группа: {device_group}, имя: {device_name}")
    print(f"Время: {event_time}, текст времени: {source_time_text}")
    print(f"Ссылка: {source_url}, device_id: {device_id}")

    if not device_id:
        print("device_id не найден, пропускаю.")
        return None

    return {
        "device_id": device_id,
        "device_raw": device_raw,
        "device_group": device_group,
        "device_name": device_name,
        "source_time_text": source_time_text,
        "event_time": event_time,
        "source_url": source_url,
    }


async def process_online_job(job, repository, trademo_client):
    device_id = job["device_id"]
    device_raw = job["device_raw"]
    device_group = job["device_group"]
    device_name = job["device_name"]
    source_time_text = job["source_time_text"]
    event_time = job["event_time"]
    source_url = job["source_url"]

    print(f"\n[QUEUE] Обрабатываю устройство {device_id}")

    msg_text = await trademo_client.fetch_last_message_text_online(device_id)
    if not msg_text:
        print(f"[QUEUE] Не удалось получить последнее сообщение устройства {device_id}.")
        return

    print("=== Текст последнего сообщения ===")
    print(msg_text)

    duplicate = repository.is_duplicate_message(device_id, msg_text)
    if duplicate:
        print(f"[QUEUE] Полный дубль по устройству {device_id}. Balance будет пустым, сумма не обновится.")

    balance_value, balance_currency, balance_text = parse_balance(msg_text)
    debt_value, debt_text = parse_debt(msg_text)

    repository.write_event_row(
        dt=event_time,
        device_id=device_id,
        device_raw=device_raw,
        device_group=device_group,
        device_name=device_name,
        source_time_text=source_time_text,
        source_url=source_url,
        balance_value=None if duplicate else balance_value,
        balance_currency="" if duplicate else balance_currency,
        balance_text="" if duplicate else balance_text,
        debt_value=debt_value,
        debt_text=debt_text,
        site_message_text=msg_text,
        is_duplicate=1 if duplicate else 0,
    )

    if (not duplicate) and (balance_value is not None):
        repository.update_daily_group_csv()

    repository.remember_last_message(device_id, msg_text)

    print(f"[QUEUE] Записано в events.csv для устройства {device_id}.")
