import telebot
import requests
import time
import threading

# Apna Bot Token aur Telegram Channel/Group ka ID yahan daalo
# (Agar personal chat me chalana hai toh apni chat_id number daal dena)
TOKEN = 'YOUR_BOT_TOKEN_HERE'
CHANNEL_ID = '@your_channel_username' 

bot = telebot.TeleBot(TOKEN)

# Tumhare Cloudflare Headers
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15; TECNO LJ8k Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/149.0.7827.159 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Cookie": "__cf_bm=JKZ0BlHlnVPWwaBNrjdE2kEueJRiaYTwdXcsn3Jis_s-1783791509.2740498-1.0.1.1-qr6qG9nCHoBIpiFQOOtrEZsV1l_WSeTxls7k2PRlfkw.t8uDCnCmN25VgTvm7iMXnk7P4nuyBQN8EmyXiAqTpd88NM3yvAgh2qCXpC4qLa22udg6VBLb3KkG1tiHeF79"
}

# State maintain karne ke liye global variables
last_period = None
last_message_id = None
current_prediction_color = None

def get_api_data():
    """API se latest period aur color fetch karne ka function"""
    try:
        current_ts = int(time.time() * 1000)
        api_url = f"https://draw.ar-lottery01.com/WinGo/WinGo_30S/GetHistoryIssuePage.json?ts={current_ts}"
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            
            # NOTE: JSON ka structure website par depend karta hai. 
            # Maan lo latest result data['data']['list'][0] me aata hai
            # Tumhe apne console print ke hisaab se isko adjust karna pad sakta hai
            latest_record = data['data']['list'][0]
            
            period = latest_record.get('issueNumber') # Period number
            color = latest_record.get('color')        # Red/Green/Violet
            
            return period, color
    except Exception as e:
        print(f"API Error: {e}")
    
    return None, None

def prediction_algorithm(last_color):
    """
    Yahan tum apna dimag aur logic laga sakte ho.
    Abhi ke liye main ek simple logic laga raha hu: Jo last aaya, wahi reverse kar do.
    """
    if last_color == "Red":
        return "Green"
    else:
        return "Red"

def automation_loop():
    """Ye loop background me lagatar chalta rahega"""
    global last_period, last_message_id, current_prediction_color
    
    while True:
        period, actual_color = get_api_data()
        
        # Agar API se data mila aur period change ho gaya hai (Naya game shuru hua)
        if period and period != last_period:
            
            # Agle game ka period number nikalna (e.g., 1234 -> 1235)
            try:
                next_period = str(int(period) + 1)
            except:
                next_period = "Unknown"
            
            result_text = ""
            
            # Agar pehle se koi prediction chal rahi thi, toh check karo wo pass hui ya fail
            if current_prediction_color:
                
                # 1. Purana Prediction Message Delete Karo
                if last_message_id:
                    try:
                        bot.delete_message(chat_id=CHANNEL_ID, message_id=last_message_id)
                        print("Purana message delete kar diya.")
                    except Exception as e:
                        print(f"Message delete nahi hua (Admin rights check karo): {e}")
                
                # 2. Win/Loss Status set karo
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
            
            # 3. Nayi Prediction Generate Karo
            current_prediction_color = prediction_algorithm(actual_color)
            
            # 4. Naya Message Format Banao
            msg_text = (
                f"{result_text}"
                f"🎯 **VIP PREDICTION LIVE** 🎯\n\n"
                f"🎮 Game: **WinGo 30S**\n"
                f"🔢 Period: `{next_period}`\n"
                f"💡 Predict: **{current_prediction_color}**\n\n"
                f"⏳ Hurry up! Place your bets now."
            )
            
            # 5. Channel/Chat me message bhejo aur uska ID save karo taaki agle round me delete kar sakein
            try:
                sent_msg = bot.send_message(chat_id=CHANNEL_ID, text=msg_text, parse_mode="Markdown")
                last_message_id = sent_msg.message_id
                last_period = period  # Period update kar do taaki loop ruke
                print(f"Naya message bhej diya period {next_period} ke liye.")
            except Exception as e:
                print(f"Message send karne me error: {e}")
        
        # Har 3 second me API check karega (30s game ke liye 3s delay best hai)
        time.sleep(3)

# Background me Automation Loop start karna
print("Bot Started! Fetching data...")
threading.Thread(target=automation_loop, daemon=True).start()

# Main bot ko zinda rakhna
bot.polling(none_stop=True)
