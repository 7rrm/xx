import asyncio
import akinator
from telethon import TelegramClient, events, Button
import os

# ========== بياناتك ==========
API_ID = 21623560
API_HASH = "8c448c687d43262833a0ab100255fb43"
BOT_TOKEN = "7145022358:AAHlgguv9tTBkQTwar57Swkb5xiKycptxR8"
# ===========================

bot = TelegramClient("aki_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
games = {}

buttons = [
    [Button.inline("✅ نعم", b"0"), Button.inline("❌ لا", b"1"), Button.inline("❓ لا أعلم", b"2")],
    [Button.inline("🤔 من المحتمل", b"3"), Button.inline("😕 على الأغلب لا", b"4")]
]

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "🧞‍♂️ **مرحباً! أنا بوت Akinator**\n\n"
        "✨ فكر بشخصية (حقيقية أو خيالية)\n"
        "📝 سأطرح عليك أسئلة لأحاول تخمينها\n\n"
        "🎮 **أرسل /play لبدء اللعبة**"
    )

@bot.on(events.NewMessage(pattern="/play"))
async def play(event):
    chat_id = event.chat_id
    try:
        # تأكد من إنشاء الكائن بشكل صحيح
        aki = akinator.Akinator()
        
        # ابدأ اللعبة واحصل على السؤال
        question = aki.start_game()
        
        # تخزين الجلسة
        games[chat_id] = aki
        
        # تأكد أن question هو نص وليس كائن
        await event.reply(
            f"🧞‍♂️ **السؤال 1:**\n\n{str(question)}\n\n📊 التقدم: {aki.progression}%",
            buttons=buttons
        )
    except Exception as e:
        await event.reply(f"❌ خطأ في بدء اللعبة:\n{str(e)}")

@bot.on(events.CallbackQuery)
async def handle_answer(event):
    chat_id = event.chat_id
    answer = event.data.decode()
    
    if chat_id not in games:
        await event.answer("❌ لا توجد لعبة نشطة! أرسل /play", alert=True)
        return
    
    aki = games[chat_id]
    
    try:
        # إرسال الإجابة والحصول على السؤال التالي
        next_question = aki.answer(answer)
        
        # التحقق من الوصول للتخمين
        if aki.progression >= 80 or aki.step >= 80:
            # الحصول على التخمين النهائي
            aki.win()
            guess = aki.first_guess
            
            result_text = f"🎉 **توقعتي هي:**\n\n✨ **{guess['name']}**\n\n📝 {guess['description']}"
            
            # محاولة إرسال الصورة
            if guess.get('absolute_picture_path'):
                try:
                    await event.edit(result_text, file=guess['absolute_picture_path'])
                except Exception as img_err:
                    await event.edit(result_text)
            else:
                await event.edit(result_text)
            
            # حذف الجلسة بعد الانتهاء
            if chat_id in games:
                del games[chat_id]
        else:
            # عرض السؤال التالي
            await event.edit(
                f"🧞‍♂️ **السؤال {aki.step + 1}:**\n\n{str(next_question)}\n\n📊 التقدم: {aki.progression}%",
                buttons=buttons
            )
    except Exception as e:
        await event.answer(f"⚠️ حدث خطأ: {str(e)[:100]}", alert=True)
        # إذا كان الخطأ جسيماً، حذف الجلسة
        if chat_id in games:
            del games[chat_id]

@bot.on(events.NewMessage(pattern="/stop"))
async def stop(event):
    chat_id = event.chat_id
    if chat_id in games:
        del games[chat_id]
        await event.reply("✅ تم إنهاء اللعبة. أرسل /play للبدء من جديد")
    else:
        await event.reply("ℹ️ لا توجد لعبة نشطة!")

@bot.on(events.NewMessage(pattern="/help"))
async def help_cmd(event):
    await event.reply(
        "🎮 **أوامر بوت Akinator:**\n\n"
        "/start - عرض الترحيب\n"
        "/play - بدء لعبة جديدة\n"
        "/stop - إنهاء اللعبة الحالية\n"
        "/help - عرض هذه المساعدة\n\n"
        "✨ **طريقة اللعب:**\n"
        "1. فكر في شخصية (حقيقية أو خيالية)\n"
        "2. أجب على الأسئلة بالأزرار\n"
        "3. سأحاول تخمين شخصيتك!"
    )

print("✅ بوت Akinator يعمل... انتظر الأوامر")
bot.run_until_disconnected()
