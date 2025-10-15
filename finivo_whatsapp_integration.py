import requests
import os


def _load_dotenv(path='.env'):
    """Lightweight .env loader: sets variables in os.environ if not already set."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except FileNotFoundError:
        # It's fine if there's no .env file
        pass


# Load local .env (if present) so we don't need to hard-code tokens in source
_load_dotenv()

# Load token from environment variable (set via OS env or .env file)
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

PHONE_NUMBER_ID = "848842828304712"  # Updated to correct phone number ID
USER_PHONE_NUMBER = "918999554776"   # Your verified test number (string)

def send_whatsapp_message(recipient_number, message):
    """
    Sends a message via WhatsApp Cloud API using your verified business number.
    """
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(recipient_number),  # must be string
        "type": "text",
        "text": {"body": message}
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        print("✅ Message sent successfully!")
    else:
        # Print response for debugging (but never print token)
        print("❌ Failed to send message:", response.text)
    return response


def _send_message_raw(recipient_number, message):
    """Returns the raw requests.Response from the WhatsApp API."""
    # Reuse send_whatsapp_message to keep logging consistent
    return send_whatsapp_message(recipient_number, message)

# Example usage
if __name__ == "__main__":
    send_whatsapp_message(USER_PHONE_NUMBER, "Hello from Finivo AI! Your WhatsApp Cloud API is connected.")