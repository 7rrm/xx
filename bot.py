"""
بوت تليجرام يعمل مع Groq AI ويدعم Telethon
يدعم 17 نموذجاً مختلفاً من Groq
"""

import asyncio
import os
import signal
import sys
from telethon import TelegramClient, events
from telethon.tl.types import Message
from groq import Groq
import logging

# إعدادات التسجيل للأخطاء
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================
# 🔐 إعدادات API (⚠️ استبدلها فوراً!)
# ========================
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
GROQ_API_KEY = "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"

# الإعدادات الافتراضية
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 2000

# ========================
# قائمة جميع النماذج المتاحة في Groq (17 نموذجاً)
# ========================
AVAILABLE_MODELS = {
    # 🤖 نماذج الإنتاج (Production)
    "1": {"name": "openai/gpt-oss-120b", "desc": "GPT-OSS 120B - نموذج متقدم من OpenAI"},
    "2": {"name": "openai/gpt-oss-20b", "desc": "GPT-OSS 20B - نسخة أسرع وأخف"},
    "3": {"name": "llama-3.3-70b-versatile", "desc": "Llama 3.3 70B - نموذج قوي من Meta"},
    "4": {"name": "llama-3.1-8b-instant", "desc": "Llama 3.1 8B - سريع جداً (560 رمز/ثانية)"},
    "5": {"name": "mixtral-8x7b-32768", "desc": "Mixtral 8x7B - سياق طويل 32K"},
    
    # 🎯 نماذج المعاينة (Preview)
    "6": {"name": "meta-llama/llama-4-scout-17b-16e-instruct", "desc": "Llama 4 Scout 17B - أحدث نماذج Meta"},
    "7": {"name": "meta-llama/llama-4-maverick-17b-128e-instruct", "desc": "Llama 4 Maverick 17B - متقدم"},
    "8": {"name": "qwen/qwen3-32b", "desc": "Qwen 3 32B - من阿里巴巴 (استدلال قوي)"},
    "9": {"name": "qwen/qwen3-14b", "desc": "Qwen 3 14B - نسخة متوسطة"},
    "10": {"name": "qwen/qwen3-8b", "desc": "Qwen 3 8B - نسخة سريعة"},
    "11": {"name": "moonshotai/kimi-k2-instruct-0905", "desc": "Kimi K2 - سياق عملاق 262K رمز"},
    "12": {"name": "deepseek-r1-distill-llama-70b", "desc": "DeepSeek R1 - استدلال متقدم"},
    "13": {"name": "mistral-saba-24b", "desc": "Mistral Saba - ممتاز للغة العربية ⭐"},
    "14": {"name": "allam-2-7b", "desc": "ALLaM 2 7B - نموذج عربي"},
    "15": {"name": "gemma2-9b-it", "desc": "Gemma 2 9B - من Google"},
    
    # 🛠️ الأنظمة المتكاملة
    "16": {"name": "groq/compound", "desc": "Compound - نظام متكامل (بحث ويب + كود)"},
    "17": {"name": "groq/compound-mini", "desc": "Compound Mini - نسخة أخف"},
}

# ========================
# تهيئة العميل
# ========================
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# تخزين بيانات المستخدمين
user_settings = {}
user_conversations = {}

def get_user_settings(user_id: int) -> dict:
    """الحصول على إعدادات المستخدم"""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "model": DEFAULT_MODEL,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS
        }
    return user_settings[user_id]

async def get_ai_response(user_id: int, user_message: str) -> str:
    """الحصول على رد من Groq AI"""
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
        
        # استدعاء Groq API
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
        logger.error(f"خطأ للمستخدم {user_id}: {error_msg}")
        
        if "rate_limit_exceeded" in error_msg.lower() or "request too large" in error_msg.lower():
            user_conversations[user_id] = []
            return "⚠️ **تم تجاوز حد الرموز.**\n\nتم مسح سجل المحادثة تلقائياً. أعد إرسال سؤالك."
        
        if "rate_limit" in error_msg.lower():
            return "⚠️ تم تجاوز حد الطلبات (1000 طلب/يوم). الرجاء المحاولة لاحقاً."
        
        if "does not exist" in error_msg.lower():
            return "⚠️ هذا النموذج غير متاح حالياً. استخدم /models لرؤية النماذج المتاحة."
        
        return f"⚠️ حدث خطأ: {error_msg[:150]}"

