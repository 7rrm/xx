import asyncio
import akinator
from telethon import TelegramClient, events, Button

# ========== بياناتك ==========
API_ID = 23032698
API_HASH = "99ad65a5fcd38203621cb20acd2aaba5"
BOT_TOKEN = "7068624335:AAHagvK1fby2WpnulcN1akudmRTfhIJ42-4"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

# أزرار الإجابة (الأرقام من 0 إلى 4)
buttons = [
    [Button.inline("✅ نعم", b"0"), Button.inline("❌ لا", b"1")],
    [Button.inline("❓ لا أعرف", b"2"), Button.inline("🤔 ربما", b"3")],
    [Button.inline("😕 الأغلب لا", b"4")]
]

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
    
    # تنظيف أي جلسة قديمة
    if chat_id in games:
        del games[chat_id]
    
    try:
        # بدء لعبة جديدة
        aki = akinator.Akinator()
        first_question = aki.start_game(language='ar')
        games[chat_id] = aki
        
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{first_question}\n\n📊 التقدم: {int(aki.progression)}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ: {str(e)[:200]}")

@bot.on(events.CallbackQuery)
async def on_button_click(event):
    chat_id = event.chat_id
    answer_code = int(event.data.decode())
    
    # التحقق من وجود لعبة نشطة
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # إرسال الإجابة
        aki.answer(answer_code)
        
        # التحقق من التخمين
        if aki.progression < 80:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step + 1}:**\n\n{aki.question}\n\n📊 التقدم: {int(aki.progression)}%",
                buttons=buttons
            )
        else:
            # الحصول على التخمين
            aki.win()
            guess = aki.first_guess
            
            result = f"🎉 **تخميني هو:**\n\n✨ **{guess['name']}**\n\n📝 {guess['description']}"
            
            # إرسال الصورة إذا وجدت
            if guess.get('absolute_picture_path'):
                try:
                    await event.edit(result, file=guess['absolute_picture_path'])
                except:
                    await event.edit(result)
            else:
                await event.edit(result)
            
            # حذف الجلسة
            del games[chat_id]
            
    except Exception as e:
        await event.answer(f"⚠️ خطأ: {str(e)[:100]}", alert=True)

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

print("✅ بوت Akinator يعمل...")
bot.run_until_disconnected()
