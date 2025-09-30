import yfinance as yf
from typing import List, Dict, Any
import time
import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

from logger_config import setup_logging

# Configure logging for all modules
setup_logging()
logger = logging.getLogger(__name__)


async def get_stock_data(symbol: str) -> Dict[str, Any]:
    """
    Get stock market data using yfinance. (No changes applied here.)
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        # Fetch 1 month of historical data
        hist = stock.history(period="1mo")

        return {
            "symbol": symbol,
            "current_price": info.get("currentPrice", None),
            "target_price": info.get("targetMeanPrice", None),
            "recommendation": info.get("recommendationKey", None),
            "price_history": {
                k.strftime("%Y-%m-%d"): v for k, v in hist["Close"].to_dict().items()
            },
            "volume_history": {
                k.strftime("%Y-%m-%d"): v for k, v in hist["Volume"].to_dict().items()
            },
            "pe_ratio": info.get("forwardPE", None),
            "market_cap": info.get("marketCap", None),
            "dividend_yield": info.get("dividendYield", None),
            "sector": info.get("sector", None),
            "fifty_day_average": info.get("fiftyDayAverage", None),
            "two_hundred_day_average": info.get("twoHundredDayAverage", None),
            "high_52week": info.get("fiftyTwoWeekHigh", None),
            "low_52week": info.get("fiftyTwoWeekLow", None),
        }

    except Exception as e:
        logging.error(f"Error fetching stock data via yfinance for {symbol}: {str(e)}")
        return {}


async def get_yahoo_finance_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Uses Playwright to launch a browser, wait for JavaScript to render content,
    and then scrape the research reports using BeautifulSoup.
    """
    all_articles = []
    url = f"https://finance.yahoo.com/quote/{symbol}/"

    try:
        # Initialize Playwright
        async with async_playwright() as p:
            # Launch the browser in headless mode
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            logger.info(f"Navigating to {url} using Playwright")

            # Navigate to the page and wait for the DOM to be fully loaded
            await page.goto(url, wait_until="load", timeout=300_000)

            # Wait for the dynamic content to load
            # Selector targets the first non-skeleton section element within the listContainer
            reports_list_selector = (
                'div.listContainer section:not([data-testid="skeleton-loader"])'
            )

            logger.info("Waiting for research reports to load")

            # Playwright waits until the element matching the selector appears
            await page.wait_for_selector(reports_list_selector, timeout=120_000)

            # Get the fully rendered HTML content
            content = await page.content()

            # Close the page and browser
            await page.close()
            await browser.close()

            logger.info("Content successfully rendered and scraped.")

            # Use BeautifulSoup to parse the fully rendered content
            soup = BeautifulSoup(content, "html.parser")

            research_reports_section = soup.find(
                "section", {"data-testid": "research-report"}
            )

            if research_reports_section:
                list_container = research_reports_section.find(
                    "div", class_="listContainer"
                )

                if list_container:
                    # Find all inner section tags which contain the report data
                    report_items = list_container.find_all("section")

                    for item_section in report_items:
                        if len(all_articles) >= 15:
                            logger.info("Reached 15 item limit for research reports.")
                            break

                        # Find Title (h3.title)
                        h3_tag = item_section.find("h3", class_="title")
                        headline = h3_tag.get_text(strip=True) if h3_tag else None

                        # Find Description (p.summary)
                        p_tag = item_section.find("p", class_="summary")
                        description = (
                            p_tag.get_text(strip=True) if p_tag else "No summary found."
                        )

                        if not headline:
                            # Skip boilerplate or incomplete sections
                            continue

                        all_articles.append(
                            {
                                "source": "Yahoo Finance - Research Reports (Playwright)",
                                "title": headline,
                                "content": f"Summary: {description}",
                                "type": "research_report",
                            }
                        )
                        time.sleep(0.1)

                    logger.info(f"Extracted {len(all_articles)} research reports.")
                else:
                    logger.warning(
                        "listContainer div not found within research-reports section."
                    )
            else:
                logger.warning(
                    "Research reports section [data-testid=research-report] not found."
                )

    except Exception as e:
        # Catches errors like Timeouts if the content doesn't load within 30 seconds
        logger.error(
            f"Playwright operation failed (e.g., Timeout or Browser error): {str(e)}",
            exc_info=True,
        )
        return []

    return all_articles


async def get_market_sentiment(symbol: str) -> Dict[str, Any]:
    """
    Consolidate stock data and research reports into one output.
    """
    try:
        # 1. Get research reports
        logging.info(f"Getting Yahoo Finance research reports for {symbol}")
        # This call now uses Playwright
        articles = await get_yahoo_finance_news(symbol)

        # 2. Get stock data
        logging.info(f"Getting stock data for {symbol} via yfinance")
        stock_data = await get_stock_data(symbol)

        # Log collection summary
        logging.info(f"Collected {len(articles)} research reports for {symbol}")

        # Count articles by type
        article_types = {}
        for article in articles:
            article_type = article["type"]
            article_types[article_type] = article_types.get(article_type, 0) + 1

        logging.info(
            "Article type breakdown: "
            + ", ".join([f"{k}: {v}" for k, v in article_types.items()])
        )

        # Renamed output key to reflect content change
        return {
            "symbol": symbol,
            "research_reports": articles,
            "stock_data": stock_data,
        }

    except Exception as e:
        logging.error(f"Error in get_market_sentiment: {str(e)}", exc_info=True)
        return {
            "symbol": symbol,
            "research_reports": [],
            "stock_data": {},
        }
