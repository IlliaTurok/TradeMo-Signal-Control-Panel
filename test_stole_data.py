from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

PROFILE_DIR = str(Path("trademo-profile").resolve())

def read_last_message(device_id: int | str):
    messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
        )

        page = context.new_page()
        page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

        msg_cards = page.locator('a[href*="modal_message="]')

        try:
            # ждём появление хотя бы одной карточки,
            # но если их реально нет — по таймауту просто выходим
            msg_cards.first.wait_for(timeout=15000)
        except PlaywrightTimeoutError:
            print("Сообщений нет или список не загрузился.")
            context.close()
            return

        count = msg_cards.count()
        if count == 0:
            print("Сообщений нет.")
            context.close()
            return

        first_msg = msg_cards.first

        href = first_msg.get_attribute("href")
        print("Ссылка сообщения:", href)

        msg_text = first_msg.locator("p.styles_messageText__TMXxy").inner_text()
        print("\n=== Текст из списка ===")
        print(msg_text)

        # Никаких кликов, модалок и input — сразу закрываем
        context.close()

if __name__ == "__main__":
    read_last_message(505655)