import requests

TELEGRAM_BOT_TOKEN = '7798925167:AAEzvmt_OjBZzE0m9GDmxs25F83_-zDb-0s'
CHAT_ID = '6931444291'

def send_test_message():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': '🚀 Test message from my portfolio bot!',
        'parse_mode': 'HTML'
    }
    response = requests.post(url, json=payload)
    print(response.json())  # Print the Telegram API response for debugging

send_test_message()
