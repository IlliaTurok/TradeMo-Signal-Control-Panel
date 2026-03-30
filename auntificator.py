from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path("trademo-profile").resolve())
AUTH_URL = "https://trademo.io/auth?at=aExMUjg2bER1d3Uza1pmSzFxK2xnZlllUUxhQlhyTjJhb2p2aXFoVVl2c2dNWWdyRXBDZ3Z2eUxHN0RQYXBleVhwWmtOSitPQkZXei8xSk5vbWhUUjlnd3dEaW9zRVlZWU1CeHdVRXNXams1K0xpZC9FT1pXUmM2cEhjeE1Mc0N6amxOeFd0Ymdla1hMdDRUNlBaa2dYN21STGRPOEtyVEF0cmN6SGpzaHNGWWtZSTMyV0ZTN0JMcWJYL3FncGhBZFJTZ3BTSE5hTFB2WHBNcUhFbHJucVdXQVRWdlk5bFlaeDRMeDBuTmpoc3VFVkZrclA3UHJlL0Q5MVdKZTljPS0tcUljUXVRN0VFL2hGelIvWS0tS1dUc1RudXVFNmZZMDVlTVd1eG9uQT09"  # сюда вставляй одноразовую ссылку

def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
        )

        page = context.new_page()
        page.goto(AUTH_URL, wait_until="domcontentloaded", timeout=60000)

        print("Открылся Trademo.")
        print("Дождись входа в кабинет и полной загрузки страницы.")
        input("Когда кабинет открыт, нажми Enter...")

        print(f"Профиль сохранен в: {PROFILE_DIR}")
        context.close()

if __name__ == "__main__":
    main()