import asyncio
import csv
import random
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telethon import TelegramClient, events
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from openpyxl import Workbook


# ============ CONFIG ============

api_id = 37853433
api_hash = "2b593ec952b6dc6134f101d599f8600a"
session_name = "TradeMo Bot"

chat = "trademo_sup_bot"

CONTROL_CHATS = [
    "@acspeaker",
    "pio_boss"
    # "@second_username",
    # 123456789,
    # -1001234567890,
]

PROFILE_DIR = str(Path("trademo-profile").resolve())
TARGET_TEXT = "disabled"

RUN_OFFLINE_TODAY_AT_START = True  # True = делать оффлайн-прогон при старте, False = сразу онлайн

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"

EVENTS_CSV = DATA_DIR / "events.csv"
DAILY_CSV = DATA_DIR / "daily_groups.csv"

EVENTS_XLSX = EXPORT_DIR / "events.xlsx"
DAILY_XLSX = EXPORT_DIR / "daily_groups.xlsx"

LOCAL_TZ = ZoneInfo("Europe/Moscow")

DEVICE_URL_RE = re.compile(
    r"https?://trademo\.io(?:/ru)?/devices/device/(\d+)",
    re.IGNORECASE,
)

BALANCE_RE = re.compile(
    r"(Доступно[: ]+|Баланс[: ]+)([\d\s\u202f]+)\s*₽",
    re.IGNORECASE,
)

NEXT_EVENT_ID = 1
LAST_MESSAGE_BY_DEVICE = {}
REQUEST_QUEUE = asyncio.Queue()

OFFLINE_PLAYWRIGHT = None
OFFLINE_BROWSER_CONTEXT = None
OFFLINE_BROWSER_PAGE = None


# ============ INIT FILES ============

def init_files():
    global NEXT_EVENT_ID

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not EVENTS_CSV.exists():
        with EVENTS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow([
                "id",
                "datetime",
                "device_id",
                "device_raw",
                "device_group",
                "device_name",
                "source_time_text",
                "source_url",
                "balance_value",
                "balance_currency",
                "balance_text",
                "site_message_text",
                "is_duplicate",
            ])
        NEXT_EVENT_ID = 1
    else:
        with EVENTS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
            NEXT_EVENT_ID = len(rows) if len(rows) > 1 else 1

    if not DAILY_CSV.exists():
        with DAILY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["Дата"])

    load_last_seen_messages()
    update_daily_group_csv()


def load_last_seen_messages():
    global LAST_MESSAGE_BY_DEVICE

    LAST_MESSAGE_BY_DEVICE = {}

    if not EVENTS_CSV.exists():
        return

    with EVENTS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            device_id = (row.get("device_id") or "").strip()
            site_message_text = (row.get("site_message_text") or "").strip()
            if device_id and site_message_text:
                LAST_MESSAGE_BY_DEVICE[device_id] = site_message_text


# ============ PARSERS ============

def parse_device(raw_text: str):
    device_raw = ""
    for line in (raw_text or "").splitlines():
        if "Устройство:" in line:
            device_raw = line.split("Устройство:", 1)[1].strip()
            break

    raw_no_space = device_raw.replace(" ", "")
    letters = []
    digits = []

    for ch in raw_no_space:
        if ch.isalpha() and not digits:
            letters.append(ch)
        elif ch.isdigit():
            digits.append(ch)

    device_group = "".join(letters).upper()
    device_name = "".join(digits)

    return device_raw, device_group, device_name


def parse_time_from_event(event):
    source_time_text = "N/A"
    raw_text = event.raw_text or ""

    for line in raw_text.splitlines():
        if "⏰ Время:" in line:
            source_time_text = line.split("⏰ Время:", 1)[1].strip() or "N/A"
            break

    event_time = event.message.date.astimezone(LOCAL_TZ)
    return source_time_text, event_time


