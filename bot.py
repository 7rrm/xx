import asyncio
import cloudscraper
import json
import uuid
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

# أزرار الإجابة
buttons = [
    [Button.inline("✅ نعم", b"0"), Button.inline("❌ لا", b"1"), Button.inline("❓ لا أعرف", b"2")],
    [Button.inline("🤔 ربما", b"3"), Button.inline("😕 الأغلب لا", b"4")]
]

# إنشاء سكرابر واحد لجميع الجلسات
scraper = cloudscraper.create_scraper()

# خادم اللعبة (بالعربية)
SERVER_URL = "https://ar.akinator.com"
API_URL = "https://api4.akinator.com"

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت أكيناتور**\n\n"
        "✨ فكر في شخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    
    try:
        # الحصول على جلسة جديدة
        session_id = str(uuid.uuid4())
        response = scraper.get(f"{SERVER_URL}/game", params={
            "session": session_id,
            "lang": "ar",
            "theme": "c"
        })
        
        # استخراج البيانات
        games[chat_id] = {
            "session": session_id,
            "step": 0,
            "progression": 0
        }
        
        # السؤال الأول
        first_question = "فكر في شخصية واضغط ابدأ"
        
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{first_question}\n\n📊 التقدم: 0%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ: {str(e)[:200]}")

print("✅ البوت يعمل... لكن هذا حل مؤقت")
bot.run_until_disconnected()
