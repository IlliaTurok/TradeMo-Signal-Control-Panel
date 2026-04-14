import re
from pathlib import Path
from zoneinfo import ZoneInfo

api_id = 37853433
api_hash = "2b593ec952b6dc6134f101d599f8600a"
session_name = "TradeMo Bot"

chat = "trademo_sup_bot"
CONTROL_CHATS = [
    "@acspeaker",
    "pio_boss",
    # "@second_username",
    # 123456789,
    # -1001234567890,
]

PROFILE_DIR = str(Path("trademo-profile").resolve())
TARGET_TEXT = "disabled"
RUN_OFFLINE_TODAY_AT_START = True

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

DEBT_RE = re.compile(
    r"(Оплата|Платеж).*?на ([\d\s\u202f]+)\s*₽",
    re.IGNORECASE,
)