def parse_url(raw_text: str):
    source_url = ""
    device_id = None

    for line in (raw_text or "").splitlines():
        if "Ссылка" in line and "(" in line and ")" in line:
            source_url = line.split("(", 1)[1].rsplit(")", 1)[0].strip()
            break

    if source_url:
        m = DEVICE_URL_RE.search(source_url)
        if m:
            device_id = m.group(1)

    return source_url, device_id


def extract_url_from_message_obj(msg):
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

    raw_text = msg.raw_text or ""
    text_urls = re.findall(r"https?://[^\s)]+", raw_text, flags=re.IGNORECASE)
    urls.extend(text_urls)

    for u in urls:
        m = DEVICE_URL_RE.search(u)
        if m:
            return u, m.group(1)

    return "", None


def parse_balance(msg_text: str):
    m = BALANCE_RE.search(msg_text or "")
    if not m:
        return None, "", ""

    raw_num = m.group(2).replace(" ", "").replace("\u202f", "")
    try:
        balance_value = int(raw_num)
    except ValueError:
        return None, "", ""

    return balance_value, "RUB", m.group(0)


# ============ CSV HELPERS ============

def write_event_row(
    dt: datetime,
    device_id: str,
    device_raw: str,
    device_group: str,
    device_name: str,
    source_time_text: str,
    source_url: str,
    balance_value,
    balance_currency: str,
    balance_text: str,
    site_message_text: str,
    is_duplicate: int,
):
    global NEXT_EVENT_ID

    with EVENTS_CSV.open("a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([
            NEXT_EVENT_ID,
            dt.isoformat(timespec="seconds"),
            device_id,
            device_raw,
            device_group,
            device_name,
            source_time_text,
            source_url,
            balance_value if balance_value is not None else "",
            balance_currency,
            balance_text,
            site_message_text,
            is_duplicate,
        ])

    NEXT_EVENT_ID += 1


def update_daily_group_csv():
    pivot = {}
    all_groups = set()

    if not EVENTS_CSV.exists():
        with DAILY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Дата"])
        return

    with EVENTS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            balance_raw = (row.get("balance_value") or "").strip()
            is_duplicate = (row.get("is_duplicate") or "0").strip()
            device_group = (row.get("device_group") or "").strip().upper()
            dt_raw = (row.get("datetime") or "").strip()

            if not balance_raw:
                continue
            if is_duplicate == "1":
                continue
            if not device_group:
                continue
            if not dt_raw:
                continue

            try:
                balance_value = int(balance_raw)
            except ValueError:
                continue

            try:
                date_str = datetime.fromisoformat(dt_raw).date().isoformat()
            except ValueError:
                continue

            if date_str not in pivot:
                pivot[date_str] = {}

            if device_group not in pivot[date_str]:
                pivot[date_str][device_group] = 0

            pivot[date_str][device_group] += balance_value
            all_groups.add(device_group)

    groups_sorted = sorted(all_groups)
    dates_sorted = sorted(pivot.keys(), reverse=True)

    with DAILY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Дата"] + groups_sorted)

        for date_str in dates_sorted:
            row = [date_str]
            for group in groups_sorted:
                value = pivot[date_str].get(group, 0)
                row.append(f"{value} ₽" if value else "")
            writer.writerow(row)


# ============ XLSX EXPORT ============

def csv_to_xlsx(csv_path: Path, xlsx_path: Path, sheet_name: str):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31] if sheet_name else "Sheet1"

    if csv_path.exists():
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for row in reader:
                ws.append(row)

    wb.save(xlsx_path)


def get_csv_row_count(csv_path: Path):
    if not csv_path.exists():
        return 0
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    return max(len(rows) - 1, 0)


# ============ OFFLINE BROWSER ============

