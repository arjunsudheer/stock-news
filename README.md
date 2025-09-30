# stock-news
This repository is dedicated to StockNews, which is a multi-agent system that provides stock recommendation based on current market trends.

StockNews is an automated stock recommendation service that provides users with a buy, sell, or hold recommendation on their watchlist. I have configured a chron job that runs every weekday at 5:30 am PST, so users can receive a stock recommendation email everyday before the stock market opens at 6:00 am PST.

StockNews consists of three parts:
1. Stock data collection
2. Analyst debate
3. Autoemail creation


### Stock Data Collection

The stock data collection stage uses the **Yahoo Finance API** to retrieve current information on a company's stock, including values such as the current stock price, 52-week high, 52-week low, PE ratio, and more.

To retrieve relevant and up-to-date news, I web scrape the Yahoo Finance page for a given stock using **Beautiful Soup**. I use **Playwright** to allow JavaScript to load all the components, and I then scrape the Research Reports section for up-to-date news articles.

This information is then fed to the analysts for debate.

### Analyst Debate

The analyst debate consists of a multi-agent system. I use  SelectorGroupChat from **Autogen**, consisting of the following agents powered by **Llama 3.1**:

* ***Debate Facilitator:*** This agent is responsible for prompting each analyst on their opinion, and following up with questions when an analyst does not provide specific information. This agent is also responsible for asking each analyst on their opinion of the other analysts' opinion.
* ***Buy Agent:*** This agent is responsible for finding reasons to buy a stock, including when a stock has potential for growth.
* ***Sell Agent:*** This agent is responsible for finding reasons to sell a stock, including identifying when a stock may be overvalued.
* ***Hold Agent:*** This agent is responsible for finding reasons to hold a stock, including analyzing the trend in the current stock price relevant to its 52-week high and low, as well as the PE ratio.
* ***Summarizer Agent:*** This agent is responsible for summarizing the debate, explaining the general consensus recommendation, and the key points from each agent. This agent's response will be included in the autoemail.

The Sell, Buy, and Hold Agents are equipped with a web search tool, powered by DuckDuckGo Search. This tool allows the agents to search up relevant information to prove their point in the debate, or fact check another agent's claim.

I also include a moderator agent, powered by **Llama Guard 3**. I filter the Summarizer Agent's output and use the moderator agent to identify any potential harmful content that may be included, as the Summarizer Agent's response will be included in the autoemail. I only allow summaries that are classified as "safe", or an "S6" hazard classification, as stock recommendation are inherently financially risky. Ignoring the S6 financial hazard class reduces false positives to make this service useful for its users.

### Autoemail Creation

After getting the Summarizer Agent's summary, and verifying that the content is safe via the moderator agent, I construct one autoemail that contains the summary for each stock in the user's watchlist. I use the Gmail SMTP server for authentication and sending the email. 