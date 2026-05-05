import asyncio
import psutil
from typing import Tuple

from app.automation.constants import BYTES_TO_MB, METRICS_POLL_INTERVAL


class MetricsCollector:
    def __init__(self):
        self._process = psutil.Process()
        self._start_memory: float = 0
        self._peak_memory: float = 0
        self._peak_cpu: float = 0
        self._running: bool = False
        self._task: asyncio.Task | None = None

    async def _collect_loop(self) -> None:
        self._start_memory = self._process.memory_info().rss / BYTES_TO_MB

        while self._running:
            mem_mb = self._process.memory_info().rss / BYTES_TO_MB
            cpu_percent = self._process.cpu_percent(interval=None)

            self._peak_memory = max(self._peak_memory, mem_mb)
            self._peak_cpu = max(self._peak_cpu, cpu_percent)

            await asyncio.sleep(METRICS_POLL_INTERVAL)

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._peak_memory = 0
        self._peak_cpu = 0

        self._task = asyncio.create_task(self._collect_loop())

    async def stop(self) -> Tuple[float, float]:
        if not self._running:
            return self._peak_memory, self._peak_cpu

        self._running = False

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=1.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

        return self._peak_memory, self._peak_cpu

    def get_current_values(self) -> Tuple[float, float]:
        return self._peak_memory, self._peak_cpu
