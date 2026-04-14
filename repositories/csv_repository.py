import csv
from datetime import datetime

from config import DAILY_CSV, DATA_DIR, EVENTS_CSV, EXPORT_DIR
from services.dedup_service import is_duplicate_message, remember_last_message


class CsvRepository:
    def __init__(self):
        self.next_event_id = 1
        self.last_message_by_device = {}

    def init_files(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        if not EVENTS_CSV.exists():
            with EVENTS_CSV.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow([
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
                    "debt_value",
                    "debt_text",
                    "site_message_text",
                    "is_duplicate",
                ])
            self.next_event_id = 1
        else:
            with EVENTS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
                rows = list(csv.reader(f))
                if rows:
                    header = rows[0]
                    expected_header = [
                        "id", "datetime", "device_id", "device_raw", "device_group",
                        "device_name", "source_time_text", "source_url", "balance_value",
                        "balance_currency", "balance_text", "debt_value", "debt_text",
                        "site_message_text", "is_duplicate"
                    ]
                    if len(header) < len(expected_header) or "debt_value" not in header:
                        # Update schema: add missing columns with empty values
                        updated_rows = [expected_header]
                        for row in rows[1:]:
                            while len(row) < len(expected_header):
                                row.append("")
                            updated_rows.append(row)
                        with EVENTS_CSV.open("w", newline="", encoding="utf-8-sig") as fw:
                            writer = csv.writer(fw)
                            writer.writerows(updated_rows)
                        print("Обновлена схема events.csv")
                self.next_event_id = len(rows) if len(rows) > 1 else 1

        if not DAILY_CSV.exists():
            with DAILY_CSV.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Дата"])

        self.load_last_seen_messages()
        self.update_daily_group_csv()

    def load_last_seen_messages(self):
        self.last_message_by_device = {}

        if not EVENTS_CSV.exists():
            return

        with EVENTS_CSV.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                device_id = (row.get("device_id") or "").strip()
                site_message_text = (row.get("site_message_text") or "").strip()
                if device_id and site_message_text:
                    self.last_message_by_device[device_id] = site_message_text

    def write_event_row(
        self,
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
        debt_value,
        debt_text: str,
        site_message_text: str,
        is_duplicate: int,
    ):
        with EVENTS_CSV.open("a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.next_event_id,
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
                debt_value if debt_value is not None else "",
                debt_text,
                site_message_text,
                is_duplicate,
            ])

        self.next_event_id += 1

    def update_daily_group_csv(self):
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

                if not balance_raw or is_duplicate == "1" or not device_group or not dt_raw:
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

    def get_csv_row_count(self, csv_path):
        if not csv_path.exists():
            return 0
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        return max(len(rows) - 1, 0)

    def is_duplicate_message(self, device_id: str, site_message_text: str):
        return is_duplicate_message(self.last_message_by_device, device_id, site_message_text)

    def remember_last_message(self, device_id: str, site_message_text: str):
        remember_last_message(self.last_message_by_device, device_id, site_message_text)
