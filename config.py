import os
import re
from pathlib import Path
from zoneinfo import ZoneInfo

def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


_load_env_file(Path(".env"))


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return int(raw_value.strip())


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_list_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None or not raw_value.strip():
        return default
    return [item.strip() for item in raw_value.split(",") if item.strip()]


api_id = _get_int_env("API_ID", 0)
api_hash = os.getenv("API_HASH", "").strip()
session_name = os.getenv("SESSION_NAME", "TradeMo Bot").strip() or "TradeMo Bot"

chat = os.getenv("CHAT", "trademo_sup_bot").strip() or "trademo_sup_bot"
CONTROL_CHATS = _get_list_env(
    "CONTROL_CHATS",
    [
        "@acspeaker",
        "pio_boss",
    ],
)

PROFILE_DIR = str(
    Path(os.getenv("PROFILE_DIR", "trademo-profile").strip() or "trademo-profile").resolve()
)
TARGET_TEXT = os.getenv("TARGET_TEXT", "disabled").strip() or "disabled"
RUN_OFFLINE_TODAY_AT_START = _get_bool_env("RUN_OFFLINE_TODAY_AT_START", True)

BASE_DIR = Path(".")
DATA_DIR = BASE_DIR / "data"
EXPORT_DIR = DATA_DIR / "exports"

EVENTS_CSV = DATA_DIR / "events.csv"
DAILY_CSV = DATA_DIR / "daily_groups.csv"

EVENTS_XLSX = EXPORT_DIR / "events.xlsx"
DAILY_XLSX = EXPORT_DIR / "daily_groups.xlsx"

LOCAL_TZ = ZoneInfo(os.getenv("LOCAL_TZ", "Europe/Moscow").strip() or "Europe/Moscow")

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
