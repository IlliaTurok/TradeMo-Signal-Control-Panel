import os
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path("trademo-profile").resolve())


def _get_auth_url() -> str:
    auth_url = os.getenv("AUTH_URL", "").strip()
    if not auth_url:
        raise RuntimeError("Set AUTH_URL in environment before running authenticator.py")
    return auth_url

def main():
    auth_url = _get_auth_url()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
        )

        page = context.new_page()
        page.goto(auth_url, wait_until="domcontentloaded", timeout=60000)

        print("Открылся Trademo.")
        print("Дождись входа в кабинет и полной загрузки страницы.")
        input("Когда кабинет открыт, нажми Enter...")

        print(f"Профиль сохранен в: {PROFILE_DIR}")
        context.close()

if __name__ == "__main__":
    main()