# ========================
# أوامر البوت
# ========================

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """رسالة الترحيب"""
    await event.reply(
        "🤖 *مرحباً بك في بوت Groq AI المتعدد النماذج!*\n\n"
        f"✨ يتوفر *{len(AVAILABLE_MODELS)} نموذجاً* مختلفاً للاختيار!\n"
        "• ردود فائقة السرعة ⚡\n"
        "• نماذج متخصصة بالعربية 🇸🇦\n"
        "• نظام متكامل مع بحث ويب 🌐\n\n"
        "🎛️ *الأوامر:*\n"
        "/models - عرض جميع النماذج\n"
        "/model - تغيير النموذج\n"
        "/temp [0-2] - تغيير درجة الحرارة\n"
        "/settings - الإعدادات الحالية\n"
        "/clear - مسح سجل المحادثة\n"
        "/help - المساعدة",
        link_preview=False
    )

@bot.on(events.NewMessage(pattern='/models'))
async def list_models_handler(event):
    """عرض جميع النماذج المتاحة"""
    user_id = event.sender_id
    current_model = get_user_settings(user_id)["model"]
    
    # تجميع النماذج حسب الفئات
    production = []
    preview = []
    systems = []
    
    for key, model in AVAILABLE_MODELS.items():
        if "compound" in model["name"].lower():
            systems.append(f"• `{model['name']}`\n  {model['desc']}")
        elif any(x in model["name"].lower() for x in ["llama-4", "qwen", "kimi", "deepseek", "saba", "allam"]):
            preview.append(f"• `{model['name']}`\n  {model['desc']}")
        else:
            production.append(f"• `{model['name']}`\n  {model['desc']}")
    
    msg = f"🎯 *النماذج المتاحة في Groq* (إجمالي {len(AVAILABLE_MODELS)})\n\n"
    msg += f"✨ *النموذج الحالي:* `{current_model}`\n\n"
    
    if production:
        msg += "🤖 **نماذج الإنتاج:**\n" + "\n".join(production[:5]) + "\n\n"
    if preview:
        msg += "🔬 **نماذج المعاينة:**\n" + "\n".join(preview[:8]) + "\n\n"
    if systems:
        msg += "🛠️ **الأنظمة المتكاملة:**\n" + "\n".join(systems) + "\n\n"
    
    msg += "💡 *لتغيير النموذج استخدم /model*"
    
    await event.reply(msg, link_preview=False)

@bot.on(events.NewMessage(pattern='/model'))
async def change_model_handler(event):
    """تغيير النموذج الحالي"""
    user_id = event.sender_id
    
    # بناء القائمة
    models_list = f"🎛️ *اختر نموذجاً* (إجمالي {len(AVAILABLE_MODELS)}):\n\n"
    
    for key, model in AVAILABLE_MODELS.items():
        current = " ✅" if get_user_settings(user_id)["model"] == model["name"] else ""
        models_list += f"`{key}` - {model['desc']}{current}\n"
    
    models_list += f"\n*أرسل رقم النموذج* (1-{len(AVAILABLE_MODELS)})"
    
    await event.reply(models_list)
    
    # انتظار رد المستخدم
    @bot.on(events.NewMessage(chats=user_id))
    async def handle_model_choice(e):
        if e.sender_id != user_id:
            return
        
        choice = e.raw_text.strip()
        if choice in AVAILABLE_MODELS:
            settings = get_user_settings(user_id)
            settings["model"] = AVAILABLE_MODELS[choice]["name"]
            user_settings[user_id] = settings
            if user_id in user_conversations:
                user_conversations[user_id] = []
            await e.reply(f"✅ تم تغيير النموذج إلى:\n*{AVAILABLE_MODELS[choice]['desc']}*\n\n🗑️ تم مسح سجل المحادثة.")
        else:
            await e.reply(f"❌ رقم غير صالح. الرجاء إرسال رقم بين 1 و {len(AVAILABLE_MODELS)}")
        
        # إزالة المعالج المؤقت
        bot.remove_event_handler(handle_model_choice)

