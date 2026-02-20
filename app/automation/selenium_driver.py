import asyncio
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

from app.automation.base_driver import TypingDriver, TypingResult
from app.automation.profiles import keystroke_delay, word_pause
from app.automation.metrics_collector import MetricsCollector
from app.config import settings
from app.models.enums import TypingProfileType


class SeleniumTypingDriver(TypingDriver):
    def __init__(self, screenshots_dir: Path | None = None):
        self.screenshots_dir = screenshots_dir or Path(settings.SCREENSHOTS_DIR)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _create_driver(self) -> WebDriver:
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Remote(
            command_executor=settings.SELENIUM_REMOTE_URL,
            options=options
        )

        driver.set_window_size(1920, 1080)
        return driver

    def _extract_text_from_words(self, driver: WebDriver) -> str:
        words_container = driver.find_element(By.ID, "words")
        letters = words_container.find_elements(By.TAG_NAME, "letter")
        text = "".join(letter.text for letter in letters)
        return text

    def _get_results(self, driver: WebDriver) -> tuple[float, float]:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "result"))
        )

        wpm_element = driver.find_element(By.CSS_SELECTOR, "#result .wpm .bottom")
        wpm = float(wpm_element.text)

        acc_element = driver.find_element(By.CSS_SELECTOR, "#result .acc .bottom")
        accuracy_text = acc_element.text.rstrip("%")
        accuracy = float(accuracy_text)

        return wpm, accuracy

    def _run_sync(self, profile: TypingProfileType, session_id: str) -> TypingResult:
        driver = None
        start_time = time.time()

        try:
            browser_start = time.time()
            driver = self._create_driver()
            browser_start_ms = (time.time() - browser_start) * 1000

            driver.get("https://monkeytype.com")

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "words"))
            )

            screenshot_before = str(self.screenshots_dir / f"{session_id}_before.png")
            driver.save_screenshot(screenshot_before)

            text = self._extract_text_from_words(driver)

            words_element = driver.find_element(By.ID, "words")
            words_element.click()

            for char in text:
                driver.switch_to.active_element.send_keys(char)

                if profile == TypingProfileType.BEGINNER:
                    base, jitter = 0.200, 0.080
                elif profile == TypingProfileType.INTERMEDIATE:
                    base, jitter = 0.100, 0.030
                elif profile == TypingProfileType.EXPERT:
                    base, jitter = 0.050, 0.015
                else:
                    base, jitter = 0.0, 0.0

                if base > 0:
                    delay = max(0, base + random.uniform(-jitter, jitter))
                    time.sleep(delay)

                if char == " ":
                    if profile == TypingProfileType.BEGINNER:
                        pause = random.uniform(0.3, 1.0)
                    elif profile == TypingProfileType.INTERMEDIATE:
                        pause = random.uniform(0.05, 0.15)
                    elif profile == TypingProfileType.EXPERT:
                        pause = random.uniform(0.0, 0.02)
                    else:
                        pause = 0.0

                    if pause > 0:
                        time.sleep(pause)

            wpm, accuracy = self._get_results(driver)

            screenshot_after = str(self.screenshots_dir / f"{session_id}_after.png")
            driver.save_screenshot(screenshot_after)

            duration_sec = time.time() - start_time

            return TypingResult(
                wpm=wpm,
                accuracy=accuracy,
                duration_sec=duration_sec,
                browser_start_ms=browser_start_ms,
                peak_memory_mb=0,
                peak_cpu_percent=0,
                screenshot_before=screenshot_before,
                screenshot_after=screenshot_after,
            )

        finally:
            if driver:
                driver.quit()

    async def run(self, profile: TypingProfileType) -> TypingResult:
        session_id = str(uuid.uuid4())

        collector = MetricsCollector()
        collector.start()

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._run_sync,
                profile,
                session_id
            )

            peak_memory, peak_cpu = await collector.stop()
            result.peak_memory_mb = peak_memory
            result.peak_cpu_percent = peak_cpu

            return result

        except Exception:
            await collector.stop()
            raise
