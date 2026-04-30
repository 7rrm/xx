import telebot
from groq import Groq
import threading
import time
import json
import os

# ========================
# 🔐 الإعدادات - قم بتعديلها
# ========================
TELEGRAM_BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
GROQ_API_KEY = "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"

# الإعدادات الافتراضية
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 1
DEFAULT_MAX_TOKENS = 8192

# قائمة النماذج المتاحة (يمكن تحديثها)
AVAILABLE_MODELS = {
    "1": {"name": "openai/gpt-oss-120b", "desc": "GPT-OSS 120B - نموذج متقدم من OpenAI"},
    "2": {"name": "openai/gpt-oss-20b", "desc": "GPT-OSS 20B - نسخة أسرع وأخف"},
    "3": {"name": "llama3-70b-8192", "desc": "Llama 3 70B - نموذج قوي من Meta"},
    "4": {"name": "llama3-8b-8192", "desc": "Llama 3 8B - سريع ومناسب للمهام البسيطة"},
    "5": {"name": "mixtral-8x7b-32768", "desc": "Mixtral 8x7B - سياق طويل جداً"},
    "6": {"name": "gemma2-9b-it", "desc": "Gemma 2 9B - من Google"}
}

# ========================
# تهيئة العملاء
# ========================
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# تخزين إعدادات كل مستخدم
user_settings = {}
user_conversations = {}

