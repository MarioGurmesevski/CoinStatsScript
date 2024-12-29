from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Callback data identifiers
ADD_PORTFOLIO = "add_portfolio"
ADD_TICKER = "add_ticker"
REMOVE_TICKER = "remove_ticker"
BACK = "back"
NAME = "name"
URL = "url"
THRESHOLD = "threshold"
TICKER_NAME = "ticker_name"


# Load JSON data from files
def load_json_data():
    with open("portfolios.json", "r") as f:
        portfolios = json.load(f)
    with open("tickers.json", "r") as f:
        tickers = json.load(f)
    return portfolios, tickers

def save_json_data(portfolios, tickers):
    with open("portfolios.json", "w") as f:
        json.dump(portfolios, f, indent=4)
    with open("tickers.json", "w") as f:
        json.dump(tickers, f, indent=4)


# Load data into variables
portfolios, tickers = load_json_data()


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler."""
    await update.message.reply_text("Welcome! Use /commands to access the menu.")


# Commands menu
async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main commands menu."""
    keyboard = [
        [InlineKeyboardButton("Add Portfolio", callback_data=ADD_PORTFOLIO)],
        [InlineKeyboardButton("Add Ticker", callback_data=ADD_TICKER)],
        [InlineKeyboardButton("Remove Ticker", callback_data=REMOVE_TICKER)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)


# Handle button clicks and dynamic submenus
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks for adding/removing Tickers."""
    query = update.callback_query
    await query.answer()

    if query.data == ADD_PORTFOLIO:
        # Show fields for adding a portfolio
        keyboard = [
            [InlineKeyboardButton("Name", callback_data=NAME)],
            [InlineKeyboardButton("URL", callback_data=URL)],
            [InlineKeyboardButton("Threshold", callback_data=THRESHOLD)],
            [InlineKeyboardButton("Back", callback_data=BACK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    elif query.data == ADD_TICKER:
        # Show field for adding a ticker
        await query.edit_message_text("Please enter the name of the ticker to add:")
        context.user_data["current_field"] = TICKER_NAME

    elif query.data == REMOVE_TICKER:
        # Show a list of tickers to remove
        keyboard = [
            [InlineKeyboardButton(ticker, callback_data=f"remove_{ticker}")] for ticker in tickers
        ]
        keyboard.append([InlineKeyboardButton("Back", callback_data=BACK)])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a ticker to remove:", reply_markup=reply_markup)

    elif query.data.startswith("remove_"):
        # Remove the selected ticker
        ticker_to_remove = query.data.split("_")[1]
        if ticker_to_remove in tickers:
            tickers.remove(ticker_to_remove)
            save_json_data(portfolios, tickers)
            await query.edit_message_text(f"Ticker '{ticker_to_remove}' removed successfully!")
        else:
            await query.edit_message_text(f"Ticker '{ticker_to_remove}' not found.")

    elif query.data == NAME:
        # Collect portfolio name
        await query.edit_message_text("Please enter the portfolio name:")
        context.user_data["current_field"] = NAME

    elif query.data == URL:
        # Collect portfolio URL
        await query.edit_message_text("Please enter the portfolio URL:")
        context.user_data["current_field"] = URL

    elif query.data == THRESHOLD:
        # Collect portfolio threshold
        await query.edit_message_text("Please enter the portfolio threshold:")
        context.user_data["current_field"] = THRESHOLD

    elif query.data == BACK:
        # Return to the main menu
        keyboard = [
            [InlineKeyboardButton("Add Portfolio", callback_data=ADD_PORTFOLIO)],
            [InlineKeyboardButton("Add Ticker", callback_data=ADD_TICKER)],
            [InlineKeyboardButton("Remove Ticker", callback_data=REMOVE_TICKER)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Choose an option:", reply_markup=reply_markup)


# Handle user input for adding a portfolio or ticker
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user input for creating portfolios or tickers."""
    # Reload portfolios and tickers from JSON to ensure the latest state
    global portfolios, tickers
    portfolios, tickers = load_json_data()

    current_field = context.user_data.get("current_field")

    if current_field == NAME:
        # Save portfolio name in user data
        context.user_data["portfolio_name"] = update.message.text
        await update.message.reply_text(f"Portfolio name set to: {update.message.text}")

        # Redirect back to Add Portfolio menu
        keyboard = [
            [InlineKeyboardButton("Name", callback_data=NAME)],
            [InlineKeyboardButton("URL", callback_data=URL)],
            [InlineKeyboardButton("Threshold", callback_data=THRESHOLD)],
            [InlineKeyboardButton("Back", callback_data=BACK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    elif current_field == URL:
        # Save portfolio URL in user data
        context.user_data["portfolio_url"] = update.message.text
        await update.message.reply_text(f"Portfolio URL set to: {update.message.text}")

        # Redirect back to Add Portfolio menu
        keyboard = [
            [InlineKeyboardButton("Name", callback_data=NAME)],
            [InlineKeyboardButton("URL", callback_data=URL)],
            [InlineKeyboardButton("Threshold", callback_data=THRESHOLD)],
            [InlineKeyboardButton("Back", callback_data=BACK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    elif current_field == THRESHOLD:
        try:
            # Convert threshold value to float and save it in user data
            threshold_value = float(update.message.text)
            context.user_data["portfolio_threshold"] = threshold_value
            await update.message.reply_text(f"Portfolio threshold set to: {threshold_value}")

            # Check if all required fields are filled and save the portfolio
            if (
                "portfolio_name" in context.user_data and
                "portfolio_url" in context.user_data and
                "portfolio_threshold" in context.user_data
            ):
                new_portfolio = {
                    "name": context.user_data.get("portfolio_name"),
                    "url": context.user_data.get("portfolio_url"),
                    "threshold": context.user_data.get("portfolio_threshold"),
                    "totalLostOrGainedSinceTheStartOfTheScript": 0,
                }
                portfolios.append(new_portfolio)  # Add the new portfolio to the list
                save_json_data(portfolios, tickers)  # Save changes to JSON file
                await update.message.reply_text(f"Portfolio '{new_portfolio['name']}' added successfully!")

        except ValueError:
            # Handle invalid threshold input
            await update.message.reply_text("Invalid threshold value. Please enter a number.")

        # Redirect back to Add Portfolio menu regardless of success or failure
        keyboard = [
            [InlineKeyboardButton("Name", callback_data=NAME)],
            [InlineKeyboardButton("URL", callback_data=URL)],
            [InlineKeyboardButton("Threshold", callback_data=THRESHOLD)],
            [InlineKeyboardButton("Back", callback_data=BACK)],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Add Portfolio - Choose a field to set:", reply_markup=reply_markup)

    elif current_field == TICKER_NAME:
        # Process ticker name input
        ticker_name = update.message.text.upper()

        if ticker_name not in tickers:
            tickers.append(ticker_name)  # Add ticker to the list
            save_json_data(portfolios, tickers)  # Save changes to JSON file
            await update.message.reply_text(f"Ticker '{ticker_name}' added successfully!")
        else:
            await update.message.reply_text(f"Ticker '{ticker_name}' already exists.")

# Main function
def main() -> None:
    """Run the bot."""
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands))
    application.add_handler(CallbackQueryHandler(handle_menu))

    # Handle user input for adding a ticker or portfolio fields (name/URL/threshold)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    # Start polling for updates
    application.run_polling()

if __name__ == "__main__":
    main()




