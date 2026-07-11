import telebot
import requests
import time
import os
import threading
from flask import Flask

# ==========================================
# 1. CONFIGURATION (Sirf Token Change Karo)
# ==========================================
TOKEN = '8212126889:AAGWBN6dMhyufJU51KlbRG94PGeW3IgEYPo'  # <--- APNA TOKEN YAHAN DAALO
bot = telebot.TeleBot(TOKEN)

# Cloudflare Cookie (Jab bot API Error de, toh isko browser se naya laakar yahan badalna)
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; TECNO LJ8k Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.159 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "__cf_bm=JKZ0BlHlnVPWwaBNrjdE2kEueJRiaYTwdXcsn3Jis_s-1783791509.2740498-1.0.1.1-qr6qG9nCHoBIpiFQOOtrEZsV1l_WSeTxls7k2PRlfkw.t8uDCnCmN25VgTvm7iMXnk7P4nuyBQN8EmyXiAqTpd88NM3yvAgh2qCXpC4qLa22udg6VBLb3KkG1tiHeF79"
}

# ==========================================
# 2. DATA FETCH & ALGORITHM
# ==========================================
def get_api_data():
    try:
        current_ts = int(time.time() * 1000)
        api_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={current_ts}"
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            history_list = data['data']['list'][:10]
            latest_period = history_list[0].get('issueNumber')
            color_history = [item.get('color') for item in history_list]
            return latest_period, color_history
    except Exception as e:
        print(f"API Error: {e}")
    return None, None

def advanced_prediction_algorithm(color_history):
    if not color_history or len(color_history) < 4: return "Red"
    
    recent_3 = color_history[:3]
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
        bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id, text="❌ API Error! Cookie update karo.")

# ==========================================
# 4. SERVER & CRASH HANDLER (BULLETPROOF)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home(): 
    return "Bot is Online and Bulletproof!"

def run_bot():
    print("Bot Background Engine Starting...")
    
    # 404/409 Error ko chup-chaap bypass karne ka tarika
    try:
        bot.remove_webhook()
    except Exception:
        pass 

    # Agar server drop ho, toh bot crash nahi hoga, dobara try karega
    while True:
        try:
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Telegram server hichki le raha hai: {e}. 5 sec me restart kar raha hu...")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