async def init_offline_browser():
    global OFFLINE_PLAYWRIGHT, OFFLINE_BROWSER_CONTEXT, OFFLINE_BROWSER_PAGE

    if OFFLINE_BROWSER_CONTEXT is not None and OFFLINE_BROWSER_PAGE is not None:
        return

    OFFLINE_PLAYWRIGHT = await async_playwright().start()

    OFFLINE_BROWSER_CONTEXT = await OFFLINE_PLAYWRIGHT.chromium.launch_persistent_context(
        PROFILE_DIR,
        channel="chrome",
        headless=False,
        viewport=None,
    )

    pages = OFFLINE_BROWSER_CONTEXT.pages
    if pages:
        OFFLINE_BROWSER_PAGE = pages[0]
    else:
        OFFLINE_BROWSER_PAGE = await OFFLINE_BROWSER_CONTEXT.new_page()


async def close_offline_browser():
    global OFFLINE_PLAYWRIGHT, OFFLINE_BROWSER_CONTEXT, OFFLINE_BROWSER_PAGE

    try:
        if OFFLINE_BROWSER_CONTEXT is not None:
            await OFFLINE_BROWSER_CONTEXT.close()
    except Exception:
        pass

    try:
        if OFFLINE_PLAYWRIGHT is not None:
            await OFFLINE_PLAYWRIGHT.stop()
    except Exception:
        pass

    OFFLINE_PLAYWRIGHT = None
    OFFLINE_BROWSER_CONTEXT = None
    OFFLINE_BROWSER_PAGE = None


async def fetch_last_message_text_offline(device_id: str):
    await init_offline_browser()

    messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

    await asyncio.sleep(random.uniform(1.2, 3.4))

    try:
        await OFFLINE_BROWSER_PAGE.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

        msg_cards = OFFLINE_BROWSER_PAGE.locator('a[href*="modal_message="]')
        await msg_cards.first.wait_for(timeout=15000)

        count = await msg_cards.count()
        if count == 0:
            return None

        first_msg = msg_cards.first
        msg_text = await first_msg.locator("p.styles_messageText__TMXxy").inner_text()
        return msg_text

    except PlaywrightTimeoutError:
        return None
    except Exception as e:
        print(f"Ошибка OFFLINE Playwright для устройства {device_id}: {e}")
        return None


# ============ ONLINE HEADLESS FETCH ============

async def fetch_last_message_text_online(device_id: str):
    messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

    for attempt in range(1, 4):
        playwright = None
        context = None

        try:
            await asyncio.sleep(random.uniform(1.2, 3.4))

            playwright = await async_playwright().start()

            context = await playwright.chromium.launch_persistent_context(
                PROFILE_DIR,
                channel="chrome",
                headless=True,
                viewport=None,
            )

            page = context.pages[0] if context.pages else await context.new_page()

            await page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

            msg_cards = page.locator('a[href*="modal_message="]')
            await msg_cards.first.wait_for(timeout=15000)

            count = await msg_cards.count()
            if count == 0:
                return None

            first_msg = msg_cards.first
            msg_text = await first_msg.locator("p.styles_messageText__TMXxy").inner_text()
            return msg_text

        except PlaywrightTimeoutError:
            print(f"[ONLINE] Таймаут для устройства {device_id}, попытка {attempt}/3")
        except Exception as e:
            print(f"[ONLINE] Ошибка Playwright для устройства {device_id}, попытка {attempt}/3: {e}")
        finally:
            try:
                if context is not None:
                    await context.close()
            except Exception:
                pass

            try:
                if playwright is not None:
                    await playwright.stop()
            except Exception:
                pass

        if attempt < 3:
            await asyncio.sleep(random.uniform(2.0, 4.5))

    return None


# ============ DUPLICATE LOGIC ============

def is_duplicate_message(device_id: str, site_message_text: str):
    old_text = LAST_MESSAGE_BY_DEVICE.get(device_id)
    if old_text and old_text == site_message_text:
        return True
    return False


def remember_last_message(device_id: str, site_message_text: str):
    if device_id and site_message_text:
        LAST_MESSAGE_BY_DEVICE[device_id] = site_message_text


# ============ OFFLINE TODAY ============

