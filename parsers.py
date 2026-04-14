import re

from config import BALANCE_RE, DEBT_RE, DEVICE_URL_RE, LOCAL_TZ


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
        match = DEVICE_URL_RE.search(source_url)
        if match:
            device_id = match.group(1)

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

    for url in urls:
        match = DEVICE_URL_RE.search(url)
        if match:
            return url, match.group(1)

    return "", None


def parse_balance(msg_text: str):
    match = BALANCE_RE.search(msg_text or "")
    if not match:
        return None, "", ""

    raw_num = match.group(2).replace(" ", "").replace("\u202f", "")
    try:
        balance_value = int(raw_num)
    except ValueError:
        return None, "", ""

    return balance_value, "RUB", match.group(0)


def parse_debt(msg_text: str):
    match = DEBT_RE.search(msg_text or "")
    if not match:
        return None, ""

    raw_num = match.group(2).replace(" ", "").replace("\u202f", "")
    try:
        debt_value = int(raw_num)
    except ValueError:
        return None, ""

    return debt_value, match.group(0)
