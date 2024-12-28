from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Define states for conversation
NAME, URL, THRESHOLD = range(3)
TICKER_NAME = range(1)



# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /add_portfolio to add a new portfolio /add_ticker to add a ticker.")


# Add portfolio command
async def add_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the portfolio name:")
    return NAME


# Handle name input
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Enter the portfolio URL:")
    return URL


# Handle URL input
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['url'] = update.message.text
    await update.message.reply_text("Enter the threshold value (must be a number):")
    return THRESHOLD


# Handle threshold input and validate it
async def handle_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Validate that the input is a number
        threshold = float(update.message.text)
        context.user_data['threshold'] = threshold

        # Create portfolio dictionary
        portfolio = {
            "name": context.user_data['name'],
            "url": context.user_data['url'],
            "threshold": context.user_data['threshold'],
            "totalLostOrGainedSinceTheStartOfTheScript": 0
        }

        # Load existing portfolios or initialize an empty list
        portfolios = []
        if os.path.exists("portfolios.json"):
            with open("portfolios.json", "r") as file:
                portfolios = json.load(file)

        # Append new portfolio and save back to the file
        portfolios.append(portfolio)
        with open("portfolios.json", "w") as file:
            json.dump(portfolios, file, indent=4)

        await update.message.reply_text(f"Portfolio added successfully:\n{portfolio}")
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Invalid input. Please enter a valid number for the threshold:")
        return THRESHOLD


async def add_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the ticker symbol (e.g., BTC, SOL, ETH):")
    return TICKER_NAME

async def handle_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticker = update.message.text.upper()  # Convert to uppercase for consistency

    # Load existing tickers or initialize an empty list
    tickers = []
    if os.path.exists("tickers.json"):
        with open("tickers.json", "r") as file:
            tickers = json.load(file)

    # Check if the ticker already exists
    if ticker in tickers:
        await update.message.reply_text(f"The ticker '{ticker}' already exists.")
        return ConversationHandler.END

    # Add new ticker and save back to the file
    tickers.append(ticker)
    with open("tickers.json", "w") as file:
        json.dump(tickers, file, indent=4)

    await update.message.reply_text(f"Ticker '{ticker}' added successfully.")
    return ConversationHandler.END

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END

# Main function
def main():
    # Replace 'YOUR_API_TOKEN' with your bot's token from BotFather
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Define conversation handler for /add_portfolio
    conv_handler_portfolio = ConversationHandler(
        entry_points=[CommandHandler('add_portfolio', add_portfolio)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)],
            THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_threshold)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Define conversation handler for /add_ticker
    conv_handler_ticker = ConversationHandler(
        entry_points=[CommandHandler('add_ticker', add_ticker)],
        states={
            TICKER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ticker)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler_portfolio)
    application.add_handler(conv_handler_ticker)

    # Start polling for updates
    application.run_polling()

if __name__ == '__main__':
    main()
