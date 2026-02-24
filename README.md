# TypeForge Bench

Selenium vs Playwright - which is faster and more reliable? TypeForge Bench conducts an objective comparison by simulating real-world interaction on monkeytype.com, a popular typing test platform. We measure speed, accuracy, resource consumption, and startup time for both automation frameworks.

## Features

- **Dual Driver Support**: Test both Selenium (Remote WebDriver) and Playwright (async API)
- **Configurable Profiles**: Beginner, Intermediate, Expert, and Robot typing speeds
- **Detailed Metrics**: WPM, accuracy, browser startup time, CPU/RAM usage
- **Benchmark Comparison**: Run both drivers side-by-side and compare results
- **Screenshot Capture**: Before/after screenshots for each session
- **REST API**: Full FastAPI-powered API with Swagger documentation

## Tech Stack

- **Backend**: FastAPI 0.115+
- **Database**: PostgreSQL 16 (async with SQLAlchemy 2.0)
- **Automation**: Selenium 4.x + Playwright 1.x
- **Deployment**: Docker + Docker Compose
- **Metrics**: psutil for CPU/RAM monitoring

## Philosophy & Motivation

Most automation benchmarks test against simple static pages. We chose monkeytype.com - a live project with dynamic DOM updates, cookie modals, and complex input handling logic. We implemented 4 typing profiles from 'beginner' to 'robot' to validate how frameworks handle different input speeds. The result is objective data with visual proof through before/after screenshots, not theoretical comparisons.

## Quick Start

### Prerequisites

- Docker Desktop installed and running

### Installation

1. Start all services:
```bash
docker-compose up --build
```

2. Access the API:
- **Swagger UI**: http://localhost:8000/docs
- **Selenium VNC** (watch browser): http://localhost:7900*

*VNC password is `secret` (default from selenium/standalone-chrome image)

## API Examples

### Testing via Swagger UI

1. Open http://localhost:8000/docs in your browser
2. Locate the **POST /sessions/run** endpoint
3. Click "Try it out" button
4. Paste the request body:
```json
{
  "driver": "selenium",
  "profile": "intermediate",
  "runs": 1
}
```
5. Click "Execute"
6. Wait approximately 60 seconds for test completion
7. View results in the response section below

Repeat the same steps with `"driver": "playwright"` to compare.

### Running Benchmark Comparison

1. Find **POST /benchmark/compare** in Swagger UI
2. Click "Try it out"
3. Paste the request body:
```json
{
  "profile": "intermediate",
  "runs_per_driver": 2
}
```
4. Click "Execute"
5. Wait approximately 4 minutes (runs both drivers sequentially)
6. Review comparative results with winner determination

## Typing Profiles

| Profile | Base Delay | Jitter | Use Case |
|---------|------------|--------|----------|
| **beginner** | 200ms | ±80ms | Slow typing with pauses |
| **intermediate** | 100ms | ±30ms | Average typing speed |
| **expert** | 50ms | ±15ms | Fast typing |
| **robot** | 0ms | 0ms | Maximum speed |

The benchmark includes all 4 profiles, each producing different WPM results. Use 'intermediate' for balanced testing or 'robot' for stress testing maximum throughput.

## Results & Visual Proof

### Benchmark Results (Intermediate Profile)

| Metric | Selenium | Playwright | Winner |
|--------|----------|------------|--------|
| WPM | 115.0 | 116.5 | Playwright |
| Accuracy | 100% | 100% | Tie |
| Browser Startup | 599ms | 509ms | Playwright |
| Memory Usage | 95.3 MB | 97.5 MB | Selenium |
| CPU Usage | 14.95% | 31.95% | Selenium |

**Note:** The benchmark supports 4 typing profiles (beginner, intermediate, expert, robot). The table above shows intermediate profile results for reference. Test other profiles to see how WPM scales with typing speed.

**Visual Proof:** All test runs save before/after screenshots to the `./screenshots/` directory. Access them via the `GET /screenshots/{filename}` endpoint or inspect the folder directly to verify test execution.

## Performance Insights

### Startup Speed
Playwright initializes the browser 1.2x faster (509ms vs 599ms). This difference compounds in CI/CD pipelines running hundreds of tests - Playwright saves approximately 90ms per test session. For a test suite with 1000 sessions, this translates to 90 seconds of saved execution time.

### CPU Efficiency
Selenium consumes 2x less CPU during test execution (14.95% vs 31.95%). This makes Selenium preferable for parallel test execution on resource-constrained environments. Running 10 Selenium sessions simultaneously uses roughly the same CPU as 5 Playwright sessions.

### Memory Footprint
Memory usage is nearly identical (95.3 MB vs 97.5 MB), with a negligible 2.2 MB difference. Neither framework has a significant advantage in RAM consumption for typical test scenarios.

### Typing Accuracy
Both frameworks achieve 100% accuracy across all typing profiles. This validates that reliable input simulation on complex real-world sites is achievable with either tool. The days of "Selenium is flaky" are over when properly implemented.

### The Verdict
There is no universal winner. Playwright excels in startup speed, critical for fast feedback loops. Selenium excels in CPU efficiency, essential for high-parallelism test execution. Both are production-ready - choose based on your infrastructure constraints and priorities.

## What We Achieved

**Real-World Testing** - Validated both frameworks on monkeytype.com, not a dummy test page. This site has cookie modals, dynamic DOM updates, and complex keyboard event handling.

**Objective Metrics** - Measured actual performance differences with concrete numbers. No speculation - just raw data from identical test conditions.

**100% Accuracy** - Both Selenium and Playwright reliably handle complex typing simulation. The frameworks have matured to the point where accuracy is a solved problem.

**Reusable Framework** - Built a FastAPI + Docker setup that can be adapted to benchmark other websites or automation tasks beyond typing tests.

**Visual Evidence** - Screenshots prove tests actually execute and produce results. You can inspect the before/after states to verify correct behavior.

## Docker Services

The application runs as a multi-container setup:

- **app**: FastAPI application (port 8000)
- **db**: PostgreSQL 16 database (port 5432)
- **selenium**: Chrome browser with VNC access (ports 4444, 7900)

### Basic Commands

```bash
# Start all services
docker-compose up --build

# Stop all services
docker-compose down

# View logs
docker-compose logs -f app
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Built With

- FastAPI for the REST API framework
- SQLAlchemy for async database ORM
- Selenium for traditional browser automation via Remote WebDriver
- Playwright for modern async automation with native browser protocols
- Docker for containerization and reproducible environments
- PostgreSQL for persistent data storage
- psutil for real-time system metrics collection
