import asyncio
from web_scraping import get_market_sentiment
from agents import StockAnalysisSystem
from autoemail import StockRecommendationEmailer
from typing import List
import logging
from logger_config import setup_logging

# Configure logging for all modules
setup_logging()
logger = logging.getLogger(__name__)


async def analyze_stocks(symbols: List[str]):
    """
    Main function to analyze stocks and send recommendations
    """
    try:
        stock_analysis = {}

        for symbol in symbols:
            # Initialize analysis system inside the loop to reset state for each stock
            analysis_system = StockAnalysisSystem()

            logger.info(f"Starting analysis for {symbol}")

            # Gather market data and news
            market_data = await get_market_sentiment(symbol)
            logger.info(f"Completed stock information retrieval")

            # Run agent analysis
            analysis_summary = await analysis_system.analyze_stock(market_data)
            logger.info(f"Completed agent analysis for {symbol}")

            stock_analysis[symbol] = analysis_summary

            # Wait between stocks to avoid overwhelming APIs
            await asyncio.sleep(5)

        # Initialize components
        emailer = StockRecommendationEmailer()
        # Send email with results
        email_success = emailer.send_email(stock_analysis)
        if email_success:
            logger.info("Successfully sent analysis email")
        else:
            logger.error("Failed to send analysis email")

    except Exception as e:
        logger.error(f"Error in stock analysis process: {str(e)}")


if __name__ == "__main__":
    # List of stock symbols to analyze
    with open("watchlist.txt", "r") as f:
        stock_symbols = [line.strip() for line in f if line.strip()]

    asyncio.run(analyze_stocks(stock_symbols))
