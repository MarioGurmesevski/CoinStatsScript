import time
import requests
import logging
import json
import os
from dotenv import load_dotenv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Replace with your bot token
CHAT_ID = os.getenv('CHAT_ID') # Replace with your chat ID

# JSON File for Portfolios
PORTFOLIOS_FILE = "portfolios.json"

CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH')
  # Path to chromedriver
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(threadName)s] %(message)s",
    datefmt="%H:%M:%S",
)


def load_portfolios():
    """Load portfolios from a JSON file."""
    if os.path.exists("portfolios.json"):
        with open("portfolios.json", "r") as file:
            try:
                # Parse the entire file as a single JSON array
                return json.load(file)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to load portfolios: {e}")
                return []  # Return an empty list if parsing fails
    return []

def load_tickers():
    if os.path.exists("tickers.json"):
        with open("tickers.json", "r") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return []
    return []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)s] %(message)s',
    datefmt='%H:%M:%S'
)


def send_telegram_message(message):
    """Send a message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        print("ERROR: Failed to send Telegram message")


def fetch_crypto_market_data(symbols):
    try:
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        }

        # Fetch global market data (for total market cap and dominance)
        global_url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        global_response = requests.get(global_url, headers=headers)
        global_response.raise_for_status()
        global_data = global_response.json()

        # Fetch cryptocurrency data (for individual symbols)
        coins_url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        params = {"start": 1, "limit": 250, "convert": "USD"}
        coins_response = requests.get(coins_url, headers=headers, params=params)
        coins_response.raise_for_status()
        coins_data = coins_response.json()["data"]

        # Find top gainer and loser across all cryptocurrencies
        top_gainer = max(
            (coin for coin in coins_data if coin["quote"]["USD"].get("percent_change_24h") is not None),
            key=lambda x: x["quote"]["USD"]["percent_change_24h"],
            default=None
        )
        top_loser = min(
            (coin for coin in coins_data if coin["quote"]["USD"].get("percent_change_24h") is not None),
            key=lambda x: x["quote"]["USD"]["percent_change_24h"],
            default=None
        )

        # Extract total market cap and dominance metrics
        total_market_cap = global_data["data"]["quote"]["USD"]["total_market_cap"]
        bitcoin_dominance = global_data["data"]["btc_dominance"]
        ethereum_dominance = global_data["data"]["eth_dominance"]
        altcoin_dominance = 100 - bitcoin_dominance - ethereum_dominance

        # Filter data for the requested symbols
        filtered_data = {}
        for symbol in symbols:
            coin_data = next((coin for coin in coins_data if coin["symbol"] == symbol), None)
            if coin_data:
                filtered_data[symbol] = {
                    "name": coin_data["name"],
                    "price": coin_data["quote"]["USD"].get("price"),
                    "change_24h": coin_data["quote"]["USD"].get("percent_change_24h"),
                }

        return {
            "filtered_data": filtered_data,
            "top_gainer": {"name": top_gainer["name"], "symbol": top_gainer["symbol"], "change": top_gainer["quote"]["USD"]["percent_change_24h"]} if top_gainer else None,
            "top_loser": {"name": top_loser["name"], "symbol": top_loser["symbol"], "change": top_loser["quote"]["USD"]["percent_change_24h"]} if top_loser else None,
            "total_market_cap": total_market_cap,
            "bitcoin_dominance": bitcoin_dominance,
            "ethereum_dominance": ethereum_dominance,
            "altcoin_dominance": altcoin_dominance,
        }
    except Exception as e:
        logging.error(f"Failed to fetch crypto market data: {e}")
        return None



def fetch_fear_and_greed_index():
    """Fetch the Fear & Greed Index."""
    try:
        url = "https://api.alternative.me/fng/"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        fear_and_greed_index = data["data"][0]["value"]
        sentiment = data["data"][0]["value_classification"]

        return fear_and_greed_index, sentiment
    except Exception as e:
        print(f"ERROR: Failed to fetch Fear & Greed Index: {e}")
        return None, None


def fetch_market_dominance():
    """Fetch Bitcoin and Ethereum dominance from CoinMarketCap."""
    try:
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY,
        }

        url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        bitcoin_dominance = data['data']['btc_dominance']
        ethereum_dominance = data['data']['eth_dominance']

        # Calculate Altcoin dominance
        altcoin_dominance = 100 - bitcoin_dominance - ethereum_dominance

        return bitcoin_dominance, ethereum_dominance, altcoin_dominance
    except Exception as e:
        print(f"ERROR: Failed to fetch market dominance: {e}")
        return None, None, None


def get_portfolio_data_selenium(portfolio_url):
    """Scrape portfolio data using Selenium."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    # Use WebDriver Manager to handle ChromeDriver setup
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(portfolio_url)
        time.sleep(5)

        username_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.UserInfoMenuItemWithTitleAndDesc_user-data-with-title-and-desc__lSn_8 h1'))
        )
        username = username_element.get_attribute("title") or username_element.text.strip()

        total_value_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "PortfolioPriceInfo_PT-price-info_price__AHDbL"))
        )
        total_value = float(total_value_element.text.strip("$").replace(",", ""))

        money_changed_span = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "PortfolioProfitInfo_PTProfitInfoPrice__NqSAb"))
        )
        money_changed = float(money_changed_span.get_attribute("title").replace("$", "").replace(",", "").strip())

        percentage_change_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "PortfolioProfitInfo_percentText__L7i9L"))
        )
        percentage_change = float(percentage_change_element.get_attribute("title").strip("%"))

        return username, total_value, percentage_change, money_changed

    except Exception as e:
        print(f"ERROR: Failed to fetch portfolio data: {e}")
        return None, None, None, None

    finally:
        driver.quit()

