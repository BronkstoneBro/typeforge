import asyncio
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
from app.automation.constants import (
    ACTION_CHAINS_BATCH_SIZE,
    COOKIE_MODAL_TIMEOUT,
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
    PAGE_LOAD_TIMEOUT,
    POST_CLICK_DELAY,
    POST_COOKIE_DISMISS_DELAY,
    RESULT_EXTRACTION_DELAY,
    RESULT_WAIT_TIMEOUT,
    SCREENSHOT_AFTER_SUFFIX,
    SCREENSHOT_BEFORE_SUFFIX,
)
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

        driver.set_window_size(DEFAULT_VIEWPORT_WIDTH, DEFAULT_VIEWPORT_HEIGHT)
        return driver

    def _extract_text_from_words(self, driver: WebDriver) -> str:
        words_container = driver.find_element(By.ID, "words")

        words = words_container.find_elements(By.CSS_SELECTOR, ".word")

        text_parts = []
        for word_elem in words:
            letters = word_elem.find_elements(By.TAG_NAME, "letter")
            word_text = "".join(letter.text for letter in letters)
            text_parts.append(word_text)

        text = " ".join(text_parts)
        return text

    def _get_results(self, driver: WebDriver) -> tuple[float, float]:
        WebDriverWait(driver, RESULT_WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "result"))
        )

        time.sleep(RESULT_EXTRACTION_DELAY)

        wpm_element = driver.find_element(By.CSS_SELECTOR, "#result .wpm .bottom")
        wpm_text = wpm_element.text.strip()

        acc_element = driver.find_element(By.CSS_SELECTOR, "#result .acc .bottom")
        acc_text = acc_element.text.strip().rstrip("%")

        if not wpm_text:
            raise ValueError(f"WPM element is empty. Result HTML: {driver.find_element(By.ID, 'result').get_attribute('innerHTML')[:500]}")
        if not acc_text:
            raise ValueError(f"Accuracy element is empty. Result HTML: {driver.find_element(By.ID, 'result').get_attribute('innerHTML')[:500]}")

        wpm = float(wpm_text)
        accuracy = float(acc_text)

        return wpm, accuracy

    def _run_sync(self, profile: TypingProfileType, session_id: str) -> TypingResult:
        driver = None
        start_time = time.time()

        try:
            browser_start = time.time()
            driver = self._create_driver()
            browser_start_ms = (time.time() - browser_start) * 1000

            driver.get("https://monkeytype.com")

            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.ID, "words"))
            )

            try:
                cookie_modal = WebDriverWait(driver, COOKIE_MODAL_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#cookiesModal .acceptAll"))
                )
                cookie_modal.click()
                time.sleep(POST_COOKIE_DISMISS_DELAY)
            except Exception:
                pass

            screenshot_before = str(self.screenshots_dir / f"{session_id}{SCREENSHOT_BEFORE_SUFFIX}")
            driver.save_screenshot(screenshot_before)

            text = self._extract_text_from_words(driver)

            driver.execute_script("document.body.click();")
            time.sleep(POST_CLICK_DELAY)

            if profile == TypingProfileType.BEGINNER:
                base_delay = 0.200
            elif profile == TypingProfileType.INTERMEDIATE:
                base_delay = 0.100
            elif profile == TypingProfileType.EXPERT:
                base_delay = 0.050
            else:
                base_delay = 0.0

            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(driver)

            for i, char in enumerate(text):
                actions.send_keys(char)

                if base_delay > 0:
                    actions.pause(base_delay)

                if i % ACTION_CHAINS_BATCH_SIZE == (ACTION_CHAINS_BATCH_SIZE - 1):
                    actions.perform()
                    actions = ActionChains(driver)

            actions.perform()

            wpm, accuracy = self._get_results(driver)

            screenshot_after = str(self.screenshots_dir / f"{session_id}{SCREENSHOT_AFTER_SUFFIX}")
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
