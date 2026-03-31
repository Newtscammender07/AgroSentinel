import requests
import os
from dotenv import load_dotenv

try:
    # 1. Try Streamlit Cloud's Secure Secrets First
    import streamlit as st
    TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
    TELEGRAM_CHAT_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    # 2. Fallback to Local PC .env file
    load_dotenv()
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
def send_telegram_alert(message, image_path=None):
    """
    Sends a message and an optional image to a Telegram Chat.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Warning: Telegram credentials not configured in .env file.")
        print("Required: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return False
        
    print(f"☁️ Sending Cloud Alert to Mobile...")
    
    # 1. Send the text message
    url_message = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload_message = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message
    }
    
    try:
        response = requests.post(url_message, json=payload_message)
        if response.status_code != 200:
            print(f"❌ Failed to send text message to Telegram: {response.text}")
    except Exception as e:
         print(f"❌ Telegram API Error sending text: {e}")
         return False

    # 2. Send the image (if provided)
    if image_path and os.path.exists(image_path):
        print("📷 Uploading captured photo to Telegram...")
        url_photo = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        
        try:
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                data = {'chat_id': TELEGRAM_CHAT_ID}
                response = requests.post(url_photo, files=files, data=data)
                
            if response.status_code == 200:
                print("✅ Telegram Alert + Photo Sent Successfully!")
                return True
            else:
                print(f"❌ Failed to send photo: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error uploading photo: {e}")
            return False
            
    return True

if __name__ == "__main__":
    # Test script standalone
    send_telegram_alert("🧪 TEST ALERT: Hello from AgroSentinel System!")