def send_crypto_market_update(market_data, fear_and_greed_index, sentiment):
    if market_data:
        current_time = datetime.now().strftime('%H:%M')

        # Construct the message dynamically for all cryptocurrencies in market_data
        crypto_updates = ""
        for symbol, data in market_data["filtered_data"].items():
            if data['price'] is not None:  # Skip entries with missing price
                crypto_updates += f"💰 {data['name']} ({symbol}): ${data['price']:.2f} ({data['change_24h']:+.2f}%)\n"

        # Include Top Gainer and Top Loser
        gainer_text = (
            f"🔥 Top Gainer: {market_data['top_gainer']['name']} ({market_data['top_gainer']['symbol']}) "
            f"(+{market_data['top_gainer']['change']:.2f}%)\n" if market_data.get("top_gainer") else ""
        )

        loser_text = (
            f"❄️ Top Loser: {market_data['top_loser']['name']} ({market_data['top_loser']['symbol']}) "
            f"({market_data['top_loser']['change']:.2f}%)\n\n" if market_data.get("top_loser") else ""
        )

        # Construct the full message
        message = (
            f"📈 <b>Crypto Market Update</b>\n\n"
            f"{crypto_updates}\n"
            f"{gainer_text}"
            f"{loser_text}"
            f"🌐 Total Market Cap: ${market_data['total_market_cap'] / 1e12:.2f}T\n"
            f"📊 BTC Dominance: {market_data['bitcoin_dominance']:.2f}%\n"
            f"📊 ETH Dominance: {market_data['ethereum_dominance']:.2f}%\n"
            f"📊 Altcoin Dominance: {market_data['altcoin_dominance']:.2f}%\n"
            f"😨 Fear & Greed Index: {fear_and_greed_index} ({sentiment})\n\n"
            f"🕒 Sent at: {current_time}"
        )

        send_telegram_message(message)

def monitor_market_updates():
    """Monitor and send regular market updates."""
    while True:
        symbols = load_tickers()

        # Fetch general market data and Fear & Greed Index
        market_data = fetch_crypto_market_data(symbols)

        fear_and_greed_index, sentiment = fetch_fear_and_greed_index()

        # Send market update if data is available
        if market_data:
            send_crypto_market_update(market_data, fear_and_greed_index, sentiment)

        # Timer for the next market update (30-minute interval with 10-second increments)
        for remaining in range(1800, 0, -10):  # Countdown from 1800 seconds (30 minutes) in steps of 10 seconds
            minutes, seconds = divmod(remaining, 60)
            logging.info(f"Next market update in: {minutes:02d}:{seconds:02d}")
            time.sleep(10)


def monitor_portfolios():
    """Monitor portfolios and send updates or alerts."""
    # Load portfolios from the JSON file
    portfolios = load_portfolios()

    # Dictionary to store previous values for each portfolio
    previous_values = {portfolio["name"]: None for portfolio in portfolios}

    while True:
        for portfolio in portfolios:
            try:
                # Extract portfolio details
                portfolio_url = portfolio["url"]
                threshold = portfolio["threshold"]
                portfolio_name = portfolio["name"]

                # Fetch portfolio data using Selenium
                username, total_value, percentage_change, money_changed = get_portfolio_data_selenium(portfolio_url)

                if total_value is not None and percentage_change is not None:
                    current_time = datetime.now().strftime('%H:%M')

                    # Calculate the difference from the previous value
                    previous_value = previous_values.get(portfolio_name)
                    if previous_value is not None:
                        value_difference = total_value - previous_value
                        portfolio["totalLostOrGainedSinceTheStartOfTheScript"] += value_difference
                        difference_text = f" ({'+' if value_difference > 0 else ''}{value_difference:.2f})"
                    else:
                        difference_text = ""  # No difference for the first iteration

                    # Update the previous value for next iteration
                    previous_values[portfolio_name] = total_value

                    change_emoji = "📈" if money_changed > 0 else "📉"

                    # Portfolio update message
                    update_message = (
                        f"📊 <b>{username} Update</b>\n\n"
                        f"💰 Current Value: ${total_value:.2f}{difference_text}\n"
                        f"{change_emoji} 24h Change: {percentage_change}%\n"
                        f"💵 Money Changed: ${money_changed:.2f}\n"
                        f"📊 Total Lost/Gained: "
                        f"${portfolio['totalLostOrGainedSinceTheStartOfTheScript']:.2f}\n\n"
                        f"🕒 Sent at: {current_time}"
                    )

                    send_telegram_message(update_message)

                    # Alert if threshold is crossed
                    if total_value >= threshold:
                        alert_message = (
                            f"🚀 <b>{portfolio_name} Alert</b>\n\n"
                            f"👤 Username: {username}\n"
                            f"💰 Current Value: ${total_value:.2f}\n"
                            f"⚠️ Threshold of ${threshold} crossed!\n\n"
                            f"🕒 Sent at: {current_time}"
                        )
                        for _ in range(3):  # Send alert multiple times
                            send_telegram_message(alert_message)
                            time.sleep(1)

            except Exception as e:
                logging.error(f"ERROR: {e}")

        # Timer for the next portfolio update (10-minute interval with 10-second increments)
        for remaining in range(600, 0, -10):
            minutes, seconds = divmod(remaining, 60)
            logging.info(f"Next portfolio update in: {minutes:02d}:{seconds:02d}")
            time.sleep(10)

if __name__ == "__main__":
    from threading import Thread

    # Run portfolio monitoring and market updates in parallel
    Thread(target=monitor_portfolios).start()
    Thread(target=monitor_market_updates).start()
