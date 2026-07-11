import telebot
import requests
import time
import threading
import os
from flask import Flask

# ==========================================
# 1. CREDENTIALS & SETTINGS (Yahan Changes Karo)
# ==========================================
TOKEN = '8212126889:AAGWBN6dMhyufJU51KlbRG94PGeW3IgEYPo'  # Apna Telegram Bot Token yahan daalo
CHANNEL_ID = '@shadex_predict' # Apne Channel ka username ya Chat ID daalo (-100xxxxxx)

bot = telebot.TeleBot(TOKEN)

# ==========================================
# 2. CLOUDFLARE BYPASS HEADERS
# ==========================================
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; TECNO LJ8k Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.159 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "__cf_bm=JKZ0BlHlnVPWwaBNrjdE2kEueJRiaYTwdXcsn3Jis_s-1783791509.2740498-1.0.1.1-qr6qG9nCHoBIpiFQOOtrEZsV1l_WSeTxls7k2PRlfkw.t8uDCnCmN25VgTvm7iMXnk7P4nuyBQN8EmyXiAqTpd88NM3yvAgh2qCXpC4qLa22udg6VBLb3KkG1tiHeF79"
}

# ==========================================
# 3. STATE VARIABLES (Bot ki memory)
# ==========================================
last_period = None
last_message_id = None
current_prediction_color = None

# ==========================================
# 4. DATA FETCH & ADVANCED ALGORITHM
# ==========================================
def get_api_data():
    """API se latest 10 results nikalna"""
    try:
        current_ts = int(time.time() * 1000)
        api_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={current_ts}"
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            history_list = data['data']['list'][:10] # Last 10 records
            
            latest_period = history_list[0].get('issueNumber') 
            latest_color = history_list[0].get('color')        
            
            # Pichle 10 colors ki list banana ['Red', 'Green', ...]
            color_history = [item.get('color') for item in history_list]
            
            return latest_period, latest_color, color_history
    except Exception as e:
        print(f"API Error: {e}")
    return None, None, None

def advanced_prediction_algorithm(color_history):
    """VIP PATTERN RECOGNITION ENGINE"""
    if not color_history or len(color_history) < 4:
        return "Red" # Default fallback
        
    recent_3 = color_history[:3]
    recent_4 = color_history[:4]
    
    # 1. DRAGON TREND BREAKER
    if recent_3 == ['Red', 'Red', 'Red']:
        return "Green" 
    elif recent_3 == ['Green', 'Green', 'Green']:
        return "Red"
        
    # 2. ZIG-ZAG PATTERN DETECTOR
    if recent_3 == ['Red', 'Green', 'Red']:
        return "Green"
    elif recent_3 == ['Green', 'Red', 'Green']:
        return "Red"
        
    # 3. DOUBLE-DOUBLE PATTERN
    if recent_4 == ['Red', 'Red', 'Green', 'Green']:
        return "Red"
    elif recent_4 == ['Green', 'Green', 'Red', 'Red']:
        return "Green"
        
    # 4. MOMENTUM FREQUENCY
    red_count = color_history.count('Red')
    green_count = color_history.count('Green')
    
    if red_count > green_count:
        return "Red"
    elif green_count > red_count:
        return "Green"
    else:
        return "Red"

# ==========================================
# 5. AUTOMATION LOOP (Main Engine)
# ==========================================
def automation_loop():
    global last_period, last_message_id, current_prediction_color
    
    while True:
        period, actual_color, color_history = get_api_data()
        
        if period and period != last_period:
            try:
                next_period = str(int(period) + 1)
            except:
                next_period = "Unknown"
            
            result_text = ""
            
            # Purane result ko check karna aur message update karna
            if current_prediction_color:
                if last_message_id:
                    try:
                        bot.delete_message(chat_id=CHANNEL_ID, message_id=last_message_id)
                    except Exception as e:
                        print(f"Delete Error: {e}")
                
                # Check Win or Loss
                if current_prediction_color.lower() in actual_color.lower():
                    status = "✅ **WIN**"
                else:
                    status = "❌ **LOSS**"
                
                result_text = (
                    f"📊 **LAST GAME RESULT**\n"
                    f"🔸 Period: `{period}`\n"
                    f"🔸 Result: **{actual_color}**\n"
                    f"🔸 Status: {status}\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                )
            
            # Naya Prediction Generate karna
            current_prediction_color = advanced_prediction_algorithm(color_history)
            confidence = "95%" if color_history[:2] == ['Red', 'Red'] or color_history[:2] == ['Green', 'Green'] else "88%"
            
            msg_text = (
                f"{result_text}"
                f"🎯 **PREMIUM AI PREDICTION** 🎯\n\n"
                f"🎮 Game: **WinGo 30S**\n"
                f"🔢 Period: `{next_period}`\n"
                f"💡 Predict: **{current_prediction_color}**\n"
                f"🔥 Confidence: `{confidence}`\n\n"
                f"⏳ Hurry up! Place your bets now."
            )
            
            # Naya Message Bhejna
            try:
                sent_msg = bot.send_message(chat_id=CHANNEL_ID, text=msg_text, parse_mode="Markdown")
                last_message_id = sent_msg.message_id
                last_period = period  
                print(f"Message Sent for Period: {next_period}")
            except Exception as e:
                print(f"Send Error: {e}")
        
        # Har 3 second me API ko check karna
        time.sleep(3)

# ==========================================
# 6. FLASK WEB SERVER (For Render Free Tier)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Premium Bot is Live and Running smoothly on Render!"

def run_bot():
    print("Bot Background Engine Started!")
    # Loop ko alag thread me chalana taaki bot freeze na ho
    threading.Thread(target=automation_loop, daemon=True).start()
    # Telegram server se polling start karna
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # Bot Engine Start
    threading.Thread(target=run_bot, daemon=True).start()
    
    # Render Server Start (0.0.0.0 is very important for Render)
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