def get_user_settings(user_id):
    """الحصول على إعدادات المستخدم"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS
        }
    return user_settings[user_id]

def get_ai_response(user_id, user_message):
    """الحصول على رد من Groq AI باستخدام إعدادات المستخدم"""
    try:
        settings = get_user_settings(user_id)
        
        # إدارة سجل المحادثة للمستخدم
        if user_id not in user_conversations:
            user_conversations[user_id] = []
        
        # إضافة رسالة المستخدم إلى السجل
        user_conversations[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # الاحتفاظ بآخر 10 رسائل فقط
        if len(user_conversations[user_id]) > 10:
            user_conversations[user_id] = user_conversations[user_id][-10:]
        
        # استدعاء Groq API
        completion = groq_client.chat.completions.create(
            model=settings["model"],
            messages=user_conversations[user_id],
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            top_p=1,
            stream=True
        )
        
        # تجميع الرد من الدفق
        full_response = ""
        for chunk in completion:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        # إضافة رد المساعد إلى السجل
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
            return "⚠️ تم تجاوز حد الطلبات المجانية. الرجاء المحاولة بعد دقيقة."
        return f"⚠️ حدث خطأ: {error_msg[:100]}"

# ========================
# أوامر البوت
# ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """رسالة الترحيب عند بدء البوت"""
    bot.reply_to(
        message,
        "🤖 *مرحباً بك في بوت Groq AI المتعدد النماذج!*\n\n"
        "✨ يمكنني التحدث معك بأكثر من نموذج ذكاء اصطناعي\n"
        "🎛️ يمكنك تغيير النموذج والإعدادات في أي وقت\n\n"
        "*الأوامر المتاحة:*\n"
        "/model - تغيير النموذج الحالي\n"
        "/settings - عرض الإعدادات الحالية\n"
        "/temp - تغيير درجة الحرارة (0-2)\n"
        "/clear - مسح سجل المحادثة\n"
        "/about - معلومات عن البوت\n"
        "/help - عرض المساعدة",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    """رسالة المساعدة"""
    bot.reply_to(
        message,
        "📚 *كيفية استخدام البوت:*\n\n"
        "• أرسل أي نص وسأرد عليك فوراً\n"
        "• البوت يتذكر آخر 10 رسائل للحفاظ على السياق\n"
        "• يمكنك تغيير النموذج والإعدادات متى أردت\n\n"
        "*الأوامر التفصيلية:*\n"
        "/model - عرض قائمة النماذج واختيار نموذج جديد\n"
        "/settings - عرض النموذج ودرجة الحرارة الحالية\n"
        "/temp [0-2] - تغيير درجة الحرارة (مثال: /temp 1.5)\n"
        "/clear - مسح سجل محادثتك\n"
        "/about - معلومات تقنية عن البوت",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['model'])
def change_model(message):
    """تغيير النموذج الحالي"""
    user_id = message.chat.id
    
    # بناء قائمة النماذج
    models_list = "*🎛️ النماذج المتاحة:*\n\n"
    for key, model in AVAILABLE_MODELS.items():
        current = " ✅" if get_user_settings(user_id)["model"] == model["name"] else ""
        models_list += f"`{key}` - {model['desc']}{current}\n"
    
    models_list += "\n*أرسل رقم النموذج الذي تريد استخدامه* (مثال: 1)"
    
    sent_msg = bot.reply_to(message, models_list, parse_mode='Markdown')
    
    # انتظار رد المستخدم
    def handle_model_choice(msg):
        if msg.chat.id != user_id:
            return
        
        choice = msg.text.strip()
        if choice in AVAILABLE_MODELS:
            settings = get_user_settings(user_id)
            settings["model"] = AVAILABLE_MODELS[choice]["name"]
            user_settings[user_id] = settings
            bot.reply_to(msg, f"✅ تم تغيير النموذج إلى:\n*{AVAILABLE_MODELS[choice]['desc']}*", parse_mode='Markdown')
            # مسح المحادثة للحفاظ على السياق مع النموذج الجديد
            if user_id in user_conversations:
                user_conversations[user_id] = []
                bot.send_message(user_id, "🗑️ تم مسح سجل المحادثة لتجنب الالتباس مع النموذج الجديد.")
        else:
            bot.reply_to(msg, "❌ رقم غير صالح. الرجاء إرسال رقم من القائمة (1-6).")
        
        bot.clear_step_handler_by_chat_id(user_id)
    
    bot.register_next_step_handler(sent_msg, handle_model_choice)

@bot.message_handler(commands=['settings'])
def show_settings(message):
    """عرض الإعدادات الحالية"""
    user_id = message.chat.id
    settings = get_user_settings(user_id)
    
    # معرفة اسم النموذج
    model_desc = "نموذج غير معروف"
    for key, model in AVAILABLE_MODELS.items():
        if model["name"] == settings["model"]:
            model_desc = model["desc"]
            break
    
    info = (
        f"⚙️ *الإعدادات الحالية:*\n\n"
        f"📌 *النموذج:* {model_desc}\n"
        f"🌡️ *درجة الحرارة:* {settings['temperature']}\n"
        f"📝 *الحد الأقصى للرموز:* {settings['max_tokens']}\n\n"
        f"لتغيير النموذج استخدم /model\n"
        f"لتغيير درجة الحرارة استخدم /temp [القيمة]"
    )
    bot.reply_to(message, info, parse_mode='Markdown')

@bot.message_handler(commands=['temp'])
def change_temperature(message):
    """تغيير درجة الحرارة"""
    user_id = message.chat.id
    
    try:
        # استخراج القيمة من الأمر
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ الرجاء إدخال قيمة درجة الحرارة.\nمثال: `/temp 1.5`\n\nالمدى المسموح: 0 إلى 2", parse_mode='Markdown')
            return
        
        temp_value = float(parts[1])
        
        if 0 <= temp_value <= 2:
            settings = get_user_settings(user_id)
            settings["temperature"] = temp_value
            user_settings[user_id] = settings
            bot.reply_to(message, f"✅ تم تغيير درجة الحرارة إلى *{temp_value}*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ درجة الحرارة يجب أن تكون بين 0 و 2 فقط.")
    except ValueError:
        bot.reply_to(message, "❌ الرجاء إدخال رقم صحيح. مثال: `/temp 1.5`", parse_mode='Markdown')

@bot.message_handler(commands=['clear'])
def clear_history(message):
    """مسح سجل المحادثة للمستخدم"""
    user_id = message.chat.id
    if user_id in user_conversations:
        user_conversations[user_id] = []
        bot.reply_to(message, "✅ تم مسح سجل المحادثة بنجاح!")
    else:
        bot.reply_to(message, "📭 لا يوجد سجل محادثة لمسحه.")

@bot.message_handler(commands=['about'])
def send_about(message):
    """معلومات تقنية عن البوت"""
    user_id = message.chat.id
    settings = get_user_settings(user_id)
    
    bot.reply_to(
        message,
        "ℹ️ *معلومات تقنية:*\n\n"
        f"• المنصة: Groq Cloud API\n"
        f"• النموذج الحالي: `{settings['model']}`\n"
        f"• درجة الحرارة: `{settings['temperature']}`\n"
        f"• الحد الأقصى: `{settings['max_tokens']}` رمز\n"
        "• وضع الدفق (Streaming): مفعل ✅\n"
        "• سعة الذاكرة: 10 رسائل أخيرة\n\n"
        "🔄 *لتحديث قائمة النماذج:*\n"
        "يمكنك تعديل قاموس `AVAILABLE_MODELS` في الكود",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    """الرد على جميع الرسائل النصية"""
    user_id = message.chat.id
    user_text = message.text
    
    # تجنب الاستجابة للأوامر التي تبدأ بـ / ولكن لم يتم التقاطها
    if user_text.startswith('/'):
        return
    
    # إرسال إشارة بأن البوت يكتب
    bot.send_chat_action(user_id, 'typing')
    
    # الحصول على رد من Groq AI
    response = get_ai_response(user_id, user_text)
    
    # تقسيم الرد إذا كان طويلاً جداً
    if len(response) > 4000:
        for x in range(0, len(response), 4000):
            bot.reply_to(message, response[x:x+4000])
    else:
        bot.reply_to(message, response)

# ========================
# تشغيل البوت
# ========================
if __name__ == "__main__":
    print("🤖 بدء تشغيل بوت تيليجرام مع Groq AI...")
    print("📡 النماذج المتاحة:")
    for key, model in AVAILABLE_MODELS.items():
        print(f"   {key}. {model['desc']}")
    print("✅ البوت يعمل... اضغط Ctrl+C للإيقاف")
    bot.infinity_polling()
