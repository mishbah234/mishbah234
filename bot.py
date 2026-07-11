import telebot
import requests
import time
import threading
import os
from flask import Flask

# ... (Tumhara Token, Headers, get_api_data, prediction_algorithm aur automation_loop yahan same rahega) ...

# --- NAYA FLASK SERVER LOGIC ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Live and Running!"

def run_bot():
    print("Bot Started! Fetching data...")
    # Apna prediction loop start karo
    threading.Thread(target=automation_loop, daemon=True).start()
    # Bot ki polling start karo
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # 1. Telegram bot ko alag background thread me start karna
    threading.Thread(target=run_bot, daemon=True).start()
    
    # 2. Render ko satisfy karne ke liye Flask Web Server start karna
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
    
