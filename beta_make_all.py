import re
from datetime import datetime, timedelta
from pathlib import Path
from telethon import TelegramClient
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ==== Telegram config ====
api_id = 37853433
api_hash = '2b593ec952b6dc6134f101d599f8600a'
session_name = 'TradeMo Bot'
chat = 'trademo_sup_bot'

# ==== Playwright config ====
PROFILE_DIR = str(Path("trademo-profile").resolve())

DEVICE_URL_RE = re.compile(
    r'https?://trademo\.io(?:/ru)?/devices/device/(\d+)',
    re.IGNORECASE
)

TARGET_TEXT = 'disabled'


async def get_yesterday_device_ids_from_entities(client):
    """
    Берём все сообщения за вчера, в тексте которых есть 'disabled',
    и вытаскиваем device_id из URL в entities/buttons.
    """
    device_ids = set()
    today_local = datetime.now().date()
    yesterday_local = today_local - timedelta(days=2)

    async for msg in client.iter_messages(chat):
        msg_local_date = msg.date.astimezone().date()

        # как только дошли до сообщений старше вчерашнего дня — заканчиваем
        if msg_local_date < yesterday_local:
            break

        # пропускаем всё, что не вчера
        if msg_local_date != yesterday_local:
            continue

        text = (msg.raw_text or '').lower()
        if TARGET_TEXT.lower() not in text:
            continue

        urls = []

        if msg.entities:
            for ent in msg.entities:
                if hasattr(ent, "url") and ent.url:
                    urls.append(ent.url)

        if msg.buttons:
            for row in msg.buttons:
                for btn in row:
                    if getattr(btn, "url", None):
                        urls.append(btn.url)

        for u in urls:
            m = DEVICE_URL_RE.search(u)
            if m:
                device_ids.add(m.group(1))

    return sorted(device_ids)


def read_last_message_for_device_ids(device_ids):
    """
    Для каждого device_id открываем вкладку messages и читаем последнее сообщение.
    """
    if not device_ids:
        print("Ссылок на устройства за вчера не найдено (по disabled).")
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
        )
        page = context.new_page()

        for device_id in device_ids:
            messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"
            print(f"\n=== Устройство {device_id} ===")
            print(f"URL: {messages_url}")

            try:
                page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"Не получилось открыть страницу: {e}")
                continue

            msg_cards = page.locator('a[href*="modal_message="]')

            try:
                msg_cards.first.wait_for(timeout=15000)
            except PlaywrightTimeoutError:
                print("Сообщений нет или список не загрузился.")
                continue

            count = msg_cards.count()
            if count == 0:
                print("Сообщений нет.")
                continue

            first_msg = msg_cards.first

            href = first_msg.get_attribute("href")
            print("Ссылка сообщения:", href)

            try:
                msg_text = first_msg.locator("p.styles_messageText__TMXxy").inner_text()
            except Exception as e:
                print(f"Не удалось прочитать текст сообщения: {e}")
                continue

            print("=== Текст последнего сообщения ===")
            print(msg_text)

        context.close()


def main():
    client = TelegramClient(session_name, api_id, api_hash)
    client.start()

    print(f"Собираю устройства за вчера (по слову '{TARGET_TEXT}')...")
    device_ids = client.loop.run_until_complete(
        get_yesterday_device_ids_from_entities(client)
    )
    print(f"Найдено устройств за вчера: {len(device_ids)} -> {device_ids}")

    read_last_message_for_device_ids(device_ids)

    client.disconnect()


if __name__ == "__main__":
    main()