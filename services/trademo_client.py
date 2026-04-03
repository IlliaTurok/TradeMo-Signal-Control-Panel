import asyncio
import random

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from config import PROFILE_DIR


class TradeMoClient:
    def __init__(self):
        self._offline_playwright = None
        self._offline_browser_context = None
        self._offline_browser_page = None

    async def init_offline_browser(self):
        if self._offline_browser_context is not None and self._offline_browser_page is not None:
            return

        self._offline_playwright = await async_playwright().start()

        self._offline_browser_context = await self._offline_playwright.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="chrome",
            headless=False,
            viewport=None,
        )

        pages = self._offline_browser_context.pages
        if pages:
            self._offline_browser_page = pages[0]
        else:
            self._offline_browser_page = await self._offline_browser_context.new_page()

    async def close_offline_browser(self):
        try:
            if self._offline_browser_context is not None:
                await self._offline_browser_context.close()
        except Exception:
            pass

        try:
            if self._offline_playwright is not None:
                await self._offline_playwright.stop()
        except Exception:
            pass

        self._offline_playwright = None
        self._offline_browser_context = None
        self._offline_browser_page = None

    async def fetch_last_message_text_offline(self, device_id: str):
        await self.init_offline_browser()

        messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

        await asyncio.sleep(random.uniform(1.2, 3.4))

        try:
            await self._offline_browser_page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

            msg_cards = self._offline_browser_page.locator('a[href*="modal_message="]')
            await msg_cards.first.wait_for(timeout=15000)

            count = await msg_cards.count()
            if count == 0:
                return None

            first_msg = msg_cards.first
            return await first_msg.locator("p.styles_messageText__TMXxy").inner_text()

        except PlaywrightTimeoutError:
            return None
        except Exception as e:
            print(f"Ошибка OFFLINE Playwright для устройства {device_id}: {e}")
            return None

    async def fetch_last_message_text_online(self, device_id: str):
        messages_url = f"https://trademo.io/ru/devices/device/{device_id}?tab=messages"

        for attempt in range(1, 4):
            playwright = None
            context = None

            try:
                await asyncio.sleep(random.uniform(1.2, 3.4))

                playwright = await async_playwright().start()

                context = await playwright.chromium.launch_persistent_context(
                    PROFILE_DIR,
                    channel="chrome",
                    headless=True,
                    viewport=None,
                )

                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)

                msg_cards = page.locator('a[href*="modal_message="]')
                await msg_cards.first.wait_for(timeout=15000)

                count = await msg_cards.count()
                if count == 0:
                    return None

                first_msg = msg_cards.first
                return await first_msg.locator("p.styles_messageText__TMXxy").inner_text()

            except PlaywrightTimeoutError:
                print(f"[ONLINE] Таймаут для устройства {device_id}, попытка {attempt}/3")
            except Exception as e:
                print(f"[ONLINE] Ошибка Playwright для устройства {device_id}, попытка {attempt}/3: {e}")
            finally:
                try:
                    if context is not None:
                        await context.close()
                except Exception:
                    pass

                try:
                    if playwright is not None:
                        await playwright.stop()
                except Exception:
                    pass

            if attempt < 3:
                await asyncio.sleep(random.uniform(2.0, 4.5))

        return None