@bot.on(events.NewMessage(pattern='/temp(?:\\s+(\\d+(?:\\.\\d+)?))?'))
async def change_temperature_handler(event):
    """تغيير درجة الحرارة"""
    user_id = event.sender_id
    parts = event.raw_text.split()
    
    if len(parts) < 2:
        await event.reply(
            "🌡️ *تغيير درجة الحرارة*\n\n"
            "المدى: 0 إلى 2\n"
            "مثال: `/temp 1.5`\n\n"
            "• 0 = ردود ثابتة ومتوقعة\n"
            "• 1 = إبداع متوسط\n"
            "• 2 = ردود عشوائية وإبداعية"
        )
        return
    
    try:
        temp_value = float(parts[1])
        
        if 0 <= temp_value <= 2:
            settings = get_user_settings(user_id)
            settings["temperature"] = temp_value
            user_settings[user_id] = settings
            await event.reply(f"✅ تم تغيير درجة الحرارة إلى *{temp_value}*")
        else:
            await event.reply("❌ القيمة يجب أن تكون بين 0 و 2")
    except ValueError:
        await event.reply("❌ أرسل رقماً صحيحاً. مثال: `/temp 1.5`")

@bot.on(events.NewMessage(pattern='/clear'))
async def clear_history_handler(event):
    """مسح سجل المحادثة"""
    user_id = event.sender_id
    user_conversations[user_id] = []
    await event.reply("✅ تم مسح سجل المحادثة بنجاح!")

@bot.on(events.NewMessage(pattern='/settings'))
async def settings_handler(event):
    """عرض الإعدادات الحالية"""
    user_id = event.sender_id
    settings = get_user_settings(user_id)
    
    model_desc = "نموذج غير معروف"
    for key, model in AVAILABLE_MODELS.items():
        if model["name"] == settings["model"]:
            model_desc = model["desc"]
            break
    
    conv_count = len(user_conversations.get(user_id, []))
    
    await event.reply(
        f"⚙️ *الإعدادات الحالية*\n\n"
        f"📌 **النموذج:** {model_desc}\n"
        f"🌡️ **درجة الحرارة:** {settings['temperature']}\n"
        f"📝 **الحد الأقصى للرد:** {settings['max_tokens']} رمز\n"
        f"💬 **رسائل المحادثة:** {conv_count}\n\n"
        f"🔄 *لرؤية جميع النماذج استخدم /models*"
    )

@bot.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    """رسالة المساعدة"""
    await event.reply(
        "📚 *الأوامر المتاحة*\n\n"
        "**📋 قائمة النماذج**\n"
        "/models - عرض جميع الـ 17 نموذجاً\n"
        "/model - تغيير النموذج\n\n"
        "**⚙️ التحكم**\n"
        "/temp [0-2] - تغيير درجة الحرارة\n"
        "/settings - عرض الإعدادات\n"
        "/clear - مسح سجل المحادثة\n\n"
        "**ℹ️ معلومات**\n"
        "/start - الترحيب\n"
        "/help - هذه المساعدة\n\n"
        "💡 *ملاحظة:* البوت يتذكر آخر 6 رسائل للحفاظ على السياق"
    )

# ========================
# معالج الرسائل العادية
# ========================
@bot.on(events.NewMessage)
async def handle_message(event: events.NewMessage.Event):
    """الرد على الرسائل العادية"""
    # تجاهل الأوامر
    if event.raw_text.startswith('/'):
        return
    
    # تجاهل الرسائل من البوت نفسه
    if event.out:
        return
    
    user_id = event.sender_id
    user_message = event.raw_text
    
    # إرسال إشارة كتابة
    async with bot.action(event.chat_id, 'typing'):
        response = await get_ai_response(user_id, user_message)
        
        # تقسيم الرد الطويل
        if len(response) > 4000:
            for x in range(0, len(response), 4000):
                await event.reply(response[x:x+4000])
        else:
            await event.reply(response)

# ========================
# تشغيل البوت مع معالجة أفضل للإغلاق
# ========================
async def main():
    """تشغيل البوت"""
    logger.info("🤖 بدء تشغيل بوت تيليجرام مع Groq AI (باستخدام Telethon)...")
    logger.info(f"✅ يتوفر {len(AVAILABLE_MODELS)} نموذجاً")
    logger.info("🎯 البوت يعمل الآن!")
    
    # معالجة إشارات الإيقاف
    def signal_handler():
        logger.info("🛑 استلام إشارة إيقاف...")
        asyncio.create_task(shutdown())
    
    async def shutdown():
        await bot.disconnect()
        logger.info("✅ تم إيقاف البوت بنجاح")
        sys.exit(0)
    
    # تسجيل معالجات الإشارات
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda s, f: signal_handler())
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت يدوياً")
    except RuntimeError as e:
        if "Event loop is closed" in str(e):
            logger.info("تم إغلاق الحلقة بشكل طبيعي")
        else:
            logger.error(f"خطأ غير متوقع: {e}")
