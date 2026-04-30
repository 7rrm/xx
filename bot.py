import telebot
from groq import Groq
import time

# ========================
# 🔐 الإعدادات
# ========================
TELEGRAM_BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
GROQ_API_KEY = "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"

# ========================
# إلغاء الـ webhook أولاً
# ========================
print("🔄 جاري إلغاء webhook الحالي...")
temp_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
try:
    result = temp_bot.remove_webhook()
    if result:
        print("✅ تم إلغاء webhook بنجاح")
    time.sleep(1)
except Exception as e:
    print(f"⚠️ ملاحظة: {e}")

# ========================
# تهيئة البوت الرئيسي
# ========================
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# الإعدادات الافتراضية
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 1
DEFAULT_MAX_TOKENS = 8192

# قائمة النماذج المتاحة
AVAILABLE_MODELS = {
    "1": {"name": "openai/gpt-oss-120b", "desc": "GPT-OSS 120B - نموذج متقدم"},
    "2": {"name": "openai/gpt-oss-20b", "desc": "GPT-OSS 20B - نسخة أسرع"},
    "3": {"name": "llama3-70b-8192", "desc": "Llama 3 70B - نموذج قوي"},
    "4": {"name": "llama3-8b-8192", "desc": "Llama 3 8B - سريع"},
    "5": {"name": "mixtral-8x7b-32768", "desc": "Mixtral - سياق طويل"},
    "6": {"name": "gemma2-9b-it", "desc": "Gemma 2 9B - من Google"}
}

# تخزين إعدادات المستخدمين
user_settings = {}
user_conversations = {}

def get_user_settings(user_id):
    if user_id not in user_settings:
        user_settings[user_id] = {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS
        }
    return user_settings[user_id]

def get_ai_response(user_id, user_message):
    try:
        settings = get_user_settings(user_id)
        
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        user_conversations[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        if len(user_conversations[user_id]) > 10:
            user_conversations[user_id] = user_conversations[user_id][-10:]
        
        completion = groq_client.chat.completions.create(
            model=settings["model"],
            messages=user_conversations[user_id],
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            top_p=1,
            stream=True
        )
        
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        if full_response.strip():
            user_conversations[user_id].append({
                "role": "assistant",
                "content": full_response
            })
        
        return full_response if full_response.strip() else "عذراً، لم أتمكن من توليد رد."
    
    except Exception as e:
        error_msg = str(e)
        print(f"خطأ: {error_msg}")
        if "rate_limit" in error_msg.lower():
            return "⚠️ تم تجاوز حد الطلبات المجانية."
        return f"⚠️ حدث خطأ: {error_msg[:100]}"

# ========================
# أوامر البوت
# ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "🤖 *مرحباً بك في بوت Groq AI!*\n\n"
        "🎛️ يمكنك تغيير النموذج عبر /model\n"
        "🌡️ تغيير درجة الحرارة عبر /temp\n"
        "🗑️ مسح المحادثة عبر /clear\n"
        "ℹ️ المساعدة عبر /help",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['model'])
def change_model(message):
    user_id = message.chat.id
    
    models_list = "*🎛️ النماذج المتاحة:*\n\n"
    for key, model in AVAILABLE_MODELS.items():
        current = " ✅" if get_user_settings(user_id)["model"] == model["name"] else ""
        models_list += f"`{key}` - {model['desc']}{current}\n"
    
    models_list += "\n*أرسل رقم النموذج* (مثال: 1)"
    
    sent_msg = bot.reply_to(message, models_list, parse_mode='Markdown')
    
    def handle_model_choice(msg):
        if msg.chat.id != user_id:
            return
        
        choice = msg.text.strip()
        if choice in AVAILABLE_MODELS:
            settings = get_user_settings(user_id)
            settings["model"] = AVAILABLE_MODELS[choice]["name"]
            user_settings[user_id] = settings
            bot.reply_to(msg, f"✅ تم تغيير النموذج إلى:\n*{AVAILABLE_MODELS[choice]['desc']}*", parse_mode='Markdown')
            if user_id in user_conversations:
                user_conversations[user_id] = []
        else:
            bot.reply_to(msg, "❌ رقم غير صالح")
        
        bot.clear_step_handler_by_chat_id(user_id)
    
    bot.register_next_step_handler(sent_msg, handle_model_choice)

@bot.message_handler(commands=['temp'])
def change_temperature(message):
    user_id = message.chat.id
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ مثال: `/temp 1.5`\nالمدى: 0-2", parse_mode='Markdown')
            return
        
        temp_value = float(parts[1])
        
        if 0 <= temp_value <= 2:
            settings = get_user_settings(user_id)
            settings["temperature"] = temp_value
            user_settings[user_id] = settings
            bot.reply_to(message, f"✅ تم تغيير درجة الحرارة إلى *{temp_value}*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ القيمة يجب أن تكون بين 0 و 2")
    except ValueError:
        bot.reply_to(message, "❌ أرسل رقماً صحيحاً")

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.chat.id
    user_conversations[user_id] = []
    bot.reply_to(message, "✅ تم مسح سجل المحادثة")

@bot.message_handler(commands=['settings'])
def show_settings(message):
    user_id = message.chat.id
    settings = get_user_settings(user_id)
    
    model_desc = "نموذج غير معروف"
    for key, model in AVAILABLE_MODELS.items():
        if model["name"] == settings["model"]:
            model_desc = model["desc"]
            break
    
    bot.reply_to(
        message,
        f"⚙️ *الإعدادات:*\n\n"
        f"📌 النموذج: {model_desc}\n"
        f"🌡️ الحرارة: {settings['temperature']}\n"
        f"📝 الحد الأقصى: {settings['max_tokens']}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        "📚 *الأوامر:*\n"
        "/model - تغيير النموذج\n"
        "/temp [0-2] - تغيير الحرارة\n"
        "/settings - الإعدادات الحالية\n"
        "/clear - مسح المحادثة\n"
        "/start - الترحيب",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    if message.text.startswith('/'):
        return
    
    user_id = message.chat.id
    bot.send_chat_action(user_id, 'typing')
    response = get_ai_response(user_id, message.text)
    
    if len(response) > 4000:
        for x in range(0, len(response), 4000):
            bot.reply_to(message, response[x:x+4000])
    else:
        bot.reply_to(message, response)

# ========================
# تشغيل البوت
# ========================
if __name__ == "__main__":
    print("🤖 بدء تشغيل البوت...")
    print("✅ البوت يعمل الآن!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
