# Gulfood Exhibitor Scraper

This tool scrapes the exhibitor directory from the Gulfood website (https://exhibitors.gulfood.com/gulfood-2026/Exhibitor).

## Prerequisites

- Python 3.8+
- Playwright

## Installation

1. Clone the repository or download the files.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

## Usage

Run the scraper script:

```bash
python scraper.py
```

## Output

The scraper will generate two files in the `data/` directory:
- `exhibitors.csv`: CSV file with all exhibitor data.
- `exhibitors.json`: JSON file with the same data.

## Configuration

You can adjust the following variables in `scraper.py`:
- `MAX_SCROLL_ATTEMPTS`: Maximum number of times to scroll down (default: 100).
- `SCROLL_PAUSE_TIME`: Time to wait after each scroll (default: 2 seconds).
- `headless`: Set to `True` in `browser.launch()` for headless mode (no visible browser window).

## Notes

- The website uses infinite scroll. The scraper will scroll until no new content is loaded or the maximum attempts are reached.
- The scraping process can take a while depending on the number of exhibitors and your internet connection.
