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
DEFAULT_MAX_TOKENS = 2000

# ========================
# قائمة جميع النماذج المتاحة في Groq
# ========================
AVAILABLE_MODELS = {
    # 🤖 نماذج الإنتاج (Production)
    "1": {"name": "openai/gpt-oss-120b", "desc": "GPT-OSS 120B - نموذج متقدم من OpenAI"},
    "2": {"name": "openai/gpt-oss-20b", "desc": "GPT-OSS 20B - نسخة أسرع وأخف"},
    "3": {"name": "llama-3.3-70b-versatile", "desc": "Llama 3.3 70B - نموذج قوي من Meta"},
    "4": {"name": "llama-3.1-8b-instant", "desc": "Llama 3.1 8B - سريع جداً (560 رمز/ثانية)"},
    "5": {"name": "mixtral-8x7b-32768", "desc": "Mixtral 8x7B - سياق طويل 32K"},
    
    # 🎯 نماذج المعاينة الجديدة (Preview)
    "6": {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "desc": "Llama 4 Scout 17B - أحدث نماذج Meta"},
    "7": {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "desc": "Llama 4 Maverick 17B - متقدم"},
    "8": {"name": "qwen/qwen3-32b", "desc": "Qwen 3 32B - من阿里巴巴 (استدلال قوي)"},
    "9": {"name": "qwen/qwen3-14b", "desc": "Qwen 3 14B - نسخة متوسطة"},
    "10": {"name": "qwen/qwen3-8b", "desc": "Qwen 3 8B - نسخة سريعة"},
    "11": {"name": "moonshotai/kimi-k2-instruct-0905", "desc": "Kimi K2 - سياق عملاق 262K رمز"},
    "12": {"name": "deepseek-r1-distill-llama-70b", "desc": "DeepSeek R1 - استدلال متقدم"},
    "13": {"name": "mistral-saba-24b", "desc": "Mistral Saba - ممتاز للغة العربية"},
    "14": {"name": "allam-2-7b", "desc": "ALLaM 2 7B - نموذج عربي"},
    "15": {"name": "gemma2-9b-it", "desc": "Gemma 2 9B - من Google"},
    "16": {"name": "google/gemma-2-2b-it", "desc": "Gemma 2 2B - خفيف وسريع جداً"},
    
    # 🛠️ الأنظمة المتكاملة
    "17": {"name": "groq/compound", "desc": "Compound - نظام متكامل (بحث ويب + كود)"},
    "18": {"name": "groq/compound-mini", "desc": "Compound Mini - نسخة أخف من النظام المتكامل"},
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
        
        # إدارة سجل المحادثة
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        user_conversations[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # الاحتفاظ بآخر 6 رسائل فقط
        if len(user_conversations[user_id]) > 6:
            user_conversations[user_id] = user_conversations[user_id][-6:]
        
        completion = groq_client.chat.completions.create(
            model=settings["model"],
            messages=user_conversations[user_id],
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            top_p=1,
            stream=False
        )
        
        full_response = completion.choices[0].message.content
        
        if full_response.strip():
            if len(full_response) < 3000:
                user_conversations[user_id].append({
                    "role": "assistant",
                    "content": full_response
                })
        
        return full_response if full_response.strip() else "عذراً، لم أتمكن من توليد رد."
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ خطأ: {error_msg}")
        
        if "rate_limit_exceeded" in error_msg.lower() or "request too large" in error_msg.lower():
            user_conversations[user_id] = []
            return "⚠️ **تم تجاوز حد الرموز.**\n\nتم مسح سجل المحادثة تلقائياً. أعد إرسال سؤالك."
        
        if "rate_limit" in error_msg.lower():
            return "⚠️ تم تجاوز حد الطلبات (1000 طلب/يوم). الرجاء المحاولة لاحقاً."
        
        return f"⚠️ حدث خطأ: {error_msg[:150]}"

# ========================
# أوامر البوت
# ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "🤖 *مرحباً بك في بوت Groq AI المتعدد النماذج!*\n\n"
        f"✨ يتوفر *{len(AVAILABLE_MODELS)} نموذجاً* مختلفاً للاختيار!\n"
        "• ردود فائقة السرعة ⚡\n"
        "• نماذج متخصصة بالعربية 🇸🇦\n"
        "• نظام متكامل مع بحث ويب 🌐\n\n"
        "🎛️ *الأوامر:*\n"
        "/models - عرض جميع النماذج\n"
        "/model - تغيير النموذج\n"
        "/temp [0-2] - تغيير درجة الإبداع\n"
        "/settings - الإعدادات الحالية\n"
        "/clear - مسح المحادثة\n"
        "/help - المساعدة",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['models'])
def list_all_models(message):
    """عرض جميع النماذج المتاحة"""
    user_id = message.chat.id
    current_model = get_user_settings(user_id)["model"]
    
    # تقسيم النماذج إلى فئات
    production = []
    preview = []
    systems = []
    
    for key, model in AVAILABLE_MODELS.items():
        if "compound" in model["name"].lower():
            systems.append(f"• `{model['name']}`\n  {model['desc']}")
        elif any(x in model["name"].lower() for x in ["llama-4", "qwen", "kimi", "deepseek", "saba", "allam", "gemma-2-2b"]):
            preview.append(f"• `{model['name']}`\n  {model['desc']}")
        else:
            production.append(f"• `{model['name']}`\n  {model['desc']}")
    
    msg = f"🎯 *النماذج المتاحة في Groq* (إجمالي {len(AVAILABLE_MODELS)})\n\n"
    msg += f"✨ *النموذج الحالي:* `{current_model}`\n\n"
    
    msg += "🤖 **نماذج الإنتاج:**\n" + "\n".join(production[:5]) + "\n\n"
    msg += "🔬 **نماذج المعاينة:**\n" + "\n".join(preview[:8]) + "\n\n" 
    msg += "🛠️ **الأنظمة المتكاملة:**\n" + "\n".join(systems) + "\n\n"
    
    msg += "💡 *لتغيير النموذج استخدم /model*"
    
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(commands=['model'])
def change_model(message):
    user_id = message.chat.id
    
    # بناء القائمة مع الترقيم
    models_list = f"🎛️ *اختر نموذجاً* (إجمالي {len(AVAILABLE_MODELS)}):\n\n"
    
    # تجميع النماذج
    for key, model in AVAILABLE_MODELS.items():
        current = " ✅" if get_user_settings(user_id)["model"] == model["name"] else ""
        models_list += f"`{key}` - {model['desc']}{current}\n"
    
    models_list += f"\n*أرسل رقم النموذج* (1-{len(AVAILABLE_MODELS)})"
    
    # تقسيم القائمة إذا كانت طويلة جداً
    if len(models_list) > 4000:
        models_list = models_list[:3500] + "\n... (قائمة طويلة، الرجاء إرسال الرقم المطلوب)"
    
    sent_msg = bot.reply_to(message, models_list, parse_mode='Markdown')
    
    def handle_model_choice(msg):
        if msg.chat.id != user_id:
            return
        
        choice = msg.text.strip()
        if choice in AVAILABLE_MODELS:
            settings = get_user_settings(user_id)
            settings["model"] = AVAILABLE_MODELS[choice]["name"]
            user_settings[user_id] = settings
            user_conversations[user_id] = []
            bot.reply_to(
                msg, 
                f"✅ تم تغيير النموذج إلى:\n*{AVAILABLE_MODELS[choice]['desc']}*\n\n🗑️ تم مسح سجل المحادثة.", 
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(msg, f"❌ رقم غير صالح. الرجاء إرسال رقم بين 1 و {len(AVAILABLE_MODELS)}")
        
        bot.clear_step_handler_by_chat_id(user_id)
    
    bot.register_next_step_handler(sent_msg, handle_model_choice)

@bot.message_handler(commands=['temp'])
def change_temperature(message):
    user_id = message.chat.id
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "🌡️ *تغيير درجة الحرارة*\n\nالمدى: 0 إلى 2\nمثال: `/temp 1.5`\n\n• 0 = ردود ثابتة\n• 1 = إبداع متوسط\n• 2 = ردود عشوائية", parse_mode='Markdown')
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
        bot.reply_to(message, "❌ أرسل رقماً صحيحاً. مثال: `/temp 1.5`", parse_mode='Markdown')

@bot.message_handler(commands=['clear'])
def clear_history(message):
    user_id = message.chat.id
    user_conversations[user_id] = []
    bot.reply_to(message, "✅ تم مسح سجل المحادثة بنجاح!", parse_mode='Markdown')

@bot.message_handler(commands=['settings'])
def show_settings(message):
    user_id = message.chat.id
    settings = get_user_settings(user_id)
    
    model_desc = "نموذج غير معروف"
    for key, model in AVAILABLE_MODELS.items():
        if model["name"] == settings["model"]:
            model_desc = model["desc"]
            break
    
    conv_count = len(user_conversations.get(user_id, []))
    
    bot.reply_to(
        message,
        f"⚙️ *الإعدادات الحالية*\n\n"
        f"📌 **النموذج:** {model_desc}\n"
        f"🌡️ **درجة الحرارة:** {settings['temperature']}\n"
        f"📝 **الحد الأقصى للرد:** {settings['max_tokens']} رمز\n"
        f"💬 **رسائل المحادثة:** {conv_count}\n\n"
        f"🔄 *لرؤية جميع النماذج استخدم /models*",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        "📚 *الأوامر المتاحة*\n\n"
        "**📋 قائمة النماذج**\n"
        "/models - عرض جميع الـ 18 نموذجاً\n"
        "/model - تغيير النموذج\n\n"
        "**⚙️ التحكم**\n"
        "/temp [0-2] - تغيير درجة الإبداع\n"
        "/settings - عرض الإعدادات\n"
        "/clear - مسح المحادثة\n\n"
        "**ℹ️ معلومات**\n"
        "/start - الترحيب\n"
        "/help - هذه المساعدة\n\n"
        "💡 *ملاحظة:* بعض النماذج قد تكون تجريبية",
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
    print(f"✅ يتوفر {len(AVAILABLE_MODELS)} نموذجاً")
    print("🎯 البوت يعمل الآن!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
