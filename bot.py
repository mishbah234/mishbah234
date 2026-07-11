import telebot
import time
import os
import threading
from flask import Flask
import cloudscraper

# ==========================================
# 1. CONFIGURATION (Sirf Token Change Karo)
# ==========================================
TOKEN = 'YOUR_BOT_TOKEN_HERE'  # <--- APNA TOKEN YAHAN DAALO
bot = telebot.TeleBot(TOKEN)

# Cloudscraper Setup (Ab cookie ki zarurat nahi, yeh khud bypass karega)
scraper = cloudscraper.create_scraper() 
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# ==========================================
# 2. DATA FETCH & ALGORITHM (Auto Bypass)
# ==========================================
def get_api_data():
    try:
        current_ts = int(time.time() * 1000)
        api_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={current_ts}"
        
        # requests.get ki jagah hum scraper.get use kar rahe hain
        response = scraper.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            history_list = data['data']['list'][:10]
            latest_period = history_list[0].get('issueNumber')
            color_history = [item.get('color') for item in history_list]
            return latest_period, color_history
        else:
            print(f"Bypass Failed! Status Code: {response.status_code}")
    except Exception as e:
        print(f"API Error: {e}")
    return None, None

def advanced_prediction_algorithm(color_history):
    if not color_history or len(color_history) < 4: return "Red"
    
    recent_3 = color_history[:3]
    # Patterns
    if recent_3 == ['Red', 'Red', 'Red']: return "Green"
    elif recent_3 == ['Green', 'Green', 'Green']: return "Red"
    
    red_count = color_history.count('Red')
    green_count = color_history.count('Green')
    return "Red" if red_count > green_count else "Green"

# ==========================================
# 3. TELEGRAM COMMANDS
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "🚀 **VIP Prediction Bot Active!**\n\nCommands:\n/predict - Agla color janne ke liye")

@bot.message_handler(commands=['predict'])
def get_prediction(message):
    msg = bot.reply_to(message, "🔍 Market analyze kar raha hu...")
    period, color_history = get_api_data()
    
    if period:
        next_period = str(int(period) + 1)
        prediction = advanced_prediction_algorithm(color_history)
        result_msg = (
            f"🎯 **AI PREDICTION** 🎯\n\n"
            f"🎮 Game: WinGo 30S\n"
            f"🔢 Next Period: `{next_period}`\n"
            f"💡 Predict: **{prediction}**\n\n"
            f"⚠️ *Play at your own risk!*"
        )
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text=result_msg, parse_mode="Markdown")
    else:
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="❌ API Error! Security bahut high hai, baad me try karein.")

# ==========================================
# 4. SERVER & CRASH HANDLER (BULLETPROOF)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home(): 
    return "VIP Bot is Online with Cloudscraper Bypass!"

def run_bot():
    print("Bot Background Engine Starting...")
    
    # 404/409 Error Bypass
    try:
        bot.remove_webhook()
    except Exception:
        pass 

    # Bulletproof Polling Loop
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Server slow hai: {e}. 5 sec me restart kar raha hu...")
            time.sleep(5)

if __name__ == "__main__":
    # Bot Start
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Render Web Server
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
