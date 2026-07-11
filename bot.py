import telebot
import requests
import time
import os
from flask import Flask

# ----------------- CONFIGURATION -----------------
TOKEN = '8217433227:AAEYXiH0wYOztkjU494uWfk5qyJ_BeYPpYY' # Yahan apna token daalna
bot = telebot.TeleBot(TOKEN)

headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; TECNO LJ8k Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.159 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "__cf_bm=JKZ0BlHlnVPWwaBNrjdE2kEueJRiaYTwdXcsn3Jis_s-1783791509.2740498-1.0.1.1-qr6qG9nCHoBIpiFQOOtrEZsV1l_WSeTxls7k2PRlfkw.t8uDCnCmN25VgTvm7iMXnk7P4nuyBQN8EmyXiAqTpd88NM3yvAgh2qCXpC4qLa22udg6VBLb3KkG1tiHeF79"
}

# ----------------- LOGIC -----------------
def get_api_data():
    try:
        current_ts = int(time.time() * 1000)
        api_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={current_ts}"
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            history_list = data['data']['list'][:10]
            latest_period = history_list[0].get('issueNumber')
            latest_color = history_list[0].get('color')
            color_history = [item.get('color') for item in history_list]
            return latest_period, latest_color, color_history
    except Exception as e:
        print(f"API Error: {e}")
    return None, None, None

def advanced_prediction_algorithm(color_history):
    if not color_history or len(color_history) < 4: return "Red"
    
    recent_3 = color_history[:3]
    if recent_3 == ['Red', 'Red', 'Red']: return "Green"
    elif recent_3 == ['Green', 'Green', 'Green']: return "Red"
    
    red_count = color_history.count('Red')
    green_count = color_history.count('Green')
    return "Red" if red_count > green_count else "Green"

# ----------------- COMMAND HANDLERS -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 **Welcome to VIP Predictor!**\n\nMain tumhare liye market trend analyze karta hu.\n\nCommands:\n/predict - Agla color janne ke liye")

@bot.message_handler(commands=['predict'])
def get_prediction(message):
    bot.reply_to(message, "🔍 Market analyze kar raha hu, please wait...")
    period, actual_color, color_history = get_api_data()
    
    if period:
        next_period = str(int(period) + 1)
        prediction = advanced_prediction_algorithm(color_history)
        
        msg = (
            f"🎯 **AI PREDICTION** 🎯\n\n"
            f"🎮 Game: WinGo 30S\n"
            f"🔢 Next Period: `{next_period}`\n"
            f"💡 Predict: **{prediction}**\n\n"
            f"Note: Yeh prediction algorithm base par hai, apne risk par khele."
        )
        bot.reply_to(message, msg, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ API Error: Server se response nahi mil raha, thodi der baad try karo.")

# ----------------- FLASK & RUNNER -----------------
app = Flask(__name__)
@app.route('/')
def home(): return "Bot is Online!"

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: bot.polling(none_stop=True)).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
