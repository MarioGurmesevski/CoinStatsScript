import time
import logging
import os
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(threadName)s] %(message)s", datefmt="%H:%M:%S")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(message):
    """Send a message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        "disable_web_page_preview": True
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        print("ERROR: Failed to send Telegram message")

def load_portfolios():
    if os.path.exists("portfolios.json"):
        with open("portfolios.json", "r") as file:
            return json.load(file)
    return []

def get_portfolio_data_selenium(portfolio_url):
    """Scrape portfolio data using Selenium."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    # Initialize WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(portfolio_url)
        time.sleep(5)  # Allow page to load

        # Locate the username (try multiple strategies)
        username = None
        try:
            # First attempt: Using the original selector
            username_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.UserInfoMenuItemWithTitleAndDesc_user-data-with-title-and-desc__c2iGU h1'))
            )
            username = username_element.get_attribute("title") or username_element.text.strip()
        except Exception as e:
            logging.warning(f"First attempt to locate username failed: {e}")

        if not username:
            try:
                # Second attempt: Alternative selector (fallback)
                username_element_alt = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.UserInfoMenuItemWithTitleAndDesc_user-data-with-title-and-desc__c2iGU span'))
                )
                username = username_element_alt.get_attribute("title") or username_element_alt.text.strip()
            except Exception as e:
                logging.warning(f"Second attempt to locate username failed: {e}")

        if not username:
            logging.error("Failed to locate username using all known selectors. Setting username as 'Unknown'")
            username = "Unknown"

        # Locate total portfolio value
        total_value = float(WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.PortfolioPriceInfo_PT-price-info_price__xjt40'))
        ).get_attribute("title").strip("$").replace(",", ""))

        # Locate percentage change
        percentage_change = float(WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.PortfolioProfitInfo_percentText__3NKUK'))
        ).get_attribute("title").strip("%"))

        # Locate money changed in 24 hours
        money_changed = float(WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.PortfolioProfitInfo_PTProfitInfoPrice__79_kR'))
        ).get_attribute("title").replace("$", "").replace(",", "").strip())

        return username, total_value, percentage_change, money_changed

    except Exception as e:
        logging.error(f"ERROR: Failed to fetch portfolio data: {e}")
        return None, None, None, None

    finally:
        driver.quit()

def monitor_portfolios():
    """Monitor portfolios and send updates or alerts."""
    # Load portfolios from the JSON file
    portfolios = load_portfolios()

    # Dictionary to store previous values and total gain/loss for each portfolio
    previous_values = {portfolio["name"]: None for portfolio in portfolios}
    total_gain_loss = {portfolio["name"]: 0 for portfolio in portfolios}

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
                        total_gain_loss[portfolio_name] += value_difference
                        difference_text = f" ({'+' if value_difference > 0 else ''}{value_difference:.2f})"
                    else:
                        difference_text = ""  # No difference for the first iteration

                    # Update the previous value for the next iteration
                    previous_values[portfolio_name] = total_value

                    change_emoji = "📈" if money_changed > 0 else "📉"

                    # Portfolio update message
                    update_message = (
                        f"📊 <b>{username} Update</b>\n"
                        f"🔗 <b>Portfolio Link:</b> {portfolio_url}\n\n"
                        f"💰 Current Value: ${total_value:.2f}{difference_text}\n"
                        f"{change_emoji} 24h Change: {percentage_change}%\n"
                        f"💵 Money Changed: ${money_changed:.2f}\n"
                        f"📊 Total Lost/Gained: ${total_gain_loss[portfolio_name]:.2f}\n\n"
                        f"🕒 Sent at: {current_time}"
                    )

                    send_telegram_message(update_message)

                    # Send alert if the threshold is crossed
                    if total_value >= threshold:
                        alert_message = (
                            f"🚀 <b>{username} Alert</b>\n"
                            f"🔗 <b>Portfolio Link:</b> {portfolio_url}\n\n"
                            f"💰 Current Value: ${total_value:.2f}\n"
                            f"⚠️ Threshold of ${threshold} crossed!\n"
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
    monitor_portfolios()  # Run directly
