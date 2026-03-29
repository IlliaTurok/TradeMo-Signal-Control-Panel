from playwright.sync_api import sync_playwright

AUTH_FILE = "auth_trademo_bot.json"
AUTH_URL = "https://trademo.io/auth"  # сюда вставь свежую ссылку с at=...

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(AUTH_URL, wait_until="domcontentloaded", timeout=60000)
        print("В окне Playwright откроется Trademo по одноразовой ссылке.")

        print("1) Дождись, пока ты окажешься в кабинете (страница сделок/устройств).")
        print("2) Ничего больше не делай, просто дождись загрузки.")
        input("Когда кабинет открыт, нажми Enter в консоли для сохранения состояния...")

        context.storage_state(path=AUTH_FILE)
        print(f"Состояние авторизации сохранено в {AUTH_FILE}")

        context.close()
        browser.close()

if __name__ == "__main__":
    main()