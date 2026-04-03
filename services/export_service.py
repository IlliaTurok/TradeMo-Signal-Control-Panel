import csv
from pathlib import Path

from openpyxl import Workbook


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
