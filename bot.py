import asyncio
import akinator
from telethon import TelegramClient, events, Button
import logging

# إعداد التسجيل للأخطاء
logging.basicConfig(level=logging.INFO)

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

# أزرار الإجابة - باستخدام نصوص عادية
buttons = [
    [Button.inline("✅ نعم", b"yes")],
    [Button.inline("❌ لا", b"no")],
    [Button.inline("❓ لا أعرف", b"idk")],
    [Button.inline("🤔 ربما", b"prob")],
    [Button.inline("😕 الأغلب لا", b"prob_not")]
]

# خريطة تحويل الأزرار
answer_map = {
    "yes": 0,
    "no": 1,
    "idk": 2,
    "prob": 3,
    "prob_not": 4
}

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
    
    # حذف أي لعبة قديمة
    if chat_id in games:
        del games[chat_id]
    
    try:
        aki = akinator.Akinator()
        question = aki.start_game(language='ar')
        games[chat_id] = aki
        
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{question}\n\n📊 التقدم: {aki.progression}%",
            buttons=buttons
        )
        logging.info(f"Started game for {chat_id}")
        
    except Exception as e:
        logging.error(f"Error in play: {e}")
        await event.reply(f"❌ خطأ: {str(e)[:200]}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    callback_data = event.data.decode()
    
    # استخراج الإجابة من البيانات
    if callback_data in answer_map:
        answer_code = answer_map[callback_data]
    else:
        await event.answer("⚠️ إجابة غير صحيحة", alert=True)
        return
    
    if chat_id not in games:
        await event.answer("❌ انتهت الجلسة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # محاولة إرسال الإجابة
        aki.answer(answer_code)
        
        # التحقق من التخمين
        if aki.progression >= 80:
            aki.win()
            guess = aki.first_guess
            
            result = f"🎉 **تخميني هو:**\n\n✨ **{guess['name']}**\n\n📝 {guess['description']}"
            
            if guess.get('absolute_picture_path'):
                try:
                    await event.edit(result, file=guess['absolute_picture_path'])
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
            
            del games[chat_id]
            
        else:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step + 1}:**\n\n{aki.question}\n\n📊 التقدم: {aki.progression}%",
                buttons=buttons
            )
        
        await event.answer()  # تأكيد الضغط
        
    except Exception as e:
        logging.error(f"Error in answer: {e}")
        await event.answer(f"❌ خطأ: {str(e)[:50]}", alert=True)

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

@bot.on(events.NewMessage(pattern="/new"))
async def new_game(event):
    await play(event)

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