async def offline_today(client: TelegramClient):
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

        msg_text = await fetch_last_message_text_offline(device_id)

        if not msg_text:
            print("Сообщений нет или список не загрузился.")
            continue

        print("=== Текст последнего сообщения ===")
        print(msg_text)

        duplicate = is_duplicate_message(device_id, msg_text)
        if duplicate:
            print("Дубль по этому устройству: balance будет пустым, в daily_groups.csv не пойдёт.")

        balance_value, balance_currency, balance_text = parse_balance(msg_text)

        msg = item["msg"]
        event_time = msg.date.astimezone(LOCAL_TZ)

        write_event_row(
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
            update_daily_group_csv()

        remember_last_message(device_id, msg_text)


# ============ ONLINE QUEUE WORKER ============

async def process_online_job(job):
    device_id = job["device_id"]
    device_raw = job["device_raw"]
    device_group = job["device_group"]
    device_name = job["device_name"]
    source_time_text = job["source_time_text"]
    event_time = job["event_time"]
    source_url = job["source_url"]

    print(f"\n[QUEUE] Обрабатываю устройство {device_id}")

    msg_text = await fetch_last_message_text_online(device_id)
    if not msg_text:
        print(f"[QUEUE] Не удалось получить последнее сообщение устройства {device_id}.")
        return

    print("=== Текст последнего сообщения ===")
    print(msg_text)

    duplicate = is_duplicate_message(device_id, msg_text)
    if duplicate:
        print(f"[QUEUE] Полный дубль по устройству {device_id}. Balance будет пустым, сумма не обновится.")

    balance_value, balance_currency, balance_text = parse_balance(msg_text)

    write_event_row(
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
        site_message_text=msg_text,
        is_duplicate=1 if duplicate else 0,
    )

    if (not duplicate) and (balance_value is not None):
        update_daily_group_csv()

    remember_last_message(device_id, msg_text)

    print(f"[QUEUE] Записано в events.csv для устройства {device_id}.")


async def online_worker():
    print("[QUEUE] Worker запущен, жду задачи...")

    while True:
        job = await REQUEST_QUEUE.get()
        try:
            await process_online_job(job)
        except Exception as e:
            print(f"[QUEUE] Ошибка обработки задачи: {e}")
        finally:
            REQUEST_QUEUE.task_done()


# ============ ONLINE LISTENER ============

client = TelegramClient(session_name, api_id, api_hash)


@client.on(events.NewMessage(chats=chat))
async def handler(event):
    text_upper = (event.raw_text or "").upper()
    if TARGET_TEXT.upper() not in text_upper:
        return

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
        return

    job = {
        "device_id": device_id,
        "device_raw": device_raw,
        "device_group": device_group,
        "device_name": device_name,
        "source_time_text": source_time_text,
        "event_time": event_time,
        "source_url": source_url,
    }

    await REQUEST_QUEUE.put(job)
    print(f"[QUEUE] Задача добавлена для устройства {device_id}. Размер очереди: {REQUEST_QUEUE.qsize()}")


# ============ COMMAND /SCRIPT ============

@client.on(events.NewMessage(chats=CONTROL_CHATS, pattern=r"^/script$"))
async def send_script_files(event):
    try:
        update_daily_group_csv()

        csv_to_xlsx(EVENTS_CSV, EVENTS_XLSX, "events")
        csv_to_xlsx(DAILY_CSV, DAILY_XLSX, "daily_groups")

        events_count = get_csv_row_count(EVENTS_CSV)
        daily_count = get_csv_row_count(DAILY_CSV)

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


# ============ MAIN ============

async def main():
    init_files()
    await client.start()

    if RUN_OFFLINE_TODAY_AT_START:
        print("Запускаю разовый оффлайн-прогон за сегодня...")
        await init_offline_browser()
        await offline_today(client)
        await close_offline_browser()
        print("Оффлайн-прогон завершён, браузер закрыт.")
    else:
        print("Оффлайн-прогон отключён, сразу перехожу в онлайн-режим.")

    asyncio.create_task(online_worker())

    print("Перехожу в онлайн-режим, жду сигналы...")
    print("Команда /script доступна в CONTROL_CHATS")

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())