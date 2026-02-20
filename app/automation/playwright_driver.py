import asyncio
import time
import uuid
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser

from app.automation.base_driver import TypingDriver, TypingResult
from app.automation.profiles import keystroke_delay, word_pause
from app.automation.metrics_collector import MetricsCollector
from app.config import settings
from app.models.enums import TypingProfileType


class PlaywrightTypingDriver(TypingDriver):
    def __init__(self, screenshots_dir: Path | None = None):
        self.screenshots_dir = screenshots_dir or Path(settings.SCREENSHOTS_DIR)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    async def _extract_text_from_words(self, page: Page) -> str:
        await page.wait_for_selector("#words", state="visible")

        letters = await page.query_selector_all("#words letter")

        text_parts = []
        for letter in letters:
            letter_text = await letter.inner_text()
            text_parts.append(letter_text)

        return "".join(text_parts)

    async def _get_results(self, page: Page) -> tuple[float, float]:
        await page.wait_for_selector("#result", state="visible", timeout=30000)

        wpm_text = await page.locator("#result .wpm .bottom").inner_text()
        wpm = float(wpm_text)

        acc_text = await page.locator("#result .acc .bottom").inner_text()
        accuracy = float(acc_text.rstrip("%"))

        return wpm, accuracy

    async def run(self, profile: TypingProfileType) -> TypingResult:
        session_id = str(uuid.uuid4())
        start_time = time.time()

        collector = MetricsCollector()
        collector.start()

        browser: Browser | None = None

        try:
            browser_start = time.time()

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                )

                browser_start_ms = (time.time() - browser_start) * 1000

                page = await browser.new_page(
                    viewport={"width": 1920, "height": 1080}
                )

                await page.goto("https://monkeytype.com", wait_until="networkidle")

                await page.wait_for_selector("#words", state="visible")

                screenshot_before = str(self.screenshots_dir / f"{session_id}_before.png")
                await page.screenshot(path=screenshot_before)

                text = await self._extract_text_from_words(page)

                await page.click("#words")

                for char in text:
                    await page.keyboard.press(char)

                    await keystroke_delay(profile)

                    if char == " ":
                        pause = word_pause(profile)
                        if pause > 0:
                            await asyncio.sleep(pause)

                wpm, accuracy = await self._get_results(page)

                screenshot_after = str(self.screenshots_dir / f"{session_id}_after.png")
                await page.screenshot(path=screenshot_after)

                duration_sec = time.time() - start_time

                peak_memory, peak_cpu = await collector.stop()

                await browser.close()

                return TypingResult(
                    wpm=wpm,
                    accuracy=accuracy,
                    duration_sec=duration_sec,
                    browser_start_ms=browser_start_ms,
                    peak_memory_mb=peak_memory,
                    peak_cpu_percent=peak_cpu,
                    screenshot_before=screenshot_before,
                    screenshot_after=screenshot_after,
                )

        except Exception:
            await collector.stop()
            if browser:
                await browser.close()
            raise
