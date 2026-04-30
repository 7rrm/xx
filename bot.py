"""
بوت تليجرام بسيط مع Groq AI (نسخة مستقرة)
"""

import asyncio
from telethon import TelegramClient, events
from groq import Groq
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================
# 🔐 إعدادات API
# ========================
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
GROQ_API_KEY = "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"

# إعدادات النموذج
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TEMPERATURE = 1.0
DEFAULT_MAX_TOKENS = 1500

# النماذج المتاحة
AVAILABLE_MODELS = {
    "1": "openai/gpt-oss-120b",
    "2": "openai/gpt-oss-20b", 
    "3": "llama-3.3-70b-versatile",
    "4": "llama-3.1-8b-instant",
    "5": "mixtral-8x7b-32768",
    "6": "mistral-saba-24b",
    "7": "gemma2-9b-it",
}

# ========================
# التهيئة
# ========================
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
groq = Groq(api_key=GROQ_API_KEY)

# تخزين بيانات المستخدمين
user_models = {}
user_history = {}

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply(
        "🤖 *بوت Groq AI*\n\n"
        "أرسل أي نص وسأرد عليك باستخدام الذكاء الاصطناعي.\n\n"
        "*الأوامر:*\n"
        "/model - تغيير النموذج\n"
        "/temp [0-2] - تغيير الإبداع\n"
        "/clear - مسح المحادثة\n"
        "/help - المساعدة",
        parse_mode='markdown'
    )

@bot.on(events.NewMessage(pattern='/help'))
async def help(event):
    await event.reply(
        "📚 *الأوامر:*\n\n"
        "/model - تغيير نموذج AI\n"
        "/temp [0-2] - تغيير درجة الحرارة\n"
        "/clear - مسح السجل\n"
        "/settings - عرض الإعدادات\n"
        "/models - قائمة النماذج",
        parse_mode='markdown'
    )

@bot.on(events.NewMessage(pattern='/models'))
async def list_models(event):
    msg = "*🤖 النماذج المتاحة:*\n\n"
    for key, name in AVAILABLE_MODELS.items():
        msg += f"`{key}` - `{name}`\n"
    msg += "\nاستخدم /model لاختيار نموذج"
    await event.reply(msg, parse_mode='markdown')

@bot.on(events.NewMessage(pattern='/model'))
async def change_model(event):
    msg = "*اختر نموذجاً:*\n\n"
    for key, name in AVAILABLE_MODELS.items():
        msg += f"`{key}` - `{name}`\n"
    msg += "\n*أرسل الرقم* (1-7)"
    
    sent = await event.reply(msg, parse_mode='markdown')
    
    @bot.on(events.NewMessage(chats=event.chat_id))
    async def reply_handler(e):
        if e.sender_id != event.sender_id:
            return
        if e.raw_text in AVAILABLE_MODELS:
            user_models[event.sender_id] = AVAILABLE_MODELS[e.raw_text]
            await e.reply(f"✅ تم تغيير النموذج إلى:\n`{AVAILABLE_MODELS[e.raw_text]}`")
        else:
            await e.reply("❌ رقم غير صالح")
        bot.remove_event_handler(reply_handler)

@bot.on(events.NewMessage(pattern='/temp'))
async def change_temp(event):
    parts = event.raw_text.split()
    if len(parts) < 2:
        await event.reply("🌡️ *تغيير درجة الحرارة*\n\nمثال: `/temp 1.5`\nالمدى: 0-2")
        return
    try:
        temp = float(parts[1])
        if 0 <= temp <= 2:
            await event.reply(f"✅ تم تغيير درجة الحرارة إلى *{temp}*")
        else:
            await event.reply("❌ القيمة بين 0 و 2")
    except:
        await event.reply("❌ أرسل رقماً صحيحاً")

@bot.on(events.NewMessage(pattern='/clear'))
async def clear(event):
    user_history[event.sender_id] = []
    await event.reply("✅ تم مسح سجل المحادثة")

@bot.on(events.NewMessage(pattern='/settings'))
async def settings(event):
    uid = event.sender_id
    model = user_models.get(uid, DEFAULT_MODEL)
    await event.reply(f"⚙️ *الإعدادات*\n\n📌 النموذج: `{model}`\n🌡️ الحرارة: {DEFAULT_TEMPERATURE}")

@bot.on(events.NewMessage)
async def handle_message(event):
    # تجاهل الأوامر
    if event.raw_text.startswith('/'):
        return
    
    uid = event.sender_id
    text = event.raw_text
    
    # اختيار النموذج
    model = user_models.get(uid, DEFAULT_MODEL)
    
    # الحصول على السجل
    if uid not in user_history:
        user_history[uid] = []
    
    # إضافة رسالة المستخدم
    user_history[uid].append({"role": "user", "content": text})
    
    # الاحتفاظ بآخر 6 رسائل
    if len(user_history[uid]) > 6:
        user_history[uid] = user_history[uid][-6:]
    
    # إظهار أن البوت يكتب
    async with bot.action(event.chat_id, 'typing'):
        try:
            # استدعاء Groq
            response = groq.chat.completions.create(
                model=model,
                messages=user_history[uid],
                temperature=DEFAULT_TEMPERATURE,
                max_tokens=DEFAULT_MAX_TOKENS,
                stream=False
            )
            
            reply = response.choices[0].message.content
            
            # حفظ رد المساعد
            user_history[uid].append({"role": "assistant", "content": reply})
            
            # إرسال الرد
            if len(reply) > 4000:
                for i in range(0, len(reply), 4000):
                    await event.reply(reply[i:i+4000])
            else:
                await event.reply(reply)
                
        except Exception as e:
            logger.error(f"Groq error: {e}")
            await event.reply(f"⚠️ خطأ: {str(e)[:100]}")

# ========================
# التشغيل
# ========================
async def main():
    logger.info("🤖 بدء تشغيل البوت...")
    await bot.start()
    logger.info("✅ البوت يعمل!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 تم إيقاف البوت")
