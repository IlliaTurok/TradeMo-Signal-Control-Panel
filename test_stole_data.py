from playwright.sync_api import sync_playwright

AUTH_FILE = "auth_trademo_bot.json"

def read_last_message(device_id: int | str):
    messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()

        page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

        # 1. первая карточка сообщения (последнее по времени)
        msg_cards = page.locator('a[href*="modal_message="]')
        msg_cards.first.wait_for(timeout=10000)
        first_msg = msg_cards.first

        href = first_msg.get_attribute("href")
        print("Ссылка сообщения:", href)

        # 2. Берём текст сообщения ИЗ ЭТОЙ КАРТОЧКИ
        msg_text = first_msg.locator("p.styles_messageText__TMXxy").inner_text()
        print("\n=== Текст из списка ===")
        print(msg_text)

        # 3. Кликаем, чтобы открыть модалку (если нужно)
        first_msg.click()

        # Если в модалке другой селектор — потом заменим здесь:
        # modal_text = page.locator("CSS_СЕЛЕКТОР_ТЕКСТА_В_МОДАЛКЕ").inner_text()
        # print("\n=== Текст из модалки ===")
        # print(modal_text)

        input("\nПосмотрел глазами? Enter чтобы закрыть...")
        context.close()
        browser.close()

if __name__ == "__main__":
    read_last_message(505655